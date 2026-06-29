import os
from google_auth_oauthlib.flow import Flow
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
flow = Flow.from_client_secrets_file('credentials.json', scopes=SCOPES, redirect_uri='http://localhost:8000/auth/callback')
auth_url, _ = flow.authorization_url(prompt='consent')
print(auth_url)
