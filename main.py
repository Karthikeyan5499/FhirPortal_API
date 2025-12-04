from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Import routers
from api.template_management.controller import router as template_router
from api.hie_config_management.controller import router as hie_router
from api.ruleset_management.controller import router as ruleset_router
from api.workflow_management.controller import router as workflow_router
from api.fga_access_control.controller import router as fga_router
from auth.auth_handler import router as auth_router

# Import database and storage test functions
from database import test_connection as test_db_connection
from api.template_management.blob_service import AzureBlobStorageService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fhir_portal_api.log')
    ]
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
    description="Complete Backend API for FHIR Portal Application with Azure Integration",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(template_router, prefix="/api/template-management", tags=["Template Management"])
app.include_router(hie_router, prefix="/api/hie-config", tags=["HIE Config Management"])
app.include_router(ruleset_router, prefix="/api/ruleset", tags=["Ruleset Management"])
app.include_router(workflow_router, prefix="/api/workflow", tags=["Workflow Management"])
app.include_router(fga_router, prefix="/api/fga", tags=["Fine-Grain Access Control"])

@app.get("/", tags=["Root"])
async def root():
    """API Root - Welcome message"""
    return {
        "message": "FHIR Portal API v3.0 - Azure Edition",
        "status": "running",
        "documentation": "/docs",
        "redoc": "/redoc",
        "health": "/api/health"
    }

@app.get("/api/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    Returns API status and connection health
    """
    # Test database
    db_healthy = False
    try:
        db_healthy = test_db_connection()
    except:
        pass
    
    # Test blob storage
    storage_healthy = False
    try:
        blob_service = AzureBlobStorageService()
        storage_healthy = blob_service.test_connection()
    except:
        pass
    
    overall_status = "healthy" if (db_healthy and storage_healthy) else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": "2024-12-04T00:00:00Z",
        "services": {
            "api": "healthy",
            "database": "healthy" if db_healthy else "unhealthy",
            "blob_storage": "healthy" if storage_healthy else "unhealthy"
        },
        "version": "3.0.0"
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

if __name__ == "__main__":
    import uvicorn
    from config import settings
    
    logger.info(f"Starting server on {settings.API_HOST}:{settings.API_PORT}")
    
    uvicorn.run(
        app, 
        host=settings.API_HOST, 
        port=settings.API_PORT,
        log_level="info"
    )