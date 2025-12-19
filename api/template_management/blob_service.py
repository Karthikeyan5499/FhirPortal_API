# api/template_management/blob_service.py
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import AzureError, ResourceNotFoundError
from urllib.parse import urlparse
from config import settings
from common.exceptions import StorageException
import logging
from typing import Optional,List

logger = logging.getLogger(__name__)

class AzureBlobStorageService:
    """Service for managing files in Azure Blob Storage"""
    
    def __init__(self, container_type: str = "liquid"):
        """
        Initialize blob service using connection string
        
        Args:
            container_type: 'liquid' for templates, 'input' for input files
        """
        try:
            # Get connection string from config
            connection_string = settings.BLOB_CONNECTION_STRING
            
            logger.info(f"🔗 Connecting to blob storage (container type: {container_type})")
            
            # Create BlobServiceClient from connection string
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            
            # Get container name based on type
            if container_type == "liquid":
                self.container_name = settings.get_liquid_container()
            elif container_type == "input":
                self.container_name = settings.get_input_container()
            else:
                raise ValueError(f"Invalid container_type: {container_type}")
            
            self.container_type = container_type
            
            logger.info(f"✅ Blob service initialized for container: {self.container_name}")
            
            # Ensure container exists
            self._ensure_container_exists()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Azure Blob Storage: {e}")
            raise StorageException(f"Storage initialization failed: {str(e)}")
    
    def _ensure_container_exists(self):
        """Create container if it doesn't exist"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not container_client.exists():
                container_client.create_container()
                logger.info(f"Created container: {self.container_name}")
        except Exception as e:
            logger.error(f"Error ensuring container exists: {e}")
            raise StorageException(f"Container setup failed: {str(e)}")
    
    def upload_template_with_path(self, blob_path: str, content: str) -> str:
        """
        Upload or update a Liquid template to Azure Blob Storage with custom path
        
        Args:
            blob_path: Full blob path (e.g., "Hl7v2/SIU_S15.liquid")
            content: Template content as string
            
        Returns:
            Full Azure Blob URL
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_path
            )
            
            # Upload with overwrite - FIX: Use ContentSettings object
            from azure.storage.blob import ContentSettings
            
            blob_client.upload_blob(
                content.encode('utf-8'),
                overwrite=True,
                content_settings=ContentSettings(content_type='text/plain')  # Fixed
            )
            
            # Return full blob URL
            full_url = blob_client.url
            logger.info(f"Successfully uploaded template: {full_url}")
            
            return full_url
            
        except AzureError as e:
            logger.error(f"Azure Storage error uploading template: {e}")
            raise StorageException(f"Failed to upload template: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error uploading template: {e}")
            raise StorageException(f"Template upload failed: {str(e)}")
    
    def download_template_by_path(self, azure_storage_path: str) -> str:
        """
        Download a Liquid template from Azure Blob Storage using full blob URL
        
        Args:
            azure_storage_path: Full Azure blob URL
            
        Returns:
            Template content as string
        """
        try:
            # Extract blob name from full URL
            # URL format: https://{account}.blob.core.windows.net/{container}/{blob_path}
            from urllib.parse import urlparse
            
            parsed_url = urlparse(azure_storage_path)
            path_parts = parsed_url.path.strip('/').split('/', 1)
            
            if len(path_parts) < 2:
                raise StorageException(f"Invalid blob URL format: {azure_storage_path}")
            
            blob_path = path_parts[1]  # Get blob path after container name
            
            # Use authenticated blob service client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_path
            )
            
            # Download blob content
            blob_data = blob_client.download_blob()
            content = blob_data.readall().decode('utf-8')
            
            logger.info(f"Successfully downloaded template: {blob_path}")
            return content
            
        except ResourceNotFoundError:
            logger.warning(f"Template not found: {azure_storage_path}")
            raise StorageException(f"Template not found in storage")
        except AzureError as e:
            logger.error(f"Azure Storage error downloading template: {e}")
            raise StorageException(f"Failed to download template: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error downloading template: {e}")
            raise StorageException(f"Template download failed: {str(e)}")
    
    def delete_template_by_path(self, azure_storage_path: str) -> bool:
        """
        Delete a Liquid template from Azure Blob Storage using full blob URL
        
        Args:
            azure_storage_path: Full Azure blob URL
            
        Returns:
            True if successful
        """
        try:
            # Extract blob name from full URL
            from urllib.parse import urlparse
            
            parsed_url = urlparse(azure_storage_path)
            path_parts = parsed_url.path.strip('/').split('/', 1)
            
            if len(path_parts) < 2:
                raise StorageException(f"Invalid blob URL format: {azure_storage_path}")
            
            blob_path = path_parts[1]  # Get blob path after container name
            
            # Use authenticated blob service client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_path
            )
            
            blob_client.delete_blob()
            logger.info(f"Successfully deleted template: {blob_path}")
            
            return True
            
        except ResourceNotFoundError:
            logger.warning(f"Template not found for deletion: {azure_storage_path}")
            raise StorageException(f"Template not found")
        except AzureError as e:
            logger.error(f"Azure Storage error deleting template: {e}")
            raise StorageException(f"Failed to delete template: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error deleting template: {e}")
            raise StorageException(f"Template deletion failed: {str(e)}")
    
    def list_templates(self, prefix: Optional[str] = None) -> list:
        """
        List all templates in the container with optional prefix
        
        Args:
            prefix: Optional prefix to filter blobs (e.g., "Hospital_XYZ/")
            
        Returns:
            List of blob paths
        """
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            
            if prefix:
                blobs = container_client.list_blobs(name_starts_with=prefix)
            else:
                blobs = container_client.list_blobs()
            
            template_paths = [blob.name for blob in blobs if blob.name.endswith('.liquid')]
            
            logger.info(f"Found {len(template_paths)} templates in storage")
            return template_paths
            
        except AzureError as e:
            logger.error(f"Azure Storage error listing templates: {e}")
            raise StorageException(f"Failed to list templates: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error listing templates: {e}")
            raise StorageException(f"Template listing failed: {str(e)}")
    
    def check_blob_exists(self, blob_path: str) -> bool:
        """
        Check if a blob exists in Azure Blob Storage
        
        Args:
            blob_path: Path to the blob (e.g., "HL7/Resource/_Organization.liquid")
            
        Returns:
            True if blob exists, False otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_path
            )
            return blob_client.exists()
        except Exception as e:
            logger.error(f"Error checking blob existence: {e}")
            return False

    def list_all_blobs_in_folder(self, folder_prefix: str) -> List[str]:
        """
        List all blobs in a specific folder
        
        Args:
            folder_prefix: Folder path (e.g., "HL7/Resource/")
            
        Returns:
            List of blob names
        """
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            
            blobs = container_client.list_blobs(name_starts_with=folder_prefix)
            blob_names = [blob.name for blob in blobs]
            
            return blob_names
        except Exception as e:
            logger.error(f"Error listing blobs in folder: {e}")
            return []
        
    def test_connection(self) -> bool:
        """Test Azure Blob Storage connection"""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            container_client.get_container_properties()
            logger.info("✅ Azure Blob Storage connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ Azure Blob Storage connection test failed: {e}")
            return False