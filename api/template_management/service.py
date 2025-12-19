# api/template_management/service.py
from typing import List, Dict, Optional
import logging
from liquid import Environment, StrictUndefined
from liquid.exceptions import LiquidSyntaxError, LiquidError

from api.template_management.repository import TemplateRepository
from api.template_management.blob_service import AzureBlobStorageService
from api.template_management.schemas import (
    TemplateResponse,
    TemplateListResponse,
    TemplateContentResponse,
    TemplateValidationResponse,
    SuccessResponse
)
from common.exceptions import DatabaseException, StorageException, ValidationException

logger = logging.getLogger(__name__)

class TemplateService:
    """Business logic for template management"""
    
    def __init__(self):
        self.repository = TemplateRepository()
        self.blob_service = AzureBlobStorageService()
        self.liquid_env = Environment(undefined=StrictUndefined)
    
    def validate_liquid_syntax(self, content: str, source_type: Optional[str] = None) -> TemplateValidationResponse:
        """
        Validate Liquid template syntax with comprehensive checks
        
        Args:
            content: Liquid template content
            source_type: Source type for checking include file existence
            
        Returns:
            TemplateValidationResponse with validation results
        """
        try:
            from api.template_management.liquid_validator import LiquidTemplateValidator
            
            # Initialize validator with blob service
            validator = LiquidTemplateValidator(
                blob_service=self.blob_service,  # Pass blob service
                source_type=source_type  # Pass source type
            )
            
            # Run validation
            result = validator.validate(content)
            
            # Format response
            all_messages = []
            if result["errors"]:
                all_messages.extend(result["errors"])
            if result["warnings"]:
                all_messages.extend([f"Warning: {w}" for w in result["warnings"]])
            
            if result["valid"]:
                message = "Template syntax is valid"
                if result["warnings"]:
                    message += f" (with {len(result['warnings'])} warning(s))"
                
                return TemplateValidationResponse(
                    valid=True,
                    message=message,
                    errors=result["warnings"] if result["warnings"] else None
                )
            else:
                return TemplateValidationResponse(
                    valid=False,
                    message="Template validation failed",
                    errors=all_messages
                )
                
        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            return TemplateValidationResponse(
                valid=False,
                message="Validation failed",
                errors=[f"Validation error: {str(e)}"]
            )
    
    def _validate_source_type(self, source_type: str) -> str:
        """Validate and normalize source type"""
        allowed_types = ['HL7', 'Hl7v2', 'HL7V2', 'CDA', 'FHIR', 'X12', 'CUSTOM', 'ADT']
        
        # Normalize common variations
        source_type_normalized = source_type
        
        # Case-insensitive check
        source_type_upper = source_type.upper()
        if source_type_upper in ['HL7VS', 'HL7V2']:
            source_type_normalized = 'Hl7v2'  # Use consistent casing
        
        # Validate against allowed types (case-insensitive)
        if not any(source_type.upper() == allowed.upper() for allowed in allowed_types):
            raise ValidationException(f"Source type must be one of: {', '.join(allowed_types)}")
        
        return source_type  # Return original casing
    
    def upload_template_file(self, file_name: str, content: str, 
                            hie_source: str, source_type: str) -> SuccessResponse:
        """Upload a new Liquid template file"""
        try:
            # 1. Validate source type
            source_type = self._validate_source_type(source_type)
            
            # 2. Validate syntax WITH source_type for include checking
            validation = self.validate_liquid_syntax(content, source_type=source_type)
            if not validation.valid:
                raise ValidationException(f"Invalid template syntax: {validation.errors}")
            
            # 3. Ensure .liquid extension
            template_name = file_name if file_name.endswith('.liquid') else f"{file_name}.liquid"
            
            # 4. Check for duplicate (NEW)
            is_duplicate = self.repository.check_duplicate_template(
                template_name, hie_source, source_type
            )
            
            if is_duplicate:
                raise ValidationException(
                    f"Template '{template_name}' already exists for HIE source '{hie_source}' "
                    f"and source type '{source_type}'. Please use update endpoint or choose a different name."
                )
            
            # 5. Create unique blob path
            blob_path = f"{source_type}/{template_name}"
            
            # 6. Upload to Azure Blob Storage
            azure_url = self.blob_service.upload_template_with_path(blob_path, content)
            
            # 7. Save metadata to database
            template_id = self.repository.create_template(
                hie_source=hie_source,
                source_type=source_type,
                liquid_template=template_name,
                azure_storage_path=azure_url
            )
            
            logger.info(f"Successfully uploaded template: {template_name} with ID: {template_id}")
            
            return SuccessResponse(
                success=True,
                message="Template uploaded successfully",
                data={
                    "id": template_id,
                    "template_name": template_name,
                    "hie_source": hie_source,
                    "azure_storage_path": azure_url
                }
            )
            
        except ValidationException:
            raise
        except (DatabaseException, StorageException):
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading template: {e}")
            raise Exception(f"Failed to upload template: {str(e)}")
    
    def list_templates_with_filters(self, hie_source: Optional[str] = None,
                                    source_type: Optional[str] = None,
                                    template_name: Optional[str] = None) -> List[TemplateListResponse]:
        """
        List templates with optional filters
        
        Args:
            hie_source: Filter by HIE source
            source_type: Filter by source type
            template_name: Filter by template name
            
        Returns:
            List of TemplateListResponse
        """
        try:
            templates = self.repository.get_templates_with_filters(
                hie_source=hie_source,
                source_type=source_type,
                template_name=template_name
            )
            
            logger.info(f"Listed {len(templates)} templates with filters")
            return [TemplateListResponse(**template) for template in templates]
            
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            raise Exception(f"Failed to list templates: {str(e)}")
    
    def get_template_by_id(self, template_id: int) -> TemplateResponse:
        """
        Get template metadata by ID
        
        Args:
            template_id: ID of the template
            
        Returns:
            TemplateResponse with template data
        """
        try:
            template_record = self.repository.get_template_by_id(template_id)
            if not template_record:
                raise ValidationException(f"Template with ID {template_id} not found")
            
            logger.info(f"Retrieved template ID: {template_id}")
            return TemplateResponse(**template_record)
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving template: {e}")
            raise Exception(f"Failed to retrieve template: {str(e)}")
    
    def get_templates_by_name(self, template_name: str, 
                             hie_source: Optional[str] = None) -> List[TemplateResponse]:
        """
        Get all templates with the same name (across different sources)
        
        Args:
            template_name: Name of the template
            hie_source: Optional filter by HIE source
            
        Returns:
            List of TemplateResponse
        """
        try:
            # Ensure .liquid extension
            if not template_name.endswith('.liquid'):
                template_name = f"{template_name}.liquid"
            
            templates = self.repository.get_templates_by_name(template_name, hie_source)
            
            if not templates:
                raise ValidationException(f"No templates found with name '{template_name}'")
            
            logger.info(f"Retrieved {len(templates)} templates with name: {template_name}")
            return [TemplateResponse(**template) for template in templates]
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving templates: {e}")
            raise Exception(f"Failed to retrieve templates: {str(e)}")
    
    def get_template_content_by_id(self, template_id: int) -> TemplateContentResponse:
        """
        Fetch template content from Azure Blob Storage by ID
        
        Args:
            template_id: ID of the template
            
        Returns:
            TemplateContentResponse with content
        """
        try:
            # Get template metadata
            template_record = self.repository.get_template_by_id(template_id)
            if not template_record:
                raise ValidationException(f"Template with ID {template_id} not found")
            
            # Download from Azure Blob Storage using the stored path
            azure_path = template_record['azure_storage_path']
            content = self.blob_service.download_template_by_path(azure_path)
            
            logger.info(f"Successfully retrieved content for template ID: {template_id}")
            
            return TemplateContentResponse(
                template_name=template_record['template_name'],
                content=content
            )
            
        except ValidationException:
            raise
        except StorageException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving template: {e}")
            raise Exception(f"Failed to retrieve template: {str(e)}")
    
    def update_template_by_id(self, template_id: int, content: str,
                             hie_source: Optional[str] = None,
                             source_type: Optional[str] = None) -> SuccessResponse:
        """
        Update an existing template by ID
        
        Args:
            template_id: ID of the template to update
            content: New template content
            hie_source: Optional new HIE source
            source_type: Optional new source type
            
        Returns:
            SuccessResponse
        """
        try:
            # Get existing template
            template_record = self.repository.get_template_by_id(template_id)
            if not template_record:
                raise ValidationException(f"Template with ID {template_id} not found")
            
            # Validate new content
            validation = self.validate_liquid_syntax(content)
            if not validation.valid:
                raise ValidationException(f"Invalid template syntax: {validation.errors}")
            
            # Validate source type if provided
            if source_type:
                source_type = self._validate_source_type(source_type)
            
            # Upload new content to Azure Blob Storage (same path)
            azure_path = template_record['azure_storage_path']
            self.blob_service.upload_template_with_path(azure_path, content)
            
            # Update database record
            self.repository.update_template_by_id(
                template_id=template_id,
                hie_source=hie_source,
                source_type=source_type
            )
            
            logger.info(f"Successfully updated template ID: {template_id}")
            
            return SuccessResponse(
                success=True,
                message="Template updated successfully",
                data={"template_id": template_id}
            )
            
        except ValidationException:
            raise
        except (DatabaseException, StorageException):
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating template: {e}")
            raise Exception(f"Failed to update template: {str(e)}")
    
    def delete_template_by_id(self, template_id: int, cascade: bool = False) -> SuccessResponse:
        """
        Delete a template by ID
        
        Args:
            template_id: ID of the template to delete
            cascade: If True, delete all templates with the same name
            
        Returns:
            SuccessResponse
        """
        try:
            # Get template to find blob path and name
            template_record = self.repository.get_template_by_id(template_id)
            if not template_record:
                raise ValidationException(f"Template with ID {template_id} not found")
            
            template_name = template_record['template_name']
            
            if cascade:
                # Cascade delete: delete all templates with same name
                deleted_templates = self.repository.delete_templates_by_name(template_name)
                
                # Delete from Azure Blob Storage for each
                for template in deleted_templates:
                    try:
                        azure_path = template['azure_storage_path']
                        self.blob_service.delete_template_by_path(azure_path)
                    except StorageException as e:
                        logger.warning(f"Failed to delete blob for template ID {template['id']}: {e}")
                
                logger.info(f"Cascade deleted {len(deleted_templates)} templates with name: {template_name}")
                
                return SuccessResponse(
                    success=True,
                    message=f"Cascade deleted {len(deleted_templates)} template(s) successfully",
                    data={
                        "deleted_count": len(deleted_templates),
                        "template_name": template_name,
                        "deleted_ids": [t['id'] for t in deleted_templates]
                    }
                )
            else:
                # Single delete
                self.repository.delete_template_by_id(template_id)
                
                # Delete from Azure Blob Storage
                azure_path = template_record['azure_storage_path']
                self.blob_service.delete_template_by_path(azure_path)
                
                logger.info(f"Successfully deleted template ID: {template_id}")
                
                return SuccessResponse(
                    success=True,
                    message="Template deleted successfully",
                    data={"template_id": template_id}
                )
            
        except ValidationException:
            raise
        except (DatabaseException, StorageException):
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting template: {e}")
            raise Exception(f"Failed to delete template: {str(e)}")