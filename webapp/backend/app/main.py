from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import annotations, auth, cases, inference, models, training
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

# Faz 1: frontend ayrı bir origin'den (Next.js dev server / ayrı container) çağırır.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(cases.router, prefix="/api/v1")
app.include_router(annotations.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(inference.router, prefix="/api/v1")
app.include_router(training.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "ml_dependencies_available": settings.ml_dependencies_available}
