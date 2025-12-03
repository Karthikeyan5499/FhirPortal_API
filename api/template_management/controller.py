from fastapi import APIRouter
from app.api.template_management.schemas import TemplateRequest, TemplateResponse
from app.api.template_management.service import TemplateService

router = APIRouter(prefix="/templates", tags=["Template Management"])

@router.get("/{name}", response_model=TemplateResponse)
def get_template(name: str):
    return TemplateService.get_template(name)

@router.post("/", response_model=dict)
def save_template(request: TemplateRequest):
    return TemplateService.save_template(request.templateName, request.templateContent)
