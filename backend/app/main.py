import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router

environment = os.getenv("ENVIRONMENT", "development").lower()
allowed_origins = [origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
app = FastAPI(title="IMAGE LMS API", version="0.1.0", docs_url=None if environment == "production" else "/docs", redoc_url=None if environment == "production" else "/redoc")
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "image-lms-api", "persistence": os.getenv("PERSISTENCE_MODE", "memory")}
