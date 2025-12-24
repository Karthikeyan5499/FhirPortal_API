# main.py - Container-Level SAS Token Support
from fastapi import FastAPI, status, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from pydantic import BaseModel
from typing import Literal
from sas_service import generate_upload_sas, test_sas_generation

# Import routers
from api.template_management.controller import router as template_router
from api.workflow_management.controller import router as workflow_router
from auth.auth_handler import router as auth_router

# Import database and storage test functions
from database import test_connection as test_db_connection
from api.template_management.blob_service import AzureBlobStorageService

import uvicorn
from config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding='utf-8', 
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 FHIR Portal API Starting...")
    logger.info("=" * 80)
    
    # Test Azure SQL Database connection
    logger.info("📊 Testing Azure SQL Database connection...")
    db_status = test_db_connection()
    if not db_status:
        logger.error("❌ Azure SQL Database connection failed!")
        logger.warning("⚠️  API will start but database operations may fail")
    
    # Test Azure Blob Storage connection
    logger.info("☁️  Testing Azure Blob Storage connection...")
    try:
        blob_service = AzureBlobStorageService()
        storage_status = blob_service.test_connection()
        if not storage_status:
            logger.error("❌ Azure Blob Storage connection failed!")
            logger.warning("⚠️  API will start but file operations may fail")
    except Exception as e:
        logger.error(f"❌ Azure Blob Storage initialization failed: {e}")
        logger.warning("⚠️  API will start but file operations may fail")
    
    # Test SAS Token Generation
    logger.info("🔑 Testing SAS Token Generation...")
    try:
        sas_test_result = test_sas_generation()
        
        # Check input container
        if sas_test_result.get("input", {}).get("status") == "success":
            input_result = sas_test_result["input"]
            logger.info(f"✅ Input Container SAS: OK")
            logger.info(f"   Account: {input_result['account_name']}")
            logger.info(f"   Container: {input_result['container']}")
            logger.info(f"   SAS Token: {input_result['container_sas']}")
        else:
            logger.error(f"❌ Input Container SAS failed: {sas_test_result.get('input', {}).get('error')}")
            
    except Exception as e:
        logger.error(f"❌ SAS Token Generation test failed: {e}")
        logger.warning("⚠️  API will start but SAS token operations may fail")
    
    logger.info("=" * 80)
    logger.info("✅ FHIR Portal API Started Successfully")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("=" * 80)
    logger.info("🛑 FHIR Portal API Shutting down...")
    logger.info("=" * 80)

app = FastAPI(
    title="FHIR Portal API",
    description="Backend API for FHIR Portal with Container-Level SAS Token Support",
    version="3.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(template_router, prefix="/api/template-management", tags=["Template Management"])
app.include_router(workflow_router, prefix="/api/workflow-management", tags=["Workflow Management"]) 

@app.get("/", tags=["Root"])
async def root():
    """API Root - Welcome message"""
    return {
        "message": "FHIR Portal API v3.2 - Container-Level SAS Token Support",
        "status": "running",
        "documentation": "/docs",
        "redoc": "/redoc",
        "health": "/api/health"
    }

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    db_healthy = False
    try:
        db_healthy = test_db_connection()
    except:
        pass
    
    storage_healthy = False
    try:
        blob_service = AzureBlobStorageService()
        storage_healthy = blob_service.test_connection()
    except:
        pass
    
    overall_status = "healthy" if (db_healthy and storage_healthy) else "degraded"
    
    return {
        "status": overall_status,
        "services": {
            "api": "healthy",
            "database": "healthy" if db_healthy else "unhealthy",
            "blob_storage": "healthy" if storage_healthy else "unhealthy"
        },
        "version": "3.2.0"
    }

@app.get("/api/health/database", tags=["Health"])
async def database_health():
    """Test database connection"""
    try:
        is_healthy = test_db_connection()
        if is_healthy:
            return {"status": "healthy", "message": "Azure SQL Database connection successful"}
        else:
            return {"status": "unhealthy", "message": "Azure SQL Database connection failed"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Error: {str(e)}"}

@app.get("/api/health/storage", tags=["Health"])
async def storage_health():
    """Test blob storage connection"""
    try:
        blob_service = AzureBlobStorageService()
        is_healthy = blob_service.test_connection()
        if is_healthy:
            return {"status": "healthy", "message": "Azure Blob Storage connection successful"}
        else:
            return {"status": "unhealthy", "message": "Azure Blob Storage connection failed"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Error: {str(e)}"}

# ========== SAS TOKEN ENDPOINTS ==========

class SasRequest(BaseModel):
    """Request model for generating input container SAS token"""
    container_type: Literal["input"] = "input"


@app.get("/api/health/sas", tags=["Health"], summary="Test Input Container SAS")
async def sas_health():
    """
    Test SAS token generation for INPUT container only
    """
    try:
        results = test_sas_generation()
        
        # Only check input container
        input_result = results.get("input", {})
        is_healthy = input_result.get("status") == "success"
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "message": "Input container SAS token generation test",
            "container": input_result
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Error: {str(e)}"
        }

@app.post("/api/get-upload-sas", tags=["Storage"], summary="Generate Input Container SAS Token")
def get_upload_sas(request: SasRequest):
    """
    Generate a SAS URL for uploading INPUT files to Azure Blob Storage
    
    **Only for INPUT container** - Returns SAS token for input-files container
    
    Allows:
    - Upload input files (HL7, CDA, CCDA, X12, etc.)
    - List files in input container
    - Read files from input container
    
    Args:
        request: SasRequest containing:
            - container_type: Must be "input" (default)
    
    Returns:
        dict: Contains input container URL with SAS token
    
    Example Request:
```json
        {
            "container_type": "input"
        }
```
        
    Frontend Usage:
```javascript
        // 1. Get input container SAS
        const response = await fetch('/api/get-upload-sas', {
            method: 'POST',
            body: JSON.stringify({ container_type: 'input' })
        });
        const { containerUrl } = await response.json();
        
        // 2. Upload input file
        const fileName = 'HL7/KONZA-ABHKS-ADT1.ccda';
        const uploadUrl = `${containerUrl.split('?')[0]}/${fileName}?${containerUrl.split('?')[1]}`;
        await fetch(uploadUrl, {
            method: 'PUT',
            headers: { 'x-ms-blob-type': 'BlockBlob' },
            body: fileContent
        });
```
    """
    try:
        # Force input container only
        container_url = generate_upload_sas(
            container_type="input"  # Hardcoded to input
        )
        
        return {
            "containerUrl": container_url,
            "containerType": "input",
            "expiresIn": "15 minutes",
            "permissions": "read, write, list",
            "note": "This SAS token is only for INPUT files container"
        }
    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Failed to generate input container SAS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate input container URL: {str(e)}"
        )


if __name__ == "__main__": 
    logger.info(f"Starting server on {settings.API_HOST}:{settings.API_PORT}")
    
    uvicorn.run(
        app, 
        host=settings.API_HOST, 
        port=settings.API_PORT,
        log_level="info"
    )