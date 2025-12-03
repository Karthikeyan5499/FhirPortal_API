from fastapi import FastAPI
from app.api.template_management.controller import router as template_router

app = FastAPI(
    title="Template Management API",
    version="1.0"
)

app.include_router(template_router)
