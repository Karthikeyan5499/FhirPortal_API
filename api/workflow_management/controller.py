# api/workflow_management/controller.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import logging
from .service import WorkflowService
from .schemas import (
    SourceMasterResponse,
    FileMetadataBulkCreate,
    BulkInsertResponse,
    FileMetadataResponse,
    FileListResponse
)
from dependencies import get_current_user
from common.exceptions import DatabaseException

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/sources",
    response_model=List[SourceMasterResponse],
    summary="Get all sources for dropdown",
    description="Fetch all Source and SourceType from SourceMaster table for UI dropdown"
)
async def get_sources(current_user: dict = Depends(get_current_user)):
    """
    **Get all sources from SourceMaster table**
    
    Used for populating dropdowns in UI with available sources and source types.
    
    Returns:
        List of sources with Id, Source, and SourceType
    """
    try:
        sources = WorkflowService.get_all_sources()
        return sources
    except DatabaseException as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sources: {str(e)}"
        )


@router.post(
    "/files/bulk-insert",
    response_model=BulkInsertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk insert file metadata",
    description="Insert multiple file metadata records when files are ready to upload"
)
async def bulk_insert_files(
    request: FileMetadataBulkCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    **Bulk insert file metadata into FileMetadata table**
    
    Frontend sends a list of file metadata when files are ready to upload.
    This endpoint inserts all records in a single transaction.
    
    Example Request Body:
```json
    {
      "files": [
        {
          "Source": "PAHSX-ADT",
          "SourceType": "ADT",
          "FileName": "adt_file_001.hl7",
          "FlowType": "Input to LFS",
          "UploadedBy": "User1",
          "Status": "Started"
        },
        {
          "Source": "PAHSX-ORU",
          "SourceType": "ORU",
          "FileName": "oru_file_001.hl7",
          "FlowType": "Input to FHIR",
          "UploadedBy": "User3",
          "Status": "Started"
        }
      ]
    }
```
    
    Returns:
        - message: Success message
        - inserted_count: Number of records inserted
        - file_ids: List of generated IDs for inserted records
    """
    try:
        if not request.files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided in request"
            )
        
        result = WorkflowService.bulk_insert_file_metadata(request.files)
        
        return BulkInsertResponse(
            message="File metadata inserted successfully",
            inserted_count=result["inserted_count"],
            file_ids=result["file_ids"]
        )
        
    except DatabaseException as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to insert file metadata: {str(e)}"
        )

@router.get(
    "/files",
    response_model=FileListResponse,
    summary="Get list of files",
    description="Fetch file metadata with optional filters and pagination"
)
async def get_files(
    source: Optional[str] = Query(None, description="Filter by source name"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    current_user: dict = Depends(get_current_user)
):
    """
    **Get list of files from FileMetadata table**
    
    Supports filtering by source, source_type, and status.
    Results are paginated and ordered by upload time (newest first).
    
    Query Parameters:
        - source: Filter by source name (optional)
        - source_type: Filter by source type (optional)
        - status: Filter by processing status (optional)
        - skip: Number of records to skip for pagination (default: 0)
        - limit: Maximum number of records to return (default: 100, max: 1000)
    
    Returns:
        - files: List of file metadata records
        - total: Total number of matching records
        - skip: Current skip value
        - limit: Current limit value
    """
    try:
        result = WorkflowService.get_all_files(
            source=source,
            source_type=source_type,
            status=status,
            skip=skip,
            limit=limit
        )
        
        return FileListResponse(**result)
        
    except DatabaseException as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch files: {str(e)}"
        )