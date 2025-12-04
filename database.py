import pyodbc
from config import settings
from contextlib import contextmanager
from common.exceptions import DatabaseException
import logging

logger = logging.getLogger(__name__)

def get_azure_connection_string():
    """Build Azure SQL Database connection string"""
    try:
        connection_string = (
            f"Driver={{{settings.AZURE_SQL_DRIVER}}};"
            f"Server={settings.AZURE_SQL_SERVER},1433;"
            f"Database={settings.AZURE_SQL_DATABASE};"
            f"Uid={settings.AZURE_SQL_USERNAME};"
            f"Pwd={settings.AZURE_SQL_PASSWORD};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
        return connection_string
    except Exception as e:
        logger.error(f"Error building Azure connection string: {e}")
        raise DatabaseException("Failed to build database connection string")

@contextmanager
def get_db_connection():
    """Get Azure SQL Database connection with proper error handling"""
    conn = None
    try:
        connection_string = get_azure_connection_string()
        conn = pyodbc.connect(connection_string)
        logger.info("Azure SQL Database connection established")
        yield conn
    except pyodbc.Error as e:
        logger.error(f"Azure SQL Database connection error: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise DatabaseException(f"Database connection failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise DatabaseException(f"Unexpected database error: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
                logger.info("Azure SQL Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")

def test_connection():
    """Test Azure SQL Database connection"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT GETDATE() as current_time")
            result = cursor.fetchone()
            logger.info(f"✅ Azure SQL Database connection test successful. Server time: {result[0]}")
            return True
    except Exception as e:
        logger.error(f"❌ Azure SQL Database connection test failed: {e}")
        return False

def get_db_cursor():
    """Get database cursor (legacy support)"""
    try:
        connection_string = get_azure_connection_string()
        conn = pyodbc.connect(connection_string)
        return conn, conn.cursor()
    except Exception as e:
        logger.error(f"Error getting cursor: {e}")
        raise DatabaseException(f"Failed to get database cursor: {str(e)}")