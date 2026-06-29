"""API routes for the Business Analytics Agent ('Claws').

Endpoints:
  POST   /analytics/upload            - upload a CSV/XLSX dataset
  GET    /analytics/datasets          - list the user's datasets
  GET    /analytics/dataset/{id}      - dataset profile + preview
  DELETE /analytics/dataset/{id}      - delete a dataset
  GET    /analytics/drive/list        - list spreadsheet files in Drive
  POST   /analytics/drive/import      - import a Drive spreadsheet as a dataset
  GET    /analytics/claws             - list available agents
  POST   /analytics/run               - run a Claw on a dataset
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from typing import Optional

from analytics import data_loader
from analytics.agents import run_claw, CLAWS

router = APIRouter(prefix="/analytics", tags=["analytics"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


def _current_user_email() -> str:
    """Resolve the logged-in Google user, falling back to a shared default.

    Analytics works even without Drive auth (direct upload), so we never raise.
    """
    try:
        from connectors.gdrive import get_drive_service
        service = get_drive_service()
        about = service.about().get(fields="user").execute()
        return about['user']['emailAddress']
    except Exception:
        return "default_user"


CLAW_CATALOG = [
    {"id": "data_analyst", "name": "Data Analyst Claw",
     "desc": "Cleans data, surfaces KPIs & trends, and writes a structured insight summary."},
    {"id": "kpi_monitoring", "name": "KPI Monitoring Claw",
     "desc": "Tracks metric changes period-over-period, explains likely causes, recommends actions."},
    {"id": "anomaly_detection", "name": "Anomaly Detection Claw",
     "desc": "Flags unusual values & exceptions using z-score and IQR, with explanations."},
    {"id": "segmentation", "name": "Customer Segmentation Claw",
     "desc": "Clusters customers/entities into segments and describes each in business terms."},
    {"id": "business_performance", "name": "Business Performance Claw",
     "desc": "Generates a full performance report: highlights, risks, and prioritised next actions."},
]


@router.get("/claws")
def list_claws():
    return {"claws": CLAW_CATALOG}


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=400, detail="File too large (max 25 MB).")

        user_email = _current_user_email()
        try:
            meta = data_loader.save_dataset(content, file.filename, user_email, source="upload")
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        return {"status": "success", "dataset": meta}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets")
def list_datasets():
    user_email = _current_user_email()
    return {"datasets": data_loader.list_datasets(user_email)}


@router.get("/dataset/{dataset_id}")
def get_dataset(dataset_id: str):
    user_email = _current_user_email()
    try:
        meta, df = data_loader.load_dataset(dataset_id, user_email)
        profile = data_loader.profile_dataframe(df)
        return {
            "dataset_id": dataset_id,
            "name": meta.get("name"),
            "clean_summary": meta.get("clean_summary"),
            "profile": profile,
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/dataset/{dataset_id}")
def delete_dataset(dataset_id: str):
    user_email = _current_user_email()
    ok = data_loader.delete_dataset(dataset_id, user_email)
    if not ok:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return {"status": "success"}


@router.get("/drive/list")
def drive_list(folder_url: Optional[str] = None):
    try:
        from connectors.gdrive import list_data_files
        items, _ = list_data_files(folder_url=folder_url)
        return {"files": [{"id": i["id"], "name": i["name"], "mimeType": i.get("mimeType")} for i in items]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drive/import")
def drive_import(file_id: str = Query(...)):
    try:
        from connectors.gdrive import download_data_file_bytes
        content, name = download_data_file_bytes(file_id)
        user_email = _current_user_email()
        try:
            meta = data_loader.save_dataset(content, name, user_email, source="gdrive")
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        return {"status": "success", "dataset": meta}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class RunRequest(BaseModel):
    dataset_id: str
    claw: str


@router.post("/run")
def run(req: RunRequest):
    if req.claw not in CLAWS:
        raise HTTPException(status_code=400, detail=f"Unknown claw. Available: {', '.join(CLAWS)}")
    user_email = _current_user_email()
    try:
        result = run_claw(req.claw, req.dataset_id, user_email)
        return {"status": "success", "result": result}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
