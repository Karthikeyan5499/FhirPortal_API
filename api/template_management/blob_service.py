from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import (
    AzureError, 
    ResourceNotFoundError, 
    ResourceExistsError,
    ClientAuthenticationError,
    ServiceRequestError
)
from config import settings
from common.exceptions import StorageException, NotFoundException, BadRequestException, ConnectionException
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class AzureBlobStorageService:
    """
    Azure Blob Storage Service with comprehensive error handling
    """
    
    def __init__(self):
        self.blob_service_client = None
        self.container_name = settings.AZURE_CONTAINER_NAME
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure Blob Storage client with error handling"""
        try:
            if not settings.AZURE_STORAGE_CONNECTION_STRING:
                raise StorageException("Azure Storage connection string not configured")
            
            self.blob_service_client = BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING
            )
            
            # Ensure container exists
            self._ensure_container_exists()
            
            logger.info("✅ Azure Blob Storage client initialized successfully")
            
        except ClientAuthenticationError as e:
            logger.error(f"Azure Blob Storage authentication failed: {e}")
            raise StorageException("Storage authentication failed. Check your credentials.")
        
        except ValueError as e:
            logger.error(f"Invalid Azure Storage connection string: {e}")
            raise StorageException("Invalid storage connection string configuration")
        
        except Exception as e:
            logger.error(f"Failed to initialize Azure Blob Storage: {e}")
            raise StorageException(f"Storage initialization failed: {str(e)}")
    
    def _ensure_container_exists(self):
        """Ensure the container exists, create if it doesn't"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            # Check if container exists
            if not container_client.exists():
                logger.info(f"Container '{self.container_name}' does not exist. Creating...")
                container_client.create_container()
                logger.info(f"✅ Container '{self.container_name}' created successfully")
            else:
                logger.info(f"✅ Container '{self.container_name}' already exists")
                
        except ResourceExistsError:
            logger.info(f"Container '{self.container_name}' already exists")
        
        except ClientAuthenticationError as e:
            logger.error(f"Authentication error creating container: {e}")
            raise StorageException("Cannot create container: authentication failed")
        
        except Exception as e:
            logger.error(f"Error ensuring container exists: {e}")
            raise StorageException(f"Container verification failed: {str(e)}")
    
    def upload_file(self, file_name: str, file_content: bytes) -> str:
        """
        Upload file to Azure Blob Storage
        
        Args:
            file_name: Name of the file
            file_content: File content as bytes
            
        Returns:
            URL of the uploaded blob
            
        Raises:
            StorageException: If upload fails
        """
        try:
            if not file_name:
                raise BadRequestException("File name cannot be empty")
            
            if not file_content or len(file_content) == 0:
                raise BadRequestException("File content cannot be empty")
            
            # Sanitize file name
            sanitized_name = self._sanitize_filename(file_name)
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=sanitized_name
            )
            
            # Upload with overwrite
            blob_client.upload_blob(file_content, overwrite=True)
            
            blob_url = blob_client.url
            logger.info(f"✅ File uploaded successfully: {sanitized_name}")
            
            return blob_url
            
        except BadRequestException:
            raise
        
        except ClientAuthenticationError as e:
            logger.error(f"Authentication error during upload: {e}")
            raise StorageException("Upload failed: authentication error")
        
        except ServiceRequestError as e:
            logger.error(f"Network error during upload: {e}")
            raise ConnectionException("Upload failed: network error")
        
        except AzureError as e:
            logger.error(f"Azure error during upload: {e}")
            raise StorageException(f"Upload failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            raise StorageException(f"Upload failed: {str(e)}")
    
    def download_file(self, blob_name: str) -> bytes:
        """
        Download file from Azure Blob Storage
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            File content as bytes
            
        Raises:
            NotFoundException: If file not found
            StorageException: If download fails
        """
        try:
            if not blob_name:
                raise BadRequestException("Blob name cannot be empty")
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Check if blob exists
            if not blob_client.exists():
                raise NotFoundException(f"File not found in storage: {blob_name}")
            
            # Download blob
            download_stream = blob_client.download_blob()
            file_content = download_stream.readall()
            
            logger.info(f"✅ File downloaded successfully: {blob_name}")
            return file_content
            
        except NotFoundException:
            raise
        
        except BadRequestException:
            raise
        
        except ResourceNotFoundError as e:
            logger.error(f"Blob not found: {e}")
            raise NotFoundException(f"File not found: {blob_name}")
        
        except ClientAuthenticationError as e:
            logger.error(f"Authentication error during download: {e}")
            raise StorageException("Download failed: authentication error")
        
        except ServiceRequestError as e:
            logger.error(f"Network error during download: {e}")
            raise ConnectionException("Download failed: network error")
        
        except AzureError as e:
            logger.error(f"Azure error during download: {e}")
            raise StorageException(f"Download failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            raise StorageException(f"Download failed: {str(e)}")
    
    def delete_file(self, blob_name: str) -> bool:
        """
        Delete file from Azure Blob Storage
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            True if deleted successfully
            
        Raises:
            StorageException: If deletion fails
        """
        try:
            if not blob_name:
                raise BadRequestException("Blob name cannot be empty")
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Check if blob exists
            if not blob_client.exists():
                logger.warning(f"Blob does not exist, skipping deletion: {blob_name}")
                return True
            
            blob_client.delete_blob()
            logger.info(f"✅ File deleted successfully: {blob_name}")
            return True
            
        except BadRequestException:
            raise
        
        except ResourceNotFoundError:
            logger.warning(f"Blob not found during deletion: {blob_name}")
            return True
        
        except ClientAuthenticationError as e:
            logger.error(f"Authentication error during deletion: {e}")
            raise StorageException("Deletion failed: authentication error")
        
        except AzureError as e:
            logger.error(f"Azure error during deletion: {e}")
            raise StorageException(f"Deletion failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error during deletion: {e}")
            raise StorageException(f"Deletion failed: {str(e)}")
    
    def list_files(self, prefix: Optional[str] = None) -> List[Dict[str, any]]:
        """
        List all files in the container
        
        Args:
            prefix: Optional prefix to filter blobs
            
        Returns:
            List of blob information dictionaries
            
        Raises:
            StorageException: If listing fails
        """
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            blobs = []
            for blob in container_client.list_blobs(name_starts_with=prefix):
                blobs.append({
                    "name": blob.name,
                    "size": blob.size,
                    "created_at": blob.creation_time.isoformat() if blob.creation_time else None,
                    "modified_at": blob.last_modified.isoformat() if blob.last_modified else None,
                    "content_type": blob.content_settings.content_type if blob.content_settings else None
                })
            
            logger.info(f"✅ Listed {len(blobs)} files from storage")
            return blobs
            
        except ClientAuthenticationError as e:
            logger.error(f"Authentication error during listing: {e}")
            raise StorageException("Listing failed: authentication error")
        
        except AzureError as e:
            logger.error(f"Azure error during listing: {e}")
            raise StorageException(f"Listing failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error during listing: {e}")
            raise StorageException(f"Listing failed: {str(e)}")
    
    def get_blob_url(self, blob_name: str) -> str:
        """
        Get URL for a blob
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            URL of the blob
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            return blob_client.url
        except Exception as e:
            logger.error(f"Error getting blob URL: {e}")
            raise StorageException(f"Failed to get blob URL: {str(e)}")
    
    def blob_exists(self, blob_name: str) -> bool:
        """
        Check if blob exists
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            True if blob exists
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            return blob_client.exists()
        except Exception as e:
            logger.error(f"Error checking blob existence: {e}")
            return False
    
    def get_storage_info(self) -> Dict[str, any]:
        """Get information about storage configuration"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            # Count blobs
            blob_count = sum(1 for _ in container_client.list_blobs())
            
            return {
                "storage_type": "Azure Blob Storage",
                "container_name": self.container_name,
                "is_azure": True,
                "file_count": blob_count,
                "status": "connected"
            }
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {
                "storage_type": "Azure Blob Storage",
                "container_name": self.container_name,
                "is_azure": True,
                "file_count": 0,
                "status": "error",
                "error": str(e)
            }
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for blob storage"""
        # Remove or replace invalid characters
        invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        return sanitized
    
    def test_connection(self) -> bool:
        """Test Azure Blob Storage connection"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.exists()
            logger.info("✅ Azure Blob Storage connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ Azure Blob Storage connection test failed: {e}")
            return False