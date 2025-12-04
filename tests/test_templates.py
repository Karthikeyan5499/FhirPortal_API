"""
Tests for Template Management API
"""

import pytest
from fastapi import status


class TestTemplateManagement:
    """Test suite for Template Management"""
    
    def test_get_all_templates(self, test_client, auth_headers_user):
        """Test getting all templates"""
        response = test_client.get(
            "/api/template-management/templates",
            headers=auth_headers_user
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
    
    def test_create_template(self, test_client, auth_headers_admin, sample_template_data, clean_test_data):
        """Test creating a template"""
        response = test_client.post(
            "/api/template-management/templates",
            headers=auth_headers_admin,
            json=sample_template_data
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == sample_template_data["name"]
        assert data["template_type"] == sample_template_data["template_type"]
        assert "id" in data
    
    def test_get_template_by_id(self, test_client, auth_headers_user, auth_headers_admin, sample_template_data, clean_test_data):
        """Test getting template by ID"""
        # First create a template
        create_response = test_client.post(
            "/api/template-management/templates",
            headers=auth_headers_admin,
            json=sample_template_data
        )
        template_id = create_response.json()["id"]
        
        # Then get it
        response = test_client.get(
            f"/api/template-management/templates/{template_id}",
            headers=auth_headers_user
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == template_id
    
    def test_update_template(self, test_client, auth_headers_admin, sample_template_data, clean_test_data):
        """Test updating a template"""
        # Create template
        create_response = test_client.post(
            "/api/template-management/templates",
            headers=auth_headers_admin,
            json=sample_template_data
        )
        template_id = create_response.json()["id"]
        
        # Update it
        update_data = {"name": "TEST_Updated Template"}
        response = test_client.put(
            f"/api/template-management/templates/{template_id}",
            headers=auth_headers_admin,
            json=update_data
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == update_data["name"]
    
    def test_delete_template(self, test_client, auth_headers_admin, sample_template_data, clean_test_data):
        """Test deleting a template"""
        # Create template
        create_response = test_client.post(
            "/api/template-management/templates",
            headers=auth_headers_admin,
            json=sample_template_data
        )
        template_id = create_response.json()["id"]
        
        # Delete it
        response = test_client.delete(
            f"/api/template-management/templates/{template_id}",
            headers=auth_headers_admin
        )
        assert response.status_code == status.HTTP_200_OK
    
    def test_unauthorized_access(self, test_client):
        """Test unauthorized access without token"""
        response = test_client.get("/api/template-management/templates")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_storage_info(self, test_client, auth_headers_user):
        """Test getting storage information"""
        response = test_client.get(
            "/api/template-management/storage/info",
            headers=auth_headers_user
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "storage_type" in data["data"]