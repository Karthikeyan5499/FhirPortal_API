from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class TemplateType(str, Enum):
    CDA = "CDA"
    HL7 = "HL7"
    FHIR = "FHIR"
    CUSTOM = "Custom"

class TemplateAction(str, Enum):
    DOWNLOAD = "download"
    VALIDATE = "validate"
    TRANSFORM = "transform"
    VIEW = "view"

class TemplateBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=200, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    template_type: TemplateType = Field(..., description="Type of template")
    version: str = Field(default="1.0", description="Template version")
    is_active: bool = Field(default=True, description="Is template active")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Template name cannot be empty')
        return v.strip()
    
    @field_validator('version')
    @classmethod
    def validate_version(cls, v):
        # Simple version validation (X.Y.Z format)
        parts = v.split('.')
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError('Version must be in format X.Y or X.Y.Z')
        return v

class TemplateCreate(TemplateBase):
    tags: Optional[List[str]] = Field(None, description="Template tags for categorization")

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_type: Optional[TemplateType] = None
    version: Optional[str] = None
    is_active: Optional[bool] = None

class TemplateResponse(TemplateBase):
    id: int
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    tags: Optional[List[str]] = []
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TemplateListResponse(BaseModel):
    total: int
    templates: List[TemplateResponse]
    page: int = 1
    page_size: int = 50

class TemplateVersionResponse(BaseModel):
    id: int
    template_id: int
    version: str
    file_url: Optional[str]
    change_description: Optional[str]
    created_by: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True

class TemplateUsageLogResponse(BaseModel):
    id: int
    template_id: int
    user_id: Optional[int]
    action: str
    timestamp: datetime
    ip_address: Optional[str]
    
    class Config:
        from_attributes = True

class TemplateStatistics(BaseModel):
    total_templates: int
    active_templates: int
    inactive_templates: int
    templates_by_type: Dict[str, int]
    most_used_templates: List[Dict[str, Any]]
    recent_uploads: List[Dict[str, Any]]

class TemplateValidationRequest(BaseModel):
    template_id: int
    data: Dict[str, Any] = Field(..., description="Data to validate against template")

class TemplateValidationResponse(BaseModel):
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    template_name: str
    template_version: str

class TemplateTransformRequest(BaseModel):
    source_template_id: int
    target_template_id: int
    data: Dict[str, Any] = Field(..., description="Data to transform")

class TemplateTransformResponse(BaseModel):
    success: bool
    transformed_data: Optional[Dict[str, Any]] = None
    errors: List[str] = []
    source_template: str
    target_template: str

class TemplateSearchRequest(BaseModel):
    query: Optional[str] = None
    template_type: Optional[TemplateType] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)

class BulkTemplateActivateRequest(BaseModel):
    template_ids: List[int]
    is_active: bool