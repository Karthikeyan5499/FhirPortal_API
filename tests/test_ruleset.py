"""
Tests for Ruleset Management API
"""

import pytest
from fastapi import status


class TestRulesetManagement:
    """Test suite for Ruleset Management"""
    
    def test_get_all_rulesets(self, test_client, auth_headers_user):
        """Test getting all rulesets"""
        response = test_client.get(
            "/api/ruleset/rulesets",
            headers=auth_headers_user
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total" in data
        assert "rulesets" in data
    
    def test_create_ruleset(self, test_client, auth_headers_admin, sample_ruleset_data, clean_test_data):
        """Test creating a ruleset"""
        response = test_client.post(
            "/api/ruleset/rulesets",
            headers=auth_headers_admin,
            json=sample_ruleset_data
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["ruleset_name"] == sample_ruleset_data["ruleset_name"]
        assert data["priority"] == sample_ruleset_data["priority"]
    
    def test_get_ruleset_by_priority(self, test_client, auth_headers_user, auth_headers_admin, sample_ruleset_data, clean_test_data):
        """Test getting rulesets by priority"""
        # Create ruleset with priority 1
        test_client.post(
            "/api/ruleset/rulesets",
            headers=auth_headers_admin,
            json=sample_ruleset_data
        )
        
        # Get by priority
        response = test_client.get(
            "/api/ruleset/rulesets/priority/1",
            headers=auth_headers_user
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_execute_ruleset(self, test_client, auth_headers_user, auth_headers_admin, sample_ruleset_data, clean_test_data):
        """Test executing a ruleset"""
        # Create ruleset
        create_response = test_client.post(
            "/api/ruleset/rulesets",
            headers=auth_headers_admin,
            json=sample_ruleset_data
        )
        ruleset_id = create_response.json()["id"]
        
        # Update to active
        test_client.put(
            f"/api/ruleset/rulesets/{ruleset_id}",
            headers=auth_headers_admin,
            json={"is_active": True}
        )
        
        # Execute it
        execution_request = {
            "ruleset_id": ruleset_id,
            "input_data": {"age": 25, "name": "Test User"}
        }
        response = test_client.post(
            "/api/ruleset/rulesets/execute",
            headers=auth_headers_user,
            json=execution_request
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "executed" in data
        assert data["executed"] is True
    
    def test_delete_ruleset(self, test_client, auth_headers_admin, sample_ruleset_data, clean_test_data):
        """Test deleting a ruleset"""
        # Create ruleset
        create_response = test_client.post(
            "/api/ruleset/rulesets",
            headers=auth_headers_admin,
            json=sample_ruleset_data
        )
        ruleset_id = create_response.json()["id"]
        
        # Delete it
        response = test_client.delete(
            f"/api/ruleset/rulesets/{ruleset_id}",
            headers=auth_headers_admin
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT