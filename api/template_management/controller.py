from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Request, status
from fastapi.responses import Response
from .service import TemplateService
from .schemas import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateListResponse,
    TemplateVersionResponse,
    TemplateUsageLogResponse,
    TemplateStatistics,
    TemplateValidationRequest,
    TemplateValidationResponse,
    TemplateTransformRequest,
    TemplateTransformResponse,
    TemplateSearchRequest,
    BulkTemplateActivateRequest,
    TemplateType
)
from common.responses import success_response
from common.exceptions import (
    BadRequestException,
    NotFoundException,
    ValidationException,
    StorageException,
    DatabaseException
)
from dependencies import get_current_user, require_admin
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize service with error handling
try:
    service = TemplateService()
    logger.info("✅ Template Management Controller initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize Template Management Controller: {e}")
    raise

# ==================== TEMPLATE CRUD ====================

@router.get("/templates", response_model=TemplateListResponse)
async def get_all_templates(
    template_type: Optional[str] = Query(None, description="Filter by template type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all templates with pagination and filtering
    
    **Exception Handling:**
    - 400: Invalid pagination parameters
    - 401: Unauthorized
    - 500: Database error
    """
    try:
        return service.get_all_templates(template_type, is_active, page, page_size, search)
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_all_templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch templates: {str(e)}"
        )

@router.post("/templates/search", response_model=TemplateListResponse)
async def search_templates(
    search_request: TemplateSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Advanced template search with multiple criteria
    
    **Exception Handling:**
    - 400: Invalid search parameters
    - 401: Unauthorized
    - 500: Database error
    """
    try:
        return service.search_templates(search_request)
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in search_templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get specific template by ID
    
    **Exception Handling:**
    - 400: Invalid template ID
    - 401: Unauthorized
    - 404: Template not found
    - 500: Database error
    """
    try:
        user_id = int(current_user.get("sub", 0)) if current_user.get("sub", "").isdigit() else None
        return service.get_template(template_id, user_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch template: {str(e)}"
        )

@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template: TemplateCreate,
    current_user: dict = Depends(require_admin)
):
    """
    Create new template (Admin only)
    
    **Exception Handling:**
    - 400: Invalid template data
    - 401: Unauthorized
    - 403: Forbidden (not admin)
    - 409: Duplicate template
    - 422: Validation error
    - 500: Database error
    """
    try:
        user_id = int(current_user.get("sub", 1)) if current_user.get("sub", "").isdigit() else 1
        return service.create_template(template, user_id)
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except BadRequestException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in create_template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}"
        )

@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    template: TemplateUpdate,
    current_user: dict = Depends(require_admin)
):
    """
    Update template (Admin only)
    
    **Exception Handling:**
    - 400: Invalid update data
    - 401: Unauthorized
    - 403: Forbidden (not admin)
    - 404: Template not found
    - 422: Validation error
    - 500: Database error
    """
    try:
        return service.update_template(template_id, template)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in update_template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update template: {str(e)}"
        )

@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
        template_id: int,
        current_user: dict = Depends(require_admin)):
    """
    Delete template (Admin only)
    **Exception Handling:**
    - 400: Invalid template ID
    - 401: Unauthorized
    - 403: Forbidden (not admin)
    - 404: Template not found
    - 500: Database or storage error
    """
    try:
        service.delete_template(template_id)
        return None
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except StorageException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in delete_template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete template: {str(e)}"
        )
#==================== FILE OPERATIONS ====================
@router.post("/templates/{template_id}/upload")
async def upload_template_file(
    template_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin)
    ):
    """
    Upload file for a template (Admin only)
    **Supported formats:** JSON, XML, XSD, TXT, YAML
    **Maximum file size:** 50MB

    **Exception Handling:**
    - 400: Invalid file or file too large
    - 401: Unauthorized
    - 403: Forbidden (not admin)
    - 404: Template not found
    - 422: Validation error
    - 500: Storage or database error
    """
    try:
        if not file.filename:
            raise ValidationException("No file provided")
        
        # Validate file extension
        allowed_extensions = ['.json', '.xml', '.xsd', '.txt', '.yaml', '.yml']
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            raise ValidationException(
                f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        contents = await file.read()
        file_size = len(contents)
        
        if file_size == 0:
            raise ValidationException("File is empty")
        
        if file_size > 50 * 1024 * 1024:  # 50MB
            raise ValidationException("File too large (max 50MB)")
        
        # Upload
        user_id = int(current_user.get("sub", 1)) if current_user.get("sub", "").isdigit() else 1
        blob_url = service.upload_template_file(template_id, file.filename, contents, user_id)
        
        return success_response(
            "File uploaded successfully",
            {
                "blob_url": blob_url,
                "filename": file.filename,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2)
            }
        )
        
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except StorageException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in upload_template_file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )
@router.get("/templates/{template_id}/download")
async def download_template_file(
    template_id: int,
    current_user: dict = Depends(get_current_user)
    ):
    """
    Download template file
    **Exception Handling:**
    - 400: Invalid template ID
    - 401: Unauthorized
    - 404: Template or file not found
    - 500: Storage or database error
    """
    try:
        user_id = int(current_user.get("sub", 0)) if current_user.get("sub", "").isdigit() else 0
        file_content, filename, mime_type = service.download_template_file(template_id, user_id)
        
        return Response(
            content=file_content,
            media_type=mime_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_content))
            }
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except StorageException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in download_template_file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download failed: {str(e)}"
        )
#==================== VERSIONING ====================
@router.get("/templates/{template_id}/versions", response_model=List[TemplateVersionResponse])
async def get_template_versions(
    template_id: int,
    current_user: dict = Depends(get_current_user)
    ):
    """Get all versions of a template"""
    try:
        return service.get_template_versions(template_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_template_versions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch versions: {str(e)}"
    )
#==================== USAGE TRACKING ====================
@router.get("/templates/{template_id}/usage-logs", response_model=List[TemplateUsageLogResponse])
async def get_usage_logs(
    template_id: int,
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    current_user: dict = Depends(require_admin)
    ):
    """Get usage logs for a template (Admin only)"""
    try:
        return service.get_usage_logs(template_id, limit)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_usage_logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch usage logs: {str(e)}"
            )
#==================== STATISTICS ====================
@router.get("/templates/stats/overview", response_model=TemplateStatistics)
async def get_statistics(current_user: dict = Depends(require_admin)):
    """Get template statistics (Admin only)"""
    try:
        return service.get_statistics()
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch statistics: {str(e)}"
            )
#==================== VALIDATION & TRANSFORMATION ====================
@router.post("/templates/validate", response_model=TemplateValidationResponse)
async def validate_data(
    request: TemplateValidationRequest,
    current_user: dict = Depends(get_current_user)
    ):
    """Validate data against a template structure"""
    try:
        return service.validate_data(request)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in validate_data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
            )
    
@router.post("/templates/transform", response_model=TemplateTransformResponse)
async def transform_data(
    request: TemplateTransformRequest,
    current_user: dict = Depends(get_current_user)
    ):
    """Transform data from one template format to another"""
    try:
        return service.transform_data(request)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in transform_data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transformation failed: {str(e)}"
            )
#==================== BULK OPERATIONS ====================
@router.post("/templates/bulk-activate")
async def bulk_activate_templates(
    request: BulkTemplateActivateRequest,
    current_user: dict = Depends(require_admin)
    ):
    """Bulk activate or deactivate templates (Admin only)"""
    try:
        result = service.bulk_activate(request)
        return success_response(
            f"Updated {result['updated_count']} templates",
            result
            )
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in bulk_activate_templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk operation failed: {str(e)}"
            )
#==================== FILTERING ====================
@router.get("/templates/by-type/{template_type}", response_model=List[TemplateResponse])
async def get_templates_by_type(
    template_type: TemplateType,
    current_user: dict = Depends(get_current_user)
    ):
    """Get all templates of a specific type"""
    try:
            return service.get_templates_by_type(template_type.value)
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_templates_by_type: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch templates by type: {str(e)}"
            )
#==================== CLONING ====================
@router.post("/templates/{template_id}/clone", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def clone_template(
    template_id: int,
    new_name: str = Query(..., description="Name for the cloned template"),
    current_user: dict = Depends(require_admin)
    ):
    """Clone an existing template (Admin only)"""
    try:
        user_id = int(current_user.get("sub", 1)) if current_user.get("sub", "").isdigit() else 1
        return service.clone_template(template_id, new_name, user_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except StorageException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in clone_template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cloning failed: {str(e)}"
            )
#==================== STORAGE INFO ====================
@router.get("/storage/info")
async def get_storage_info(current_user: dict = Depends(get_current_user)):
    """Get storage configuration information"""
    try:
        storage_info = service.blob_service.get_storage_info()
        return success_response("Storage information retrieved", storage_info)
    except StorageException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_storage_info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch storage info: {str(e)}"
            )