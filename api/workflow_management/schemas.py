# api/workflow_management/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SourceMasterResponse(BaseModel):
    """Response schema for SourceMaster"""
    Id: int
    Source: str
    SourceType: str

    class Config:
        from_attributes = True


class FileMetadataCreate(BaseModel):
    """Schema for creating FileMetadata record"""
    Source: str = Field(..., max_length=200, description="Source name")
    SourceType: str = Field(..., max_length=50, description="Source type (ADT, ORU, MDM, etc.)")
    FileName: str = Field(..., max_length=300, description="File name")
    FlowType: Optional[str] = Field(None, max_length=100, description="Flow type (Input to LFS, Input to FHIR)")
    UploadedBy: Optional[str] = Field(None, max_length=100, description="User who uploaded")
    Status: Optional[str] = Field("Started", max_length=50, description="Processing status")
    BundleId: Optional[str] = Field(None, max_length=200, description="Bundle ID")
    ValidationStatus: Optional[str] = Field(None, max_length=50, description="Validation status")


class FileMetadataBulkCreate(BaseModel):
    """Schema for bulk creating FileMetadata records"""
    files: List[FileMetadataCreate] = Field(..., description="List of file metadata to insert")


class FileMetadataResponse(BaseModel):
    """Response schema for FileMetadata"""
    Id: int
    Source: str
    SourceType: str
    FileName: str
    BundleId: Optional[str]
    FlowType: Optional[str]
    UploadedBy: Optional[str]
    Uploaded: Optional[datetime]  # Add this field
    Status: Optional[str]
    ValidationStatus: Optional[str]

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """Response schema for file list with pagination"""
    files: List[FileMetadataResponse]
    total: int
    skip: int
    limit: int
    
class BulkInsertResponse(BaseModel):
    """Response schema for bulk insert operation"""
    message: str
    inserted_count: int
    file_ids: List[int]