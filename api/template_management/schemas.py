# api/template_management/schemas.py
from pydantic import BaseModel, Field
from typing import Optional

class TemplateValidateRequest(BaseModel):
    """Schema for validating Liquid template syntax"""
    content: str = Field(..., min_length=1, description="Liquid template content to validate")
    
    class Config:
        schema_extra = {
            "example": {
                "content": "{% assign patient = source.patient %}\n{\n  \"resourceType\": \"Patient\"\n}"
            }
        }

class TemplateResponse(BaseModel):
    """Schema for template response"""
    id: int
    template_name: str
    hie_source: str
    source_type: str
    azure_storage_path: str
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "template_name": "patient_mapping.liquid",
                "hie_source": "Hospital_XYZ",
                "source_type": "HL7",
                "azure_storage_path": "fhir-templates/Hospital_XYZ/patient_mapping.liquid"
            }
        }

class TemplateListResponse(BaseModel):
    """Schema for listing templates"""
    id: int
    template_name: str
    hie_source: str
    source_type: str
    azure_storage_path: str
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "template_name": "patient_mapping.liquid",
                "hie_source": "Hospital_XYZ",
                "source_type": "HL7",
                "azure_storage_path": "fhir-templates/Hospital_XYZ/patient_mapping.liquid"
            }
        }

class TemplateContentResponse(BaseModel):
    """Schema for returning template content"""
    template_name: str
    content: str
    
    class Config:
        schema_extra = {
            "example": {
                "template_name": "patient_mapping.liquid",
                "content": "{% assign patient = source.patient %}\n{\n  \"resourceType\": \"Patient\"\n}"
            }
        }

class TemplateValidationResponse(BaseModel):
    """Schema for template validation response"""
    valid: bool
    message: str
    errors: Optional[list] = None
    
    class Config:
        schema_extra = {
            "example": {
                "valid": True,
                "message": "Template syntax is valid",
                "errors": None
            }
        }

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool
    message: str
    data: Optional[dict] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Template uploaded successfully",
                "data": {"id": 1, "template_name": "patient_mapping.liquid"}
            }
        }

class TemplateQueryParams(BaseModel):
    """Query parameters for filtering templates"""
    hie_source: Optional[str] = None
    source_type: Optional[str] = None
    template_name: Optional[str] = None