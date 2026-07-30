import os
import io
import json
import re
import asyncio
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SYNC_DIR = 'synced_docs'

# Drive credentials are stored PER ORGANISATION. A single shared token.json
# meant that whichever user completed the OAuth flow last owned the Drive
# connection for every tenant in the deployment — a cross-tenant data leak.
TOKEN_DIR = 'drive_tokens'


def _safe_org(org_id: str) -> str:
    """Sanitise org_id before using it in a filesystem path."""
    if not org_id:
        raise ValueError("org_id is required for Google Drive access")
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(org_id))


def token_path(org_id: str) -> str:
    """Filesystem path of the Drive OAuth token for one organisation."""
    return os.path.join(TOKEN_DIR, f"token_{_safe_org(org_id)}.json")


def org_sync_dir(org_id: str) -> str:
    """Per-org download directory, so two orgs syncing the same Drive file id
    cannot overwrite each other's copy."""
    return os.path.join(SYNC_DIR, _safe_org(org_id))


def has_drive_connection(org_id: str) -> bool:
    try:
        return os.path.exists(token_path(org_id))
    except ValueError:
        return False


def disconnect_drive(org_id: str) -> bool:
    """Remove one org's Drive credentials. Never touches another org's token."""
    path = token_path(org_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def save_credentials(org_id: str, creds) -> None:
    os.makedirs(TOKEN_DIR, exist_ok=True)
    with open(token_path(org_id), 'w') as token:
        token.write(creds.to_json())


def _get_user_email(service):
    try:
        about = service.about().get(fields="user").execute()
        return about['user']['emailAddress']
    except Exception as e:
        print("Could not get user email", e)
        return "default_user"

def current_user_email(org_id: str):
    """Resolve the Google account connected to this org, or 'default_user'.

    Used by the direct upload / URL-import paths so files can be ingested
    without connecting Google Drive at all.
    """
    try:
        service = get_drive_service(org_id)
        return _get_user_email(service)
    except Exception:
        return "default_user"


def get_drive_service(org_id: str):
    """Build a Drive client using the calling organisation's credentials."""
    path = token_path(org_id)
    creds = None
    if os.path.exists(path):
        try:
            creds = Credentials.from_authorized_user_file(path, SCOPES)
        except Exception:
            # If token is corrupted, remove it
            os.remove(path)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                # If refresh fails, remove token and re-auth
                if os.path.exists(path):
                    os.remove(path)
                creds = None

        if not creds:
            raise Exception("Not authenticated. Please login with Google first.")

        save_credentials(org_id, creds)

    from googleapiclient.discovery import build

    # Just use the default build which automatically handles credentials
    return build('drive', 'v3', credentials=creds)

def download_file(service, file_id, file_name, mime_type, modified_time, synced_files, user_email, org_id):
    request = None
    if mime_type == 'application/vnd.google-apps.document':
        request = service.files().export_media(fileId=file_id, mimeType='application/pdf')
        ext = '.pdf'
    else:
        request = service.files().get_media(fileId=file_id)
        ext = os.path.splitext(file_name)[1]
        if not ext:
            ext = '.pdf' if mime_type == 'application/pdf' else '.txt'

    target_dir = org_sync_dir(org_id)
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, f"{file_id}{ext}")

    try:
        with open(file_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
        
        # Update metadata in MongoDB
        from db import files_collection
        doc = {
            "user_email": user_email,
            "org_id": org_id,
            "file_id": file_id,
            "name": file_name,
            "path": file_path,
            "mimeType": mime_type,
            "modifiedTime": modified_time,
            "source": "gdrive"
        }
        files_collection.update_one(
            {"org_id": org_id, "file_id": file_id},
            {"$set": doc},
            upsert=True
        )
        
        return {
            "id": file_id,
            "name": file_name,
            "path": file_path,
            "mimeType": mime_type
        }
    except Exception as e:
        print(f"Failed to download {file_name}: {e}")
        return None

def get_files_to_sync(org_id: str, page_size: int = 10, force: bool = False, folder_url: str = None):
    service = get_drive_service(org_id)
    os.makedirs(org_sync_dir(org_id), exist_ok=True)

    user_email = _get_user_email(service)

    from db import files_collection
    synced_files_cursor = files_collection.find({"org_id": org_id})
    synced_files = {f["file_id"]: f for f in synced_files_cursor}

    # Extract folder ID if a URL is provided
    folder_query = ""
    if folder_url:
        # Match typical Drive folder URLs like https://drive.google.com/drive/folders/1XYZ...
        match = re.search(r"/folders/([a-zA-Z0-9_-]+)", folder_url)
        if match:
            folder_id = match.group(1)
            folder_query = f"'{folder_id}' in parents and "

    query = f"{folder_query}(mimeType='application/pdf' or mimeType='application/vnd.google-apps.document' or mimeType='text/plain')"
    
    results = service.files().list(
        q=query,
        pageSize=page_size,
        fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
        orderBy="modifiedTime desc"
    ).execute()
    items = results.get('files', [])

    if force:
        return items, user_email

    to_download = []
    for item in items:
        file_id = item['id']
        modified_time = item['modifiedTime']
        if file_id in synced_files and synced_files[file_id].get('modifiedTime') == modified_time:
            continue
        to_download.append(item)

    return to_download, user_email

def download_items(items, user_email, org_id):
    if not items:
        return []

    from db import files_collection
    synced_files_cursor = files_collection.find({"org_id": org_id})
    synced_files = {f["file_id"]: f for f in synced_files_cursor}

    try:
        max_workers = int(os.getenv("DOWNLOAD_WORKERS", "2"))
    except Exception:
        max_workers = 2
    max_workers = max(1, min(max_workers, 3))

    def _download_one(item):
        service = get_drive_service(org_id)
        file_id = item['id']
        file_name = item['name']
        mime_type = item['mimeType']
        modified_time = item['modifiedTime']
        print(f"Downloading {file_name}...")
        return download_file(service, file_id, file_name, mime_type, modified_time, synced_files, user_email, org_id)

    downloaded = []
    if max_workers == 1 or len(items) == 1:
        for item in items:
            result = _download_one(item)
            if result:
                downloaded.append(result)
        return downloaded

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_download_one, item) for item in items]
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    downloaded.append(result)
            except Exception as e:
                print(f"Failed to download item: {e}")

    return downloaded

