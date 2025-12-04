"""
.NET API Client
Handles communication with external .NET Core APIs
"""

import requests
from typing import Optional, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

logger = logging.getLogger(__name__)


class DotNetAPIClient:
    """
    Client for interacting with .NET Core backend APIs
    Includes retry logic, timeout handling, and error management
    """
    
    def __init__(
        self, 
        base_url: str, 
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize .NET API Client
        
        Args:
            base_url: Base URL of the .NET API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        if api_key:
            self.session.headers.update({'X-API-Key': api_key})
    
    def _build_url(self, endpoint: str) -> str:
        """Build complete URL from endpoint"""
        return f"{self.base_url}/{endpoint.lstrip('/')}"
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and errors"""
        try:
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as e:
            logger.error(f".NET API Error: {e}")
            error_detail = response.json() if response.content else {"error": str(e)}
            raise Exception(f".NET API Error: {error_detail}")
        except requests.exceptions.JSONDecodeError:
            return {"data": response.text}
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Send GET request to .NET API
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Response data as dictionary
        """
        try:
            url = self._build_url(endpoint)
            logger.info(f"GET request to .NET API: {url}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"GET request failed: {e}")
            raise
    
    def post(self, endpoint: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Send POST request to .NET API
        
        Args:
            endpoint: API endpoint path
            data: Form data
            json_data: JSON payload
            
        Returns:
            Response data as dictionary
        """
        try:
            url = self._build_url(endpoint)
            logger.info(f"POST request to .NET API: {url}")
            response = self.session.post(
                url, 
                data=data, 
                json=json_data, 
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"POST request failed: {e}")
            raise
    
    def put(self, endpoint: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Send PUT request to .NET API
        
        Args:
            endpoint: API endpoint path
            data: Form data
            json_data: JSON payload
            
        Returns:
            Response data as dictionary
        """
        try:
            url = self._build_url(endpoint)
            logger.info(f"PUT request to .NET API: {url}")
            response = self.session.put(
                url, 
                data=data, 
                json=json_data, 
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"PUT request failed: {e}")
            raise
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """
        Send DELETE request to .NET API
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Response data as dictionary
        """
        try:
            url = self._build_url(endpoint)
            logger.info(f"DELETE request to .NET API: {url}")
            response = self.session.delete(url, timeout=self.timeout)
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"DELETE request failed: {e}")
            raise
    
    def health_check(self) -> bool:
        """
        Check if .NET API is healthy
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health", 
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Example usage and configuration
class FHIRDotNetClient(DotNetAPIClient):
    """
    Specialized client for FHIR .NET API
    """
    
    def get_patient(self, patient_id: str) -> Dict[str, Any]:
        """Get patient by ID"""
        return self.get(f"api/patients/{patient_id}")
    
    def create_patient(self, patient_data: Dict) -> Dict[str, Any]:
        """Create new patient"""
        return self.post("api/patients", json_data=patient_data)
    
    def update_patient(self, patient_id: str, patient_data: Dict) -> Dict[str, Any]:
        """Update patient"""
        return self.put(f"api/patients/{patient_id}", json_data=patient_data)
    
    def delete_patient(self, patient_id: str) -> Dict[str, Any]:
        """Delete patient"""
        return self.delete(f"api/patients/{patient_id}")
    
    def search_patients(self, query_params: Dict) -> Dict[str, Any]:
        """Search patients"""
        return self.get("api/patients", params=query_params)
    
    def get_observation(self, observation_id: str) -> Dict[str, Any]:
        """Get observation by ID"""
        return self.get(f"api/observations/{observation_id}")
    
    def create_observation(self, observation_data: Dict) -> Dict[str, Any]:
        """Create new observation"""
        return self.post("api/observations", json_data=observation_data)


# Factory function
def create_dotnet_client(base_url: str, api_key: Optional[str] = None) -> DotNetAPIClient:
    """
    Factory function to create .NET API client
    
    Args:
        base_url: Base URL of the .NET API
        api_key: Optional API key
        
    Returns:
        Configured DotNetAPIClient instance
    """
    return DotNetAPIClient(base_url, api_key)


def create_fhir_client(base_url: str, api_key: Optional[str] = None) -> FHIRDotNetClient:
    """
    Factory function to create FHIR .NET API client
    
    Args:
        base_url: Base URL of the FHIR .NET API
        api_key: Optional API key
        
    Returns:
        Configured FHIRDotNetClient instance
    """
    return FHIRDotNetClient(base_url, api_key)