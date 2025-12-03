from pydantic import BaseModel

class TemplateRequest(BaseModel):
    templateName: str
    templateContent: str

class TemplateResponse(BaseModel):
    templateName: str
    templateContent: str
