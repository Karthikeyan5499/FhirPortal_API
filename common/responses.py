from typing import Optional, Any
from pydantic import BaseModel

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

def success_response(message: str, data: Any = None):
    return ApiResponse(success=True, message=message, data=data)

def error_response(message: str):
    return ApiResponse(success=False, message=message, data=None)