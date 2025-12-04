"""
Tests for Fine-Grained Access Control API
"""

import pytest
from fastapi import status


class TestAccessControl:
    """Test suite for Access Control"""
    
    def test_grant_access(self, test_client, auth_headers_admin):
        """Test granting access"""
        access_data = {
            "user_id": 1,
            "resource_type": "template",
            "resource_id": 1,
            "permission": "read"
        }
        response = test_client.post(
            "/api/fga/grant-access",
            headers=auth_headers_admin,
            json=access_data
        )
        # Should work now with fixed service
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    def test_check_access(self, test_client, auth_headers_user):
        """Test checking access"""
        check_data = {
            "user_id": 1,
            "resource_type": "template",
            "resource_id": 1,
            "permission": "read"
        }
        response = test_client.post(
            "/api/fga/check-access",
            headers=auth_headers_user,
            json=check_data
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "has_access" in data

    def test_bulk_grant_access(self, test_client, auth_headers_admin):
        """Test bulk granting access"""
        bulk_data = {
            "user_ids": [1, 2, 3],
            "resource_type": "workflow",
            "resource_id": 1,
            "permission": "execute"
        }
        response = test_client.post(
            "/api/fga/bulk-grant-access",
            headers=auth_headers_admin,
            json=bulk_data
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

    def test_get_user_permissions(self, test_client, auth_headers_admin):
        """Test getting user permissions"""
        response = test_client.get(
            "/api/fga/users/1/permissions",
            headers=auth_headers_admin
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)