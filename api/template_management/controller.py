# api/template_management/controller.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
import logging

from api.template_management.service import TemplateService
from api.template_management.schemas import (
    TemplateValidateRequest,
    TemplateResponse,
    TemplateListResponse,
    TemplateContentResponse,
    TemplateValidationResponse,
    SuccessResponse,
    TemplateQueryParams
)
from dependencies import get_current_user, require_admin
from common.exceptions import DatabaseException, StorageException, ValidationException

logger = logging.getLogger(__name__)

router = APIRouter()

def get_template_service() -> TemplateService:
    """Dependency to get TemplateService instance"""
    return TemplateService()

@router.post(
    "/validate",
    response_model=TemplateValidationResponse,
    summary="Validate Liquid Template Syntax",
    description="Validate the syntax of a Liquid template before uploading"
)
async def validate_template(
    request: TemplateValidateRequest,
    service: TemplateService = Depends(get_template_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Validate Liquid template syntax
    
    - **content**: Raw Liquid template content to validate
    
    Returns validation result with any syntax errors
    """
    try:
        logger.info(f"User {current_user.get('sub')} validating template syntax")
        result = service.validate_liquid_syntax(request.content)
        return result
    except Exception as e:
        logger.error(f"Error validating template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation error: {str(e)}"
        )

@router.post(
    "/upload",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload New Liquid Template File",
    description="Upload a .liquid file to Azure Blob Storage and save metadata to database"
)
async def upload_template(
    file: UploadFile = File(..., description="Liquid template file (.liquid)"),
    hie_source: str = Form(..., description="HIE source identifier (e.g., Hospital_XYZ)"),
    source_type: str = Form(..., description="Source type (HL7, CDA, FHIR, X12, CUSTOM)"),
    service: TemplateService = Depends(get_template_service),
    current_user: dict = Depends(require_admin)
):
    """
    Upload a new Liquid template file
    
    - **file**: .liquid template file
    - **hie_source**: HIE source identifier (e.g., Hospital_XYZ)
    - **source_type**: Source type (HL7, CDA, FHIR, X12, CUSTOM)
    
    Requires admin role
    """
    try:
        # Validate file extension
        if not file.filename.endswith('.liquid'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .liquid files are allowed"
            )
        
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')
        
        logger.info(f"Admin {current_user.get('sub')} uploading template file: {file.filename}")
        
        result = service.upload_template_file(
            file_name=file.filename,
            content=content_str,
            hie_source=hie_source,
            source_type=source_type
        )
        return result
        
    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseException as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except StorageException as e:
        logger.error(f"Storage error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error uploading template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload template: {str(e)}"
        )

@router.get(
    "/templates",
    response_model=List[TemplateListResponse],
    summary="List All Templates with Filters",
    description="Get a list of all Liquid templates with optional filters"
)
async def list_templates(
    hie_source: Optional[str] = None,
    source_type: Optional[str] = None,
    template_name: Optional[str] = None,
    service: TemplateService = Depends(get_template_service),
    current_user: dict = Depends(get_current_user)
):
    """
    List all templates with optional filters
    
    - **hie_source**: Filter by HIE source (optional)
    - **source_type**: Filter by source type (optional)
    - **template_name**: Filter by template name (optional)
    
    Returns list of templates with metadata (without content)
    """
    try:
        logger.info(f"User {current_user.get('sub')} listing templates")
        templates = service.list_templates_with_filters(
            hie_source=hie_source,
            source_type=source_type,
            template_name=template_name
        )
        return templates
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}"
        )

@router.get(
    "/templates/by-id/{template_id}",
    response_model=TemplateResponse,
    summary="Get Template by ID",
    description="Get template metadata by ID"
)
async def get_template_by_id(
    template_id: int,
    service: TemplateService = Depends(get_template_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Get template metadata by ID
    
    - **template_id**: ID of the template
    
    Returns template metadata without content
    """
    try:
        logger.info(f"User {current_user.get('sub')} fetching template ID: {template_id}")
        template = service.get_template_by_id(template_id)
        return template
    except ValidationException as e:
        logger.warning(f"Template not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error fetching template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch template: {str(e)}"
        )

@router.get(
    "/templates/{template_name}",
    response_model=List[TemplateResponse],
    summary="Get Templates by Name",
    description="Get all template versions with the same name (across different sources)"
)
async def get_templates_by_name(
    template_name: str,
    hie_source: Optional[str] = None,
    service: TemplateService = Depends(get_template_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all templates with the same name
    
    - **template_name**: Name of the template
    - **hie_source**: Optional filter by HIE source
    
    Returns list of all template versions with this name
    """
    try:
        logger.info(f"User {current_user.get('sub')} fetching templates: {template_name}")
        templates = service.get_templates_by_name(template_name, hie_source)
        return templates
    except ValidationException as e:
        logger.warning(f"Templates not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error fetching templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch templates: {str(e)}"
        )

@router.get(
    "/templates/by-id/{template_id}/content",
    response_model=TemplateContentResponse,
    summary="Get Template Content by ID",
    description="Fetch Liquid template content from Azure Blob Storage by ID"
)
async def get_template_content_by_id(
    template_id: int,
    service: TemplateService = Depends(get_template_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Get template content from Azure Blob Storage by ID
    
    - **template_id**: ID of the template
    
    Returns the full Liquid template content
    """
    try:
        logger.info(f"User {current_user.get('sub')} fetching template content for ID: {template_id}")
        content = service.get_template_content_by_id(template_id)
        return content
    except ValidationException as e:
        logger.warning(f"Template not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except StorageException as e:
        logger.error(f"Storage error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error fetching template content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch template content: {str(e)}"
        )

@router.put(
    "/templates/{template_id}",
    response_model=SuccessResponse,
    summary="Update Template by ID",
    description="Update an existing Liquid template by uploading new file"
)
async def update_template(
    template_id: int,
    file: UploadFile = File(..., description="Updated liquid template file"),
    hie_source: Optional[str] = Form(None, description="New HIE source"),
    source_type: Optional[str] = Form(None, description="New source type"),
    service: TemplateService = Depends(get_template_service),
    current_user: dict = Depends(require_admin)
):
    """
    Update an existing template by ID
    
    - **template_id**: ID of the template to update
    - **file**: New .liquid template file
    - **hie_source**: Optional new HIE source
    - **source_type**: Optional new source type
    
    Requires admin role
    """
    try:
        # Validate file extension
        if not file.filename.endswith('.liquid'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .liquid files are allowed"
            )
        
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')
        
        logger.info(f"Admin {current_user.get('sub')} updating template ID: {template_id}")
        
        result = service.update_template_by_id(
            template_id=template_id,
            content=content_str,
            hie_source=hie_source,
            source_type=source_type
        )
        return result
        
    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseException as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except StorageException as e:
        logger.error(f"Storage error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update template: {str(e)}"
        )

@router.delete(
    "/templates/{template_id}",
    response_model=SuccessResponse,
    summary="Delete Template by ID",
    description="Delete a Liquid template from both database and Azure Blob Storage"
)
async def delete_template(
    template_id: int,
    cascade: bool = False,  # ADD THIS PARAMETER
    service: TemplateService = Depends(get_template_service),
    current_user: dict = Depends(require_admin)
):
    """
    Delete a template by ID
    
    - **template_id**: ID of the template to delete
    - **cascade**: If true, deletes all templates with the same name (default: false)
    
    Deletes from both database and Azure Blob Storage
    Requires admin role
    """
    try:
        logger.info(
            f"Admin {current_user.get('sub')} deleting template ID: {template_id} "
            f"(cascade: {cascade})"
        )
        result = service.delete_template_by_id(template_id, cascade=cascade)
        return result
    except ValidationException as e:
        logger.warning(f"Template not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DatabaseException as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except StorageException as e:
        logger.error(f"Storage error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete template: {str(e)}"
        )