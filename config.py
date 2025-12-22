from pydantic_settings import BaseSettings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Azure SQL Database
    AZURE_SQL_SERVER: str
    AZURE_SQL_DATABASE: str
    AZURE_SQL_USERNAME: str
    AZURE_SQL_PASSWORD: str
    AZURE_SQL_DRIVER: str = "ODBC Driver 18 for SQL Server"
    
    # Azure Blob Storage
    AZURE_STORAGE_ACCOUNT_NAME: str
    AZURE_STORAGE_ACCOUNT_KEY: str
    AZURE_STORAGE_CONTAINER_LIQUID: str
    AZURE_STORAGE_CONTAINER_INPUT: str  # NEW
    AZURE_STORAGE_CONNECTION_STRING: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def BLOB_CONNECTION_STRING(self) -> str:
        """Get blob connection string"""
        if self.AZURE_STORAGE_CONNECTION_STRING:
            logger.info("✅ Using AZURE_STORAGE_CONNECTION_STRING from .env")
            return self.AZURE_STORAGE_CONNECTION_STRING
        
        if self.AZURE_STORAGE_ACCOUNT_NAME and self.AZURE_STORAGE_ACCOUNT_KEY:
            logger.info("⚠️ Building connection string from account name + key")
            return (
                f"DefaultEndpointsProtocol=https;"
                f"AccountName={self.AZURE_STORAGE_ACCOUNT_NAME};"
                f"AccountKey={self.AZURE_STORAGE_ACCOUNT_KEY};"
                f"EndpointSuffix=core.windows.net"
            )
        
        raise ValueError("❌ No blob storage credentials found in .env")

    def get_liquid_container(self) -> str:
        """Get liquid templates container name"""
        return self.AZURE_STORAGE_CONTAINER_LIQUID

    def get_input_container(self) -> str:
        """Get input files container name"""
        return self.AZURE_STORAGE_CONTAINER_INPUT
        
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()