def sync_google_drive(org_id: str):
    items, user_email = get_files_to_sync(org_id, page_size=10, force=False)
    return download_items(items, user_email, org_id)


# --------------------------------------------------------------------------- #
# Spreadsheet / tabular-data support for the Analytics Claws
# --------------------------------------------------------------------------- #
DATA_MIME_TYPES = [
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.google-apps.spreadsheet',
]


def list_data_files(org_id: str, page_size: int = 50, folder_url: str = None):
    """List CSV / Excel / Google Sheets files for analytics import."""
    service = get_drive_service(org_id)
    user_email = _get_user_email(service)

    folder_query = ""
    if folder_url:
        match = re.search(r"/folders/([a-zA-Z0-9_-]+)", folder_url)
        if match:
            folder_query = f"'{match.group(1)}' in parents and "

    mime_filter = " or ".join([f"mimeType='{m}'" for m in DATA_MIME_TYPES])
    query = f"{folder_query}({mime_filter})"

    results = service.files().list(
        q=query,
        pageSize=page_size,
        fields="files(id, name, mimeType, modifiedTime)",
        orderBy="modifiedTime desc",
    ).execute()
    items = results.get('files', [])
    return items, user_email


def download_data_file_bytes(file_id: str, org_id: str):
    """Download a tabular Drive file into memory; returns (bytes, filename)."""
    service = get_drive_service(org_id)
    meta = service.files().get(fileId=file_id, fields="id, name, mimeType").execute()
    mime = meta.get('mimeType')
    name = meta.get('name', file_id)

    if mime == 'application/vnd.google-apps.spreadsheet':
        request = service.files().export_media(fileId=file_id, mimeType='text/csv')
        if not name.lower().endswith('.csv'):
            name = f"{name}.csv"
    else:
        request = service.files().get_media(fileId=file_id)
        if not os.path.splitext(name)[1]:
            name = f"{name}.csv" if 'csv' in (mime or '') else f"{name}.xlsx"

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue(), name
