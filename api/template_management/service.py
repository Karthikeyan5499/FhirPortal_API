from .repository import TemplateRepository
from .blob_service import AzureBlobStorageService
from .schemas import (
    TemplateCreate, 
    TemplateUpdate, 
    TemplateSearchRequest,
    TemplateValidationRequest,
    TemplateTransformRequest,
    BulkTemplateActivateRequest
)
from common.exceptions import (
    BadRequestException, 
    NotFoundException, 
    ValidationException,
    StorageException
)
from typing import Optional, List
import mimetypes
import logging

logger = logging.getLogger(__name__)

class TemplateService:
    
    def __init__(self):
        try:
            self.repository = TemplateRepository()
            self.blob_service = AzureBlobStorageService()
            logger.info("✅ TemplateService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TemplateService: {e}")
            raise
    
    def get_all_templates(
        self,
        template_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
        search_query: Optional[str] = None
    ):
        """Get all templates with filtering and pagination"""
        try:
            logger.info(f"Fetching templates: type={template_type}, active={is_active}, page={page}, search={search_query}")
            return self.repository.get_all(template_type, is_active, page, page_size, search_query)
        except Exception as e:
            logger.error(f"Error in get_all_templates: {e}")
            raise
    
    def search_templates(self, search_request: TemplateSearchRequest):
        """Advanced template search"""
        try:
            logger.info(f"Searching templates with request: {search_request}")
            
            return self.repository.get_all(
                template_type=search_request.template_type.value if search_request.template_type else None,
                is_active=search_request.is_active,
                page=search_request.page,
                page_size=search_request.page_size,
                search_query=search_request.query
            )
        except Exception as e:
            logger.error(f"Error in search_templates: {e}")
            raise
    
    def get_template(self, template_id: int, user_id: Optional[int] = None):
        """Get template by ID and log usage"""
        try:
            logger.info(f"Fetching template {template_id}")
            template = self.repository.get_by_id(template_id)
            
            if user_id:
                try:
                    self.repository.log_usage(template_id, user_id, 'view')
                except Exception as e:
                    logger.warning(f"Failed to log usage: {e}")
            
            return template
        except Exception as e:
            logger.error(f"Error in get_template: {e}")
            raise
    
    def create_template(self, template: TemplateCreate, user_id: int):
        """Create new template"""
        try:
            logger.info(f"Creating template: {template.name}")
            
            # Validate template data
            if not template.name or len(template.name.strip()) < 3:
                raise ValidationException("Template name must be at least 3 characters")
            
            template_dict = template.model_dump()
            
            # Convert enum to string
            if hasattr(template_dict['template_type'], 'value'):
                template_dict['template_type'] = template_dict['template_type'].value
            
            result = self.repository.create(template_dict, user_id)
            logger.info(f"✅ Template created successfully: {result['id']}")
            return result
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error in create_template: {e}")
            raise
    
    def update_template(self, template_id: int, template: TemplateUpdate):
        """Update template"""
        try:
            logger.info(f"Updating template {template_id}")
            
            template_dict = {k: v for k, v in template.model_dump().items() if v is not None}
            
            if not template_dict:
                raise ValidationException("No fields to update")
            
            # Validate name if provided
            if 'name' in template_dict and len(template_dict['name'].strip()) < 3:
                raise ValidationException("Template name must be at least 3 characters")
            
            # Convert enum to string if present
            if 'template_type' in template_dict and hasattr(template_dict['template_type'], 'value'):
                template_dict['template_type'] = template_dict['template_type'].value
            
            result = self.repository.update(template_id, template_dict)
            logger.info(f"✅ Template {template_id} updated successfully")
            return result
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error in update_template: {e}")
            raise
    
    def delete_template(self, template_id: int):
        """Delete template and associated file"""
        try:
            logger.info(f"Deleting template {template_id}")
            
            # Get template to delete associated file
            try:
                template = self.repository.get_by_id(template_id)
            except NotFoundException:
                raise
            
            # Delete file from storage if exists
            if template.get('file_name'):
                try:
                    logger.info(f"Deleting blob: {template['file_name']}")
                    self.blob_service.delete_file(template['file_name'])
                    logger.info(f"✅ Blob deleted: {template['file_name']}")
                except StorageException as e:
                    logger.warning(f"Failed to delete blob (continuing): {e}")
                except Exception as e:
                    logger.warning(f"Unexpected error deleting blob (continuing): {e}")
            
            # Delete template record
            result = self.repository.delete(template_id)
            logger.info(f"✅ Template {template_id} deleted successfully")
            return result
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error in delete_template: {e}")
            raise
    
    def upload_template_file(self, template_id: int, file_name: str, file_content: bytes, user_id: int):
        """Upload file for template"""
        try:
            logger.info(f"Uploading file for template {template_id}: {file_name}")
            
            # Validate inputs
            if not file_name:
                raise ValidationException("File name cannot be empty")
            
            if not file_content or len(file_content) == 0:
                raise ValidationException("File content cannot be empty")
            
            # Validate file size (max 50MB)
            max_size = 50 * 1024 * 1024  # 50MB
            if len(file_content) > max_size:
                raise ValidationException(f"File size exceeds maximum limit of 50MB")
            
            # Get template
            try:
                template = self.repository.get_by_id(template_id)
            except NotFoundException:
                raise
            
            # Upload to blob storage
            try:
                blob_url = self.blob_service.upload_file(file_name, file_content)
            except StorageException as e:
                logger.error(f"Blob upload failed: {e}")
                raise
            
            if not blob_url:
                raise StorageException("Blob upload returned empty URL")
            
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(file_name)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Update template with file info
            try:
                self.repository.update(template_id, {
                    'file_url': blob_url,
                    'file_name': file_name,
                    'file_size': len(file_content),
                    'mime_type': mime_type
                })
            except Exception as e:
                logger.error(f"Failed to update template with file info: {e}")
                # Try to delete uploaded blob
                try:
                    self.blob_service.delete_file(file_name)
                except:
                    pass
                raise
            
            # Create version entry
            try:
                self.repository.create_version(
                    template_id=template_id,
                    version=template['version'],
                    file_url=blob_url,
                    change_description=f"Uploaded file: {file_name}",
                    user_id=user_id
                )
            except Exception as e:
                logger.warning(f"Failed to create version entry: {e}")
            
            # Log usage
            try:
                self.repository.log_usage(template_id, user_id, 'upload')
            except Exception as e:
                logger.warning(f"Failed to log usage: {e}")
            
            logger.info(f"✅ File uploaded successfully for template {template_id}")
            return blob_url
            
        except ValidationException:
            raise
        except NotFoundException:
            raise
        except StorageException:
            raise
        except Exception as e:
            logger.error(f"Error in upload_template_file: {e}")
            raise BadRequestException(f"File upload failed: {str(e)}")
    
    def download_template_file(self, template_id: int, user_id: int):
        """Download template file"""
        try:
            logger.info(f"Downloading file for template {template_id}")
            
            # Get template
            try:
                template = self.repository.get_by_id(template_id)
            except NotFoundException:
                raise
            
            if not template.get('file_name'):
                raise NotFoundException("No file attached to this template")
            
            # Download from blob storage
            try:
                file_content = self.blob_service.download_file(template['file_name'])
            except NotFoundException:
                raise
            except StorageException as e:
                logger.error(f"Blob download failed: {e}")
                raise
            
            if not file_content:
                raise NotFoundException("File not found in storage")
            
            # Log download and increment usage
            try:
                self.repository.log_usage(template_id, user_id, 'download')
                self.repository.increment_usage(template_id)
            except Exception as e:
                logger.warning(f"Failed to log usage: {e}")
            
            logger.info(f"✅ File downloaded successfully for template {template_id}")
            return file_content, template['file_name'], template.get('mime_type', 'application/octet-stream')
            
        except NotFoundException:
            raise
        except StorageException:
            raise
        except Exception as e:
            logger.error(f"Error in download_template_file: {e}")
            raise BadRequestException(f"File download failed: {str(e)}")
    
    def get_template_versions(self, template_id: int):
        """Get all versions of a template"""
        try:
            logger.info(f"Fetching versions for template {template_id}")
            
            # Verify template exists
            self.repository.get_by_id(template_id)
            
            versions = self.repository.get_versions(template_id)
            logger.info(f"✅ Fetched {len(versions)} versions for template {template_id}")
            return versions
            
        except Exception as e:
            logger.error(f"Error in get_template_versions: {e}")
            raise
    
    def get_usage_logs(self, template_id: int, limit: int = 100):
        """Get usage logs for a template"""
        try:
            logger.info(f"Fetching usage logs for template {template_id}")
            
            # Verify template exists
            self.repository.get_by_id(template_id)
            
            if limit < 1 or limit > 1000:
                raise ValidationException("Limit must be between 1 and 1000")
            
            logs = self.repository.get_usage_logs(template_id, limit)
            logger.info(f"✅ Fetched {len(logs)} usage logs for template {template_id}")
            return logs
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error in get_usage_logs: {e}")
            raise
    
    def get_statistics(self):
        """Get template statistics"""
        try:
            logger.info("Fetching template statistics")
            stats = self.repository.get_statistics()
            logger.info("✅ Statistics fetched successfully")
            return stats
        except Exception as e:
            logger.error(f"Error in get_statistics: {e}")
            raise
    
    def validate_data(self, request: TemplateValidationRequest):
        """Validate data against template structure"""
        try:
            logger.info(f"Validating data against template {request.template_id}")
            
            template = self.repository.get_by_id(request.template_id)
            
            errors = []
            warnings = []
            
            if not template.get('file_url'):
                warnings.append("Template has no schema file for validation")
            
            if not request.data:
                errors.append("Data cannot be empty")
            
            # Type-specific validation
            template_type = template['template_type']
            
            if template_type == 'FHIR':
                if 'resourceType' not in request.data:
                    errors.append("FHIR resource must have 'resourceType' field")
            elif template_type == 'HL7':
                if not isinstance(request.data, dict):
                    errors.append("HL7 message must be a valid dictionary")
            elif template_type == 'CDA':
                if 'ClinicalDocument' not in request.data:
                    errors.append("CDA document must have 'ClinicalDocument' root element")
            
            # Log validation
            try:
                self.repository.log_usage(request.template_id, 0, 'validate')
            except Exception as e:
                logger.warning(f"Failed to log validation: {e}")
            
            result = {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "template_name": template['name'],
                "template_version": template['version']
            }
            
            logger.info(f"✅ Validation completed: valid={result['valid']}")
            return result
            
        except Exception as e:
            logger.error(f"Error in validate_data: {e}")
            raise
    
    def transform_data(self, request: TemplateTransformRequest):
        """Transform data from one template format to another"""
        try:
            logger.info(f"Transforming data from template {request.source_template_id} to {request.target_template_id}")
            
            source_template = self.repository.get_by_id(request.source_template_id)
            target_template = self.repository.get_by_id(request.target_template_id)
            
            errors = []
            transformed_data = None
            
            source_type = source_template['template_type']
            target_type = target_template['template_type']
            
            if source_type == target_type:
                transformed_data = request.data
            else:
                if source_type == 'HL7' and target_type == 'FHIR':
                    transformed_data = self._transform_hl7_to_fhir(request.data)
                elif source_type == 'FHIR' and target_type == 'HL7':
                    transformed_data = self._transform_fhir_to_hl7(request.data)
                elif source_type == 'CDA' and target_type == 'FHIR':
                    transformed_data = self._transform_cda_to_fhir(request.data)
                else:
                    errors.append(f"Transformation from {source_type} to {target_type} not yet implemented")
                    transformed_data = request.data
            
            # Log transformations
            try:
                self.repository.log_usage(request.source_template_id, 0, 'transform')
                self.repository.log_usage(request.target_template_id, 0, 'transform')
            except Exception as e:
                logger.warning(f"Failed to log transformation: {e}")
            
            result = {
                "success": len(errors) == 0,
                "transformed_data": transformed_data,
                "errors": errors,
                "source_template": f"{source_template['name']} ({source_type})",
                "target_template": f"{target_template['name']} ({target_type})"
            }
            
            logger.info(f"✅ Transformation completed: success={result['success']}")
            return result
            
        except Exception as e:
            logger.error(f"Error in transform_data: {e}")
            raise
    
    def _transform_hl7_to_fhir(self, hl7_data: dict) -> dict:
        """Transform HL7 v2 to FHIR"""
        try:
            fhir_resource = {
                "resourceType": "Patient",
                "id": hl7_data.get("PID", {}).get("patient_id"),
                "name": [{
                    "family": hl7_data.get("PID", {}).get("family_name"),
                    "given": [hl7_data.get("PID", {}).get("given_name")]
                }],
                "birthDate": hl7_data.get("PID", {}).get("birth_date"),
                "gender": hl7_data.get("PID", {}).get("gender", "unknown").lower()
            }
            return fhir_resource
        except Exception as e:
            logger.error(f"Error transforming HL7 to FHIR: {e}")
            return hl7_data
    
    def _transform_fhir_to_hl7(self, fhir_data: dict) -> dict:
        """Transform FHIR to HL7 v2"""
        try:
            hl7_message = {
                "MSH": {"message_type": "ADT", "version": "2.5"},
                "PID": {
                    "patient_id": fhir_data.get("id"),
                    "family_name": fhir_data.get("name", [{}])[0].get("family"),
                    "given_name": fhir_data.get("name", [{}])[0].get("given", [""])[0],
                    "birth_date": fhir_data.get("birthDate"),
                    "gender": fhir_data.get("gender", "U").upper()
                }
            }
            return hl7_message
        except Exception as e:
            logger.error(f"Error transforming FHIR to HL7: {e}")
            return fhir_data
    
    def _transform_cda_to_fhir(self, cda_data: dict) -> dict:
        """Transform CDA to FHIR"""
        try:
            clinical_doc = cda_data.get("ClinicalDocument", {})
            fhir_bundle = {
                "resourceType": "Bundle",
                "type": "document",
                "entry": [{
                    "resource": {
                        "resourceType": "Composition",
                        "status": "final",
                        "type": clinical_doc.get("code"),
                        "title": clinical_doc.get("title"),
                        "date": clinical_doc.get("effectiveTime")
                    }
                }]
            }
            return fhir_bundle
        except Exception as e:
            logger.error(f"Error transforming CDA to FHIR: {e}")
            return cda_data
    
    def bulk_activate(self, request: BulkTemplateActivateRequest):
        """Bulk activate/deactivate templates"""
        try:
            logger.info(f"Bulk activating {len(request.template_ids)} templates")
            
            if not request.template_ids:
                raise ValidationException("No template IDs provided")
            
            if len(request.template_ids) > 100:
                raise ValidationException("Cannot process more than 100 templates at once")
            
            updated_count = self.repository.bulk_update_status(
                request.template_ids, 
                request.is_active
            )
            
            result = {
                "updated_count": updated_count,
                "template_ids": request.template_ids,
                "is_active": request.is_active
            }
            
            logger.info(f"✅ Bulk activation completed: {updated_count} templates updated")
            return result
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error in bulk_activate: {e}")
            raise
    
    def get_templates_by_type(self, template_type: str):
        """Get templates filtered by type"""
        try:
            logger.info(f"Fetching templates by type: {template_type}")
            result = self.repository.get_all(template_type=template_type)
            logger.info(f"✅ Fetched {len(result['templates'])} templates of type {template_type}")
            return result['templates']
        except Exception as e:
            logger.error(f"Error in get_templates_by_type: {e}")
            raise
    
    def clone_template(self, template_id: int, new_name: str, user_id: int):
        """Clone an existing template"""
        try:
            logger.info(f"Cloning template {template_id} with new name: {new_name}")
            
            if not new_name or len(new_name.strip()) < 3:
                raise ValidationException("New template name must be at least 3 characters")
            
            original = self.repository.get_by_id(template_id)
            
            cloned_data = {
                'name': new_name.strip(),
                'description': f"Cloned from: {original['name']}",
                'template_type': original['template_type'],
                'version': original['version'],
                'is_active': False,
                'tags': original.get('tags', [])
            }
            
            new_template = self.repository.create(cloned_data, user_id)
            
            # Copy file if exists
            if original.get('file_name'):
                try:
                    file_content = self.blob_service.download_file(original['file_name'])
                    if file_content:
                        new_file_name = f"clone_{original['file_name']}"
                        self.upload_template_file(
                            new_template['id'], 
                            new_file_name, 
                            file_content, 
                            user_id
                        )
                except Exception as e:
                    logger.warning(f"Failed to copy file during cloning: {e}")
            
            logger.info(f"✅ Template cloned successfully: {new_template['id']}")
            return new_template
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error in clone_template: {e}")
            raise