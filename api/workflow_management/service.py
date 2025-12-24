# api/workflow_management/service.py
import logging
import pyodbc
from typing import List, Optional, Dict, Any
from database import get_db_connection
from common.exceptions import DatabaseException
from .schemas import FileMetadataCreate, FileMetadataResponse, SourceMasterResponse
from datetime import datetime

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service layer for Workflow Management operations"""
    
    @staticmethod
    def get_all_sources() -> List[SourceMasterResponse]:
        """
        Fetch all sources from SourceMaster table for dropdown
        
        Returns:
            List of SourceMasterResponse objects
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT Id, Source, SourceType 
                    FROM dbo.SourceMaster 
                    WHERE IsActive = 1 
                    ORDER BY SourceType, Source
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                sources = [
                    SourceMasterResponse(
                        Id=row.Id,
                        Source=row.Source,
                        SourceType=row.SourceType
                    )
                    for row in rows
                ]
                
                logger.info(f"✅ Retrieved {len(sources)} sources from SourceMaster")
                return sources
                
        except pyodbc.Error as e:
            logger.error(f"❌ Database error fetching sources: {e}")
            raise DatabaseException(f"Failed to fetch sources: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching sources: {e}")
            raise DatabaseException(f"Unexpected error: {str(e)}")
    
    
    @staticmethod
    def bulk_insert_file_metadata(files: List[FileMetadataCreate]) -> Dict[str, Any]:
        """
        Bulk insert file metadata records
        
        Args:
            files: List of FileMetadataCreate objects
            
        Returns:
            Dictionary with inserted count and IDs
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                insert_query = """
                    INSERT INTO dbo.FileMetadata 
                    (Source, SourceType, FileName, FlowType, UploadedBy, Status, BundleId, ValidationStatus, Uploaded)
                    OUTPUT INSERTED.Id
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                inserted_ids = []
                
                for file_data in files:
                    cursor.execute(
                        insert_query,
                        file_data.Source,
                        file_data.SourceType,
                        file_data.FileName,
                        file_data.FlowType,
                        file_data.UploadedBy,
                        file_data.Status or "Started",
                        file_data.BundleId,
                        file_data.ValidationStatus,
                        datetime.utcnow()
                    )
                    
                    # Fetch the inserted ID
                    inserted_id = cursor.fetchone()[0]
                    inserted_ids.append(inserted_id)
                
                conn.commit()
                
                logger.info(f"✅ Bulk inserted {len(inserted_ids)} file metadata records")
                
                return {
                    "inserted_count": len(inserted_ids),
                    "file_ids": inserted_ids
                }
                
        except pyodbc.Error as e:
            logger.error(f"❌ Database error during bulk insert: {e}")
            raise DatabaseException(f"Failed to insert file metadata: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Unexpected error during bulk insert: {e}")
            raise DatabaseException(f"Unexpected error: {str(e)}")
        
    @staticmethod
    def get_all_files(
        source: Optional[str] = None,
        source_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Fetch file metadata with optional filters and pagination
        
        Args:
            source: Filter by source name
            source_type: Filter by source type
            status: Filter by status
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            Dictionary with files list and total count
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Build WHERE clause dynamically
                where_conditions = []
                params = []
                
                if source:
                    where_conditions.append("Source = ?")
                    params.append(source)
                
                if source_type:
                    where_conditions.append("SourceType = ?")
                    params.append(source_type)
                
                if status:
                    where_conditions.append("Status = ?")
                    params.append(status)
                
                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                
                # Count query
                count_query = f"SELECT COUNT(*) FROM dbo.FileMetadata WHERE {where_clause}"
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]
                
                # Data query with pagination
                data_query = f"""
                    SELECT Id, Source, SourceType, FileName, BundleId, FlowType, 
                        UploadedBy, Uploaded, Status, ValidationStatus
                    FROM dbo.FileMetadata 
                    WHERE {where_clause}
                    ORDER BY Uploaded DESC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """
                
                cursor.execute(data_query, params + [skip, limit])
                rows = cursor.fetchall()
                
                files = [
                    FileMetadataResponse(
                        Id=row.Id,
                        Source=row.Source,
                        SourceType=row.SourceType,
                        FileName=row.FileName,
                        BundleId=row.BundleId,
                        FlowType=row.FlowType,
                        UploadedBy=row.UploadedBy,
                        Uploaded=row.Uploaded,
                        Status=row.Status,
                        ValidationStatus=row.ValidationStatus
                    )
                    for row in rows
                ]
                
                logger.info(f"✅ Retrieved {len(files)} files (Total: {total_count})")
                
                return {
                    "files": files,
                    "total": total_count,
                    "skip": skip,
                    "limit": limit
                }
                
        except pyodbc.Error as e:
            logger.error(f"❌ Database error fetching files: {e}")
            raise DatabaseException(f"Failed to fetch files: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching files: {e}")
            raise DatabaseException(f"Unexpected error: {str(e)}")
