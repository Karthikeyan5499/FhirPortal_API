from database import get_db_connection
from common.exceptions import (
    DatabaseException, 
    NotFoundException, 
    BadRequestException,
    ConflictException,
    ValidationException
)
from typing import List, Optional, Dict, Any
import logging
import pyodbc

logger = logging.getLogger(__name__)

class TemplateRepository:
    
    @staticmethod
    def get_all(
        template_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
        search_query: Optional[str] = None
    ):
        """Get all templates with pagination and filtering - Full exception handling"""
        try:
            # Validate pagination parameters
            if page < 1:
                raise ValidationException("Page number must be >= 1")
            if page_size < 1 or page_size > 100:
                raise ValidationException("Page size must be between 1 and 100")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Build query
                query = """
                    SELECT t.id, t.name, t.description, t.template_type, t.version,
                           t.file_url, t.is_active, t.created_at, t.updated_at
                    FROM Templates t
                    WHERE 1=1
                """
                params = []
                
                if template_type:
                    query += " AND t.template_type = ?"
                    params.append(template_type)
                
                if is_active is not None:
                    query += " AND t.is_active = ?"
                    params.append(is_active)
                
                if search_query:
                    query += " AND (t.name LIKE ? OR t.description LIKE ?)"
                    search_term = f"%{search_query}%"
                    params.extend([search_term, search_term])
                
                # Count total
                try:
                    count_query = f"SELECT COUNT(*) FROM ({query}) AS CountQuery"
                    cursor.execute(count_query, params)
                    total = cursor.fetchone()[0]
                except pyodbc.Error as e:
                    logger.error(f"Error counting templates: {e}")
                    raise DatabaseException("Failed to count templates")
                
                # Add pagination
                query += " ORDER BY t.created_at DESC"
                query += f" OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
                params.extend([(page - 1) * page_size, page_size])
                
                try:
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                except pyodbc.Error as e:
                    logger.error(f"Error fetching templates: {e}")
                    raise DatabaseException("Failed to fetch templates")
                
                templates = []
                for row in rows:
                    try:
                        template = dict(zip([column[0] for column in cursor.description], row))
                        
                        # Safely get tags
                        template['tags'] = TemplateRepository._get_template_tags_safe(template['id'], conn)
                        
                        # Add default values
                        template.setdefault('file_name', None)
                        template.setdefault('file_size', None)
                        template.setdefault('mime_type', None)
                        template.setdefault('created_by', None)
                        template.setdefault('last_used_at', None)
                        template.setdefault('usage_count', 0)
                        
                        templates.append(template)
                    except Exception as e:
                        logger.warning(f"Error processing template row: {e}")
                        continue
                
                logger.info(f"✅ Fetched {len(templates)} templates (page {page}/{(total + page_size - 1) // page_size})")
                
                return {
                    "total": total,
                    "templates": templates,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }
                
        except ValidationException:
            raise
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_all: {e}", exc_info=True)
            raise DatabaseException(f"Failed to fetch templates: {str(e)}")
    
    @staticmethod
    def _get_template_tags_safe(template_id: int, conn) -> List[str]:
        """Get tags for a template - safe version with full error handling"""
        try:
            # Check if TemplateTags table exists
            check_cursor = conn.cursor()
            check_cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'TemplateTags'
            """)
            table_exists = check_cursor.fetchone()[0] > 0
            check_cursor.close()
            
            if not table_exists:
                return []
            
            # Get tags
            tag_cursor = conn.cursor()
            tag_cursor.execute(
                "SELECT tag_name FROM TemplateTags WHERE template_id = ?", 
                (template_id,)
            )
            tags = [row[0] for row in tag_cursor.fetchall()]
            tag_cursor.close()
            
            return tags
            
        except pyodbc.Error as e:
            logger.warning(f"Database error fetching tags for template {template_id}: {e}")
            return []
        except Exception as e:
            logger.warning(f"Unexpected error fetching tags for template {template_id}: {e}")
            return []
    
    @staticmethod
    def get_by_id(template_id: int):
        """Get template by ID - Full exception handling"""
        try:
            if template_id < 1:
                raise ValidationException("Template ID must be positive")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check what columns exist
                try:
                    cursor.execute("""
                        SELECT COLUMN_NAME 
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_NAME = 'Templates'
                    """)
                    available_columns = [row[0] for row in cursor.fetchall()]
                except pyodbc.Error as e:
                    logger.error(f"Error checking table schema: {e}")
                    raise DatabaseException("Failed to verify table structure")
                
                # Build query with available columns
                base_columns = ['id', 'name', 'description', 'template_type', 'version', 'is_active', 'created_at', 'updated_at']
                optional_columns = ['file_url', 'file_name', 'file_size', 'mime_type', 'created_by', 'last_used_at', 'usage_count']
                
                columns_to_select = base_columns + [col for col in optional_columns if col in available_columns]
                
                query = f"""
                    SELECT {', '.join(columns_to_select)}
                    FROM Templates
                    WHERE id = ?
                """
                
                try:
                    cursor.execute(query, (template_id,))
                    row = cursor.fetchone()
                except pyodbc.Error as e:
                    logger.error(f"Error fetching template {template_id}: {e}")
                    raise DatabaseException(f"Failed to fetch template")
                
                if not row:
                    raise NotFoundException(f"Template with ID {template_id} not found")
                
                template = dict(zip(columns_to_select, row))
                
                # Add default values for missing columns
                for col in optional_columns:
                    if col not in template:
                        template[col] = None if col != 'usage_count' else 0
                
                # Get tags
                template['tags'] = TemplateRepository._get_template_tags_safe(template_id, conn)
                
                logger.info(f"✅ Fetched template {template_id}")
                return template
                
        except NotFoundException:
            raise
        except ValidationException:
            raise
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_by_id: {e}", exc_info=True)
            raise DatabaseException(f"Failed to fetch template: {str(e)}")
    
    @staticmethod
    def create(template_data: dict, user_id: int):
        """Create new template - Full exception handling"""
        try:
            # Validate input
            if not template_data.get('name'):
                raise ValidationException("Template name is required")
            if not template_data.get('template_type'):
                raise ValidationException("Template type is required")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check for duplicate
                try:
                    cursor.execute("""
                        SELECT id FROM Templates 
                        WHERE name = ? AND version = ?
                    """, (template_data['name'], template_data.get('version', '1.0')))
                    
                    if cursor.fetchone():
                        raise ConflictException(
                            f"Template '{template_data['name']}' version '{template_data.get('version', '1.0')}' already exists"
                        )
                except pyodbc.Error as e:
                    if "duplicate" in str(e).lower():
                        raise ConflictException("Template with this name and version already exists")
                    logger.error(f"Error checking for duplicate: {e}")
                    raise DatabaseException("Failed to check for duplicate templates")
                
                # Check available columns
                try:
                    cursor.execute("""
                        SELECT COLUMN_NAME 
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_NAME = 'Templates'
                    """)
                    available_columns = [row[0] for row in cursor.fetchall()]
                except pyodbc.Error as e:
                    logger.error(f"Error checking table schema: {e}")
                    raise DatabaseException("Failed to verify table structure")
                
                # Build INSERT
                insert_columns = ['name', 'description', 'template_type', 'version', 'is_active']
                insert_values = [
                    template_data['name'],
                    template_data.get('description'),
                    template_data['template_type'],
                    template_data.get('version', '1.0'),
                    template_data.get('is_active', True)
                ]
                
                if 'created_by' in available_columns:
                    insert_columns.append('created_by')
                    insert_values.append(user_id)
                
                placeholders = ', '.join(['?' for _ in insert_values])
                
                #Build OUTPUT clause
                output_columns = ['id', 'name', 'description', 'template_type', 'version', 'is_active', 'created_at', 'updated_at']
                if 'file_url' in available_columns:
                    output_columns.append('file_url')
                if 'created_by' in available_columns:
                    output_columns.append('created_by')

                query = f"""
                    INSERT INTO Templates ({', '.join(insert_columns)})
                    OUTPUT {', '.join(['INSERTED.' + col for col in output_columns])}
                    VALUES ({placeholders})
                """
                
                try:
                    cursor.execute(query, insert_values)
                    row = cursor.fetchone()
                except pyodbc.Error as e:
                    logger.error(f"Error inserting template: {e}")
                    raise DatabaseException(f"Failed to create template: {str(e)}")
                
                template = dict(zip(output_columns, row))
                template_id = template['id']
                
                # Add default values
                template.setdefault('file_url', None)
                template.setdefault('file_name', None)
                template.setdefault('file_size', None)
                template.setdefault('mime_type', None)
                template.setdefault('created_by', user_id)
                template.setdefault('last_used_at', None)
                template.setdefault('usage_count', 0)
                
                # Add tags
                tags = []
                if 'tags' in template_data and template_data['tags']:
                    try:
                        cursor.execute("""
                            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                            WHERE TABLE_NAME = 'TemplateTags'
                        """)
                        if cursor.fetchone()[0] > 0:
                            for tag in template_data['tags']:
                                try:
                                    cursor.execute("""
                                        INSERT INTO TemplateTags (template_id, tag_name)
                                        VALUES (?, ?)
                                    """, (template_id, tag.strip()))
                                    tags.append(tag.strip())
                                except pyodbc.Error as e:
                                    logger.warning(f"Error adding tag '{tag}': {e}")
                    except Exception as e:
                        logger.warning(f"Error adding tags: {e}")
                
                try:
                    conn.commit()
                except pyodbc.Error as e:
                    logger.error(f"Error committing transaction: {e}")
                    raise DatabaseException("Failed to save template")
                
                template['tags'] = tags
                logger.info(f"✅ Created template {template_id}")
                return template
                
        except ConflictException:
            raise
        except ValidationException:
            raise
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in create: {e}", exc_info=True)
            raise DatabaseException(f"Failed to create template: {str(e)}")

    @staticmethod
    def update(template_id: int, template_data: dict):
        """Update template - Full exception handling"""
        try:
            if template_id < 1:
                raise ValidationException("Template ID must be positive")
            
            if not template_data:
                raise ValidationException("No data provided for update")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check template exists
                try:
                    cursor.execute("SELECT id FROM Templates WHERE id = ?", (template_id,))
                    if not cursor.fetchone():
                        raise NotFoundException(f"Template with ID {template_id} not found")
                except pyodbc.Error as e:
                    logger.error(f"Error checking template existence: {e}")
                    raise DatabaseException("Failed to verify template")
                
                # Check available columns
                try:
                    cursor.execute("""
                        SELECT COLUMN_NAME 
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_NAME = 'Templates'
                    """)
                    available_columns = [row[0] for row in cursor.fetchall()]
                except pyodbc.Error as e:
                    logger.error(f"Error checking table schema: {e}")
                    raise DatabaseException("Failed to verify table structure")
                
                update_fields = []
                params = []
                
                column_mapping = {
                    'name': 'name',
                    'description': 'description',
                    'template_type': 'template_type',
                    'version': 'version',
                    'is_active': 'is_active',
                    'file_url': 'file_url',
                    'file_name': 'file_name',
                    'file_size': 'file_size',
                    'mime_type': 'mime_type'
                }
                
                for key, column in column_mapping.items():
                    if key in template_data and column in available_columns:
                        update_fields.append(f"{column} = ?")
                        params.append(template_data[key])
                
                if not update_fields:
                    raise ValidationException("No valid fields to update")
                
                if 'updated_at' in available_columns:
                    update_fields.append("updated_at = GETDATE()")
                
                params.append(template_id)
                
                try:
                    cursor.execute(f"""
                        UPDATE Templates 
                        SET {', '.join(update_fields)}
                        WHERE id = ?
                    """, params)
                    
                    if cursor.rowcount == 0:
                        raise NotFoundException(f"Template with ID {template_id} not found")
                    
                    conn.commit()
                except pyodbc.Error as e:
                    logger.error(f"Error updating template: {e}")
                    raise DatabaseException(f"Failed to update template: {str(e)}")
                
                logger.info(f"✅ Updated template {template_id}")
                return TemplateRepository.get_by_id(template_id)
                
        except NotFoundException:
            raise
        except ValidationException:
            raise
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in update: {e}", exc_info=True)
            raise DatabaseException(f"Failed to update template: {str(e)}")

    @staticmethod
    def delete(template_id: int):
        """Delete template - Full exception handling"""
        try:
            if template_id < 1:
                raise ValidationException("Template ID must be positive")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    cursor.execute("DELETE FROM Templates WHERE id = ?", (template_id,))
                    
                    if cursor.rowcount == 0:
                        raise NotFoundException(f"Template with ID {template_id} not found")
                    
                    conn.commit()
                except pyodbc.Error as e:
                    logger.error(f"Error deleting template: {e}")
                    raise DatabaseException(f"Failed to delete template: {str(e)}")
                
                logger.info(f"✅ Deleted template {template_id}")
                return True
                
        except NotFoundException:
            raise
        except ValidationException:
            raise
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in delete: {e}", exc_info=True)
            raise DatabaseException(f"Failed to delete template: {str(e)}")