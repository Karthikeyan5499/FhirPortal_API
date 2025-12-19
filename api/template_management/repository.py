# api/template_management/repository.py
import pyodbc
from typing import Optional, List, Dict
from database import get_db_connection
from common.exceptions import DatabaseException
import logging

logger = logging.getLogger(__name__)

class TemplateRepository:
    """Repository for database operations on TemplateConfig table"""
    
    @staticmethod
    def create_template(hie_source: str, source_type: str, liquid_template: str, azure_storage_path: str) -> int:
        """
        Insert a new template record into the database
        
        Args:
            hie_source: HIE source identifier
            source_type: Source type (HL7, CDA, etc.)
            liquid_template: Template name
            azure_storage_path: Path in Azure Blob Storage
            
        Returns:
            ID of the newly created record
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    INSERT INTO dbo.TemplateConfig 
                    (HieSource, SourceType, LiquidTemplate, AzureStoragePath)
                    OUTPUT INSERTED.Id
                    VALUES (?, ?, ?, ?)
                """

                cursor.execute(query, (hie_source, source_type, liquid_template, azure_storage_path))
                result = cursor.fetchone()

                if result is None:
                    conn.commit()
                    raise DatabaseException("Failed to retrieve inserted template ID")

                template_id = int(result[0])
                conn.commit()
                logger.info(f"Created template record with ID: {template_id}")
                
                return template_id
                
        except Exception as e:
            logger.error(f"Error creating template record: {e}")
            raise DatabaseException(f"Failed to create template: {str(e)}")
    
    @staticmethod
    def get_template_by_id(template_id: int) -> Optional[Dict]:
        """
        Retrieve a template record by ID
        
        Args:
            template_id: ID of the template
            
        Returns:
            Dictionary with template data or None
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT Id, HieSource, SourceType, LiquidTemplate, AzureStoragePath
                    FROM dbo.TemplateConfig
                    WHERE Id = ?
                """
                
                cursor.execute(query, (template_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        "id": row[0],
                        "hie_source": row[1],
                        "source_type": row[2],
                        "template_name": row[3],
                        "azure_storage_path": row[4]
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error fetching template by ID: {e}")
            raise DatabaseException(f"Failed to fetch template: {str(e)}")
    
    @staticmethod
    def get_templates_by_name(template_name: str, hie_source: Optional[str] = None) -> List[Dict]:
        """
        Retrieve all template records with the same name (possibly across different sources)
        
        Args:
            template_name: Name of the template
            hie_source: Optional filter by HIE source
            
        Returns:
            List of dictionaries with template data
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                if hie_source:
                    query = """
                        SELECT Id, HieSource, SourceType, LiquidTemplate, AzureStoragePath
                        FROM dbo.TemplateConfig
                        WHERE LiquidTemplate = ? AND HieSource = ?
                        ORDER BY Id DESC
                    """
                    cursor.execute(query, (template_name, hie_source))
                else:
                    query = """
                        SELECT Id, HieSource, SourceType, LiquidTemplate, AzureStoragePath
                        FROM dbo.TemplateConfig
                        WHERE LiquidTemplate = ?
                        ORDER BY Id DESC
                    """
                    cursor.execute(query, (template_name,))
                
                rows = cursor.fetchall()
                
                templates = []
                for row in rows:
                    templates.append({
                        "id": row[0],
                        "hie_source": row[1],
                        "source_type": row[2],
                        "template_name": row[3],
                        "azure_storage_path": row[4]
                    })
                
                return templates
                
        except Exception as e:
            logger.error(f"Error fetching templates by name: {e}")
            raise DatabaseException(f"Failed to fetch templates: {str(e)}")
    
    @staticmethod
    def get_templates_with_filters(hie_source: Optional[str] = None,
                                   source_type: Optional[str] = None,
                                   template_name: Optional[str] = None) -> List[Dict]:
        """
        Retrieve templates with optional filters
        
        Args:
            hie_source: Filter by HIE source
            source_type: Filter by source type
            template_name: Filter by template name
            
        Returns:
            List of dictionaries with template data
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic query
                conditions = []
                params = []
                
                if hie_source:
                    conditions.append("HieSource = ?")
                    params.append(hie_source)
                
                if source_type:
                    conditions.append("SourceType = ?")
                    params.append(source_type)
                
                if template_name:
                    if not template_name.endswith('.liquid'):
                        template_name = f"{template_name}.liquid"
                    conditions.append("LiquidTemplate = ?")
                    params.append(template_name)
                
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                
                query = f"""
                    SELECT Id, HieSource, SourceType, LiquidTemplate, AzureStoragePath
                    FROM dbo.TemplateConfig
                    WHERE {where_clause}
                    ORDER BY Id DESC
                """
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                templates = []
                for row in rows:
                    templates.append({
                        "id": row[0],
                        "hie_source": row[1],
                        "source_type": row[2],
                        "template_name": row[3],
                        "azure_storage_path": row[4]
                    })
                
                logger.info(f"Retrieved {len(templates)} template records with filters")
                return templates
                
        except Exception as e:
            logger.error(f"Error fetching templates with filters: {e}")
            raise DatabaseException(f"Failed to fetch templates: {str(e)}")
    
    @staticmethod
    def update_template_by_id(template_id: int, 
                             hie_source: Optional[str] = None,
                             source_type: Optional[str] = None) -> bool:
        """
        Update an existing template record by ID
        
        Args:
            template_id: ID of the template to update
            hie_source: Optional new HIE source
            source_type: Optional new source type
            
        Returns:
            True if successful
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                update_fields = []
                params = []
                
                if hie_source:
                    update_fields.append("HieSource = ?")
                    params.append(hie_source)
                
                if source_type:
                    update_fields.append("SourceType = ?")
                    params.append(source_type)
                
                if not update_fields:
                    logger.warning("No fields to update")
                    return True
                
                params.append(template_id)
                
                query = f"""
                    UPDATE dbo.TemplateConfig
                    SET {', '.join(update_fields)}
                    WHERE Id = ?
                """
                
                cursor.execute(query, params)
                conn.commit()
                
                if cursor.rowcount == 0:
                    logger.warning(f"No template found with ID: {template_id}")
                    raise DatabaseException(f"Template with ID {template_id} not found")
                
                logger.info(f"Updated template ID: {template_id}")
                return True
                
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Error updating template: {e}")
            raise DatabaseException(f"Failed to update template: {str(e)}")
    
    @staticmethod
    def delete_template_by_id(template_id: int) -> bool:
        """
        Delete a template record by ID
        
        Args:
            template_id: ID of the template to delete
            
        Returns:
            True if successful
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    DELETE FROM dbo.TemplateConfig
                    WHERE Id = ?
                """
                
                cursor.execute(query, (template_id,))
                conn.commit()
                
                if cursor.rowcount == 0:
                    logger.warning(f"No template found with ID: {template_id}")
                    raise DatabaseException(f"Template with ID {template_id} not found")
                
                logger.info(f"Deleted template ID: {template_id}")
                return True
                
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            raise DatabaseException(f"Failed to delete template: {str(e)}")
        
    @staticmethod
    def check_duplicate_template(liquid_template: str, hie_source: str, source_type: str) -> bool:
        """
        Check if a template with the same name, hie_source, and source_type already exists
        
        Returns:
            True if duplicate exists, False otherwise
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT COUNT(*) 
                    FROM dbo.TemplateConfig
                    WHERE LiquidTemplate = ? AND HieSource = ? AND SourceType = ?
                """
                
                cursor.execute(query, (liquid_template, hie_source, source_type))
                count = cursor.fetchone()[0]
                
                return count > 0
                
        except Exception as e:
            logger.error(f"Error checking duplicate template: {e}")
            raise DatabaseException(f"Failed to check duplicate: {str(e)}")
        
    @staticmethod
    def delete_templates_by_name(template_name: str, hie_source: Optional[str] = None, 
                                source_type: Optional[str] = None) -> List[Dict]:
        """
        Delete all templates with the same name (cascade delete)
        
        Args:
            template_name: Name of the template
            hie_source: Optional filter by HIE source
            source_type: Optional filter by source type
            
        Returns:
            List of deleted template records
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # First, get all matching templates
                conditions = ["LiquidTemplate = ?"]
                params = [template_name]
                
                if hie_source:
                    conditions.append("HieSource = ?")
                    params.append(hie_source)
                
                if source_type:
                    conditions.append("SourceType = ?")
                    params.append(source_type)
                
                where_clause = " AND ".join(conditions)
                
                # Get templates before deletion
                select_query = f"""
                    SELECT Id, HieSource, SourceType, LiquidTemplate, AzureStoragePath
                    FROM dbo.TemplateConfig
                    WHERE {where_clause}
                """
                
                cursor.execute(select_query, params)
                rows = cursor.fetchall()
                
                deleted_templates = []
                for row in rows:
                    deleted_templates.append({
                        "id": row[0],
                        "hie_source": row[1],
                        "source_type": row[2],
                        "template_name": row[3],
                        "azure_storage_path": row[4]
                    })
                
                if not deleted_templates:
                    raise DatabaseException(f"No templates found with name: {template_name}")
                
                # Delete all matching templates
                delete_query = f"""
                    DELETE FROM dbo.TemplateConfig
                    WHERE {where_clause}
                """
                
                cursor.execute(delete_query, params)
                conn.commit()
                
                logger.info(f"Cascade deleted {len(deleted_templates)} templates with name: {template_name}")
                return deleted_templates
                
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Error cascade deleting templates: {e}")
            raise DatabaseException(f"Failed to cascade delete templates: {str(e)}")