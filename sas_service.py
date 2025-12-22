# sas_service.py - Container-Level SAS Token Generation
import os
from datetime import datetime, timedelta, timezone
from azure.storage.blob import (
    generate_container_sas, 
    ContainerSasPermissions
)
import logging
from dotenv import load_dotenv 
from typing import Literal

load_dotenv()

logger = logging.getLogger(__name__)

def get_storage_credentials():
    """Extract storage account name and key from environment"""
    load_dotenv(override=True)
    
    # Try connection string first
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    if connection_string:
        logger.info(f"Found AZURE_STORAGE_CONNECTION_STRING: {connection_string[:50]}...")
        parts = {}
        for part in connection_string.split(';'):
            if '=' in part:
                key, value = part.split('=', 1)
                parts[key.strip()] = value.strip()
        
        account_name = parts.get('AccountName')
        account_key = parts.get('AccountKey')
        
        if account_name and account_key:
            logger.info(f"✅ Using credentials from AZURE_STORAGE_CONNECTION_STRING")
            logger.info(f"   Account Name: {account_name}")
            return account_name, account_key
        else:
            logger.warning(f"Connection string found but missing AccountName or AccountKey")
    else:
        logger.warning("AZURE_STORAGE_CONNECTION_STRING not found in environment")
    
    # Fallback to individual env vars
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
    
    if account_name and account_key:
        logger.info(f"✅ Using credentials from AZURE_STORAGE_ACCOUNT_NAME and KEY")
        logger.info(f"   Account Name: {account_name}")
        return account_name, account_key
    else:
        logger.error("AZURE_STORAGE_ACCOUNT_NAME or AZURE_STORAGE_ACCOUNT_KEY not found")
    
    # Debug: Print all environment variables that start with AZURE
    logger.error("Available AZURE environment variables:")
    for key in os.environ.keys():
        if key.startswith('AZURE'):
            value = os.environ[key]
            masked_value = value[:20] + "..." if len(value) > 20 else value
            logger.error(f"   {key} = {masked_value}")
    
    raise ValueError(
        "Azure Storage credentials not found. "
        "Set either AZURE_STORAGE_CONNECTION_STRING or "
        "(AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY)"
    )


def validate_azure_config(container_type: Literal[ "input"] = "input"):
    """
    Validate Azure Storage configuration for specific container type
    
    Args:
        container_type: Type of container ("input")
    """
    try:
        account_name, account_key = get_storage_credentials()
        
        if container_type == "input":
            container_name = os.getenv("AZURE_STORAGE_CONTAINER_INPUT")
            if not container_name:
                raise ValueError("AZURE_STORAGE_CONTAINER_INPUT not set in .env")
        else:
            raise ValueError(f"Invalid container type: {container_type}")
        
        logger.info(f"✅ Config validated for {container_type} container: {container_name}")
        return account_name, account_key, container_name
    except ValueError as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        raise


def generate_upload_sas(
    container_type: Literal["input"] = "input",
    expiry_minutes: int = 15
) -> str:
    """
    Generate a SAS URL for entire container (no specific blob path)
    
    Args:
        container_type: Container type ("liquid" or "input")
        expiry_minutes: Minutes until SAS token expires (default: 15)
    
    Returns:
        str: Container URL with SAS token
        
    Example:
        >>> generate_upload_sas("liquid")
        'https://account.blob.core.windows.net/liquid-templates?sv=2023-01-03&ss=b...'
    """
    try:
        account_name, account_key, container_name = validate_azure_config(container_type)
        
        # Generate CONTAINER SAS token (covers entire container)
        sas_token = generate_container_sas(
            account_name=account_name,
            container_name=container_name,
            account_key=account_key,
            permission=ContainerSasPermissions(
                read=True,
                write=True,
                delete=False,
                list=True
            ),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        )

        # Construct container-level URL
        container_url = (
            f"https://{account_name}.blob.core.windows.net/"
            f"{container_name}?{sas_token}"
        )
        
        logger.info(
            f"Generated container SAS URL for {container_type} container: {container_name} "
            f"(expires in {expiry_minutes} minutes, permissions: read, write, list)"
        )
        return container_url
    
    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
        raise
    except Exception as e:
        logger.error(f"Failed to generate container SAS token: {e}")
        raise Exception(f"Container SAS token generation failed: {str(e)}")


def test_sas_generation():
    """
    Test SAS token generation for both containers
    Returns: dict with test results for each container
    """
    results = {}
    
    # Test input container
    try:
        account_name, account_key, input_container = validate_azure_config("input")
        container_url = generate_upload_sas("input", expiry_minutes=5)
        
        results["input"] = {
            "status": "success",
            "account_name": account_name,
            "container": input_container,
            "container_sas": "generated" if container_url else "failed"
        }
        logger.info("✅ Input container SAS test successful")
    except Exception as e:
        results["input"] = {"status": "failed", "error": str(e)}
        logger.error(f"❌ Input container SAS test failed: {e}")
    
    return results