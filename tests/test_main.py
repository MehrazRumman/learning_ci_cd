import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_root_endpoint(self):
        """Test the root health check endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "FastAPI CI/CD Learning Project is running!"
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
        
        # Verify the response structure matches our HealthResponse model
        required_fields = ["message", "status", "timestamp", "version"]
        for field in required_fields:
            assert field in data
    
    def test_root_endpoint_response_structure(self):
        """Test that the response structure is correct"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check data types
        assert isinstance(data["message"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], str)  # ISO format string
        assert isinstance(data["version"], str)
        
        # Check specific values
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
    
    def test_docs_endpoint(self):
        """Test that the docs endpoint is accessible"""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_openapi_endpoint(self):
        """Test that the OpenAPI schema endpoint is accessible"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "openapi" in response.json()
