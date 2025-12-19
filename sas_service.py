# sas_service.py - UPDATED VERSION
import os
from datetime import datetime, timedelta, timezone
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
import logging

logger = logging.getLogger(__name__)

def get_storage_credentials():
    """
    Extract storage account name and key from environment
    Supports both connection string and individual credentials
    """
    # Try connection string first
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    if connection_string:
        # Parse connection string
        parts = {}
        for part in connection_string.split(';'):
            if '=' in part:
                key, value = part.split('=', 1)
                parts[key.strip()] = value.strip()
        
        account_name = parts.get('AccountName')
        account_key = parts.get('AccountKey')
        
        if account_name and account_key:
            logger.info("✅ Using credentials from AZURE_STORAGE_CONNECTION_STRING")
            return account_name, account_key
    
    # Fallback to individual env vars
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
    
    if account_name and account_key:
        logger.info("✅ Using credentials from AZURE_STORAGE_ACCOUNT_NAME and KEY")
        return account_name, account_key
    
    raise ValueError(
        "Azure Storage credentials not found. "
        "Set either AZURE_STORAGE_CONNECTION_STRING or "
        "(AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY)"
    )

def get_container_name(container_type: str = "liquid") -> str:
    """
    Get container name based on type
    
    Args:
        container_type: 'liquid' or 'input'
    
    Returns:
        Container name
    """
    if container_type == "liquid":
        container = os.getenv("AZURE_STORAGE_CONTAINER_LIQUID")
        if not container:
            raise ValueError("AZURE_STORAGE_CONTAINER_LIQUID not set in .env")
        return container
    
    elif container_type == "input":
        container = os.getenv("AZURE_STORAGE_CONTAINER_INPUT")
        if not container:
            raise ValueError("AZURE_STORAGE_CONTAINER_INPUT not set in .env")
        return container
    
    else:
        raise ValueError(f"Invalid container_type: {container_type}. Must be 'liquid' or 'input'")

def validate_azure_config(container_type: str = "liquid"):
    """
    Validate that all required Azure Storage environment variables are set
    
    Args:
        container_type: 'liquid' or 'input'
    
    Raises:
        ValueError: If required config is missing
    """
    try:
        account_name, account_key = get_storage_credentials()
        container_name = get_container_name(container_type)
        
        logger.info(f"✅ Config validated for container type: {container_type}")
        return account_name, account_key, container_name
    
    except ValueError as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        raise

def generate_upload_sas(blob_name: str, container_type: str = "liquid", expiry_minutes: int = 15) -> str:
    """
    Generates a write-only SAS URL for a single blob
    
    Args:
        blob_name: Name of the blob to upload
        container_type: 'liquid' for templates, 'input' for input files (default: 'liquid')
        expiry_minutes: Minutes until the SAS token expires (default: 15)
    
    Returns:
        str: Complete upload URL with SAS token
    
    Raises:
        ValueError: If Azure Storage configuration is missing
        Exception: If SAS token generation fails
    
    Example:
        >>> generate_upload_sas("patient.liquid", "liquid", 15)
        'https://account.blob.core.windows.net/liquid-templates/patient.liquid?sv=...'
        
        >>> generate_upload_sas("sample.hl7", "input", 15)
        'https://account.blob.core.windows.net/input-files/sample.hl7?sv=...'
    """
    try:
        # Validate configuration and get credentials
        account_name, account_key, container_name = validate_azure_config(container_type)
        
        # Generate SAS token with create and write permissions
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(create=True, write=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        )

        # Construct the full upload URL
        upload_url = (
            f"https://{account_name}.blob.core.windows.net/"
            f"{container_name}/{blob_name}?{sas_token}"
        )
        
        logger.info(
            f"Generated upload SAS URL for blob: {blob_name} "
            f"in container: {container_name} (expires in {expiry_minutes} minutes)"
        )
        return upload_url
    
    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
        raise
    except Exception as e:
        logger.error(f"Failed to generate SAS token for {blob_name}: {e}")
        raise Exception(f"SAS token generation failed: {str(e)}")


def generate_read_sas(blob_name: str, container_type: str = "liquid", expiry_minutes: int = 60) -> str:
    """
    Generates a read-only SAS URL for a single blob
    
    Args:
        blob_name: Name of the blob to read
        container_type: 'liquid' for templates, 'input' for input files (default: 'liquid')
        expiry_minutes: Minutes until the SAS token expires (default: 60)
    
    Returns:
        str: Complete read URL with SAS token
    
    Example:
        >>> generate_read_sas("patient.liquid", "liquid", 60)
        'https://account.blob.core.windows.net/liquid-templates/patient.liquid?sv=...'
    """
    try:
        # Validate configuration and get credentials
        account_name, account_key, container_name = validate_azure_config(container_type)
        
        # Generate SAS token with read permission
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        )

        # Construct the full read URL
        read_url = (
            f"https://{account_name}.blob.core.windows.net/"
            f"{container_name}/{blob_name}?{sas_token}"
        )
        
        logger.info(
            f"Generated read SAS URL for blob: {blob_name} "
            f"in container: {container_name} (expires in {expiry_minutes} minutes)"
        )
        return read_url
    
    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
        raise
    except Exception as e:
        logger.error(f"Failed to generate read SAS token for {blob_name}: {e}")
        raise Exception(f"Read SAS token generation failed: {str(e)}")