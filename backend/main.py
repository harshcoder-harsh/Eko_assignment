import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["MALLOC_ARENA_MAX"] = "2"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
from langfuse import Langfuse

langfuse = Langfuse(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_HOST")
)

from api.routes import router
from api.analytics_routes import router as analytics_router
from api.upload_routes import router as documents_router
from api.support_routes import router as support_router
from api.observability_routes import router as observability_router
from api.auth_routes import router as auth_router

app = FastAPI(title="FlowClaw API")

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
# Clean any trailing slashes to prevent exact-match CORS errors
if frontend_url.endswith("/"):
    frontend_url = frontend_url[:-1]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url,
        
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(analytics_router)
app.include_router(documents_router)
app.include_router(support_router)
app.include_router(observability_router)
app.include_router(auth_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    is_dev = os.getenv("ENVIRONMENT", "development") == "development"
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=is_dev)