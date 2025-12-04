"""
Pytest Configuration and Fixtures
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from auth.auth_handler import create_access_token
import pyodbc
from database import get_connection_string


@pytest.fixture(scope="session")
def test_client():
    """Create test client for API testing"""
    return TestClient(app)


@pytest.fixture(scope="session")
def admin_token():
    """Generate admin token for testing"""
    token = create_access_token(data={"sub": "admin", "role": "admin"})
    return token


@pytest.fixture(scope="session")
def user_token():
    """Generate user token for testing"""
    token = create_access_token(data={"sub": "testuser", "role": "user"})
    return token


@pytest.fixture(scope="session")
def auth_headers_admin(admin_token):
    """Admin authorization headers"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def auth_headers_user(user_token):
    """User authorization headers"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="function")
def db_connection():
    """Database connection for testing"""
    conn = pyodbc.connect(get_connection_string())
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def clean_test_data(db_connection):
    """Clean test data before and after tests"""
    cursor = db_connection.cursor()
    
    # Clean before test
    cursor.execute("DELETE FROM Templates WHERE name LIKE 'TEST_%'")
    cursor.execute("DELETE FROM Rulesets WHERE ruleset_name LIKE 'TEST_%'")
    cursor.execute("DELETE FROM Workflows WHERE workflow_name LIKE 'TEST_%'")
    cursor.execute("DELETE FROM HIEConfigurations WHERE config_name LIKE 'TEST_%'")
    db_connection.commit()
    
    yield
    
    # Clean after test
    cursor.execute("DELETE FROM Templates WHERE name LIKE 'TEST_%'")
    cursor.execute("DELETE FROM Rulesets WHERE ruleset_name LIKE 'TEST_%'")
    cursor.execute("DELETE FROM Workflows WHERE workflow_name LIKE 'TEST_%'")
    cursor.execute("DELETE FROM HIEConfigurations WHERE config_name LIKE 'TEST_%'")
    db_connection.commit()


@pytest.fixture
def sample_template_data():
    """Sample template data for testing"""
    return {
        "name": "TEST_Sample Template",
        "description": "Test template description",
        "template_type": "FHIR"
    }


@pytest.fixture
def sample_ruleset_data():
    """Sample ruleset data for testing"""
    return {
        "ruleset_name": "TEST_Sample Ruleset",
        "rule_definition": {
            "condition": "age > 18",
            "action": "approve",
            "parameters": {"min_age": 18}
        },
        "priority": 1,
        "is_active": True
    }


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing"""
    return {
        "workflow_name": "TEST_Sample Workflow",
        "workflow_definition": {
            "version": "1.0",
            "steps": [
                {
                    "step_id": "step1",
                    "step_name": "Validation",
                    "step_type": "validation",
                    "configuration": {},
                    "next_step": "step2"
                },
                {
                    "step_id": "step2",
                    "step_name": "Processing",
                    "step_type": "process",
                    "configuration": {}
                }
            ]
        },
        "status": "draft"
    }


@pytest.fixture
def sample_hie_config_data():
    """Sample HIE config data for testing"""
    return {
        "config_name": "TEST_Sample HIE Config",
        "config_data": {
            "endpoint": "https://test.example.com",
            "timeout": 30
        },
        "is_active": True
    }