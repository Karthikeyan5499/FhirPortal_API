from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

class BaseAPIException(HTTPException):
    """Base exception class for API errors"""
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)
        logger.error(f"{self.__class__.__name__}: {detail}")

class DatabaseException(BaseAPIException):
    """Database operation exceptions"""
    def __init__(self, detail: str):
        super().__init__(detail=f"Database error: {detail}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class NotFoundException(BaseAPIException):
    """Resource not found exceptions"""
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class BadRequestException(BaseAPIException):
    """Bad request exceptions"""
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)

class UnauthorizedException(BaseAPIException):
    """Unauthorized access exceptions"""
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)

class ForbiddenException(BaseAPIException):
    """Forbidden access exceptions"""
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)

class ConflictException(BaseAPIException):
    """Conflict exceptions (duplicate resources)"""
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)

class ValidationException(BaseAPIException):
    """Data validation exceptions"""
    def __init__(self, detail: str):
        super().__init__(detail=f"Validation error: {detail}", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

class StorageException(BaseAPIException):
    """Azure Blob Storage exceptions"""
    def __init__(self, detail: str):
        super().__init__(detail=f"Storage error: {detail}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ConnectionException(BaseAPIException):
    """Connection exceptions"""
    def __init__(self, detail: str):
        super().__init__(detail=f"Connection error: {detail}", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

class TimeoutException(BaseAPIException):
    """Operation timeout exceptions"""
    def __init__(self, detail: str):
        super().__init__(detail=f"Operation timeout: {detail}", status_code=status.HTTP_504_GATEWAY_TIMEOUT)