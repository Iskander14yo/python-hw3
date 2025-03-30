import pytest
from fastapi.testclient import TestClient

# We don't need to define a test_client fixture here anymore as it's in conftest.py

# Example basic test (can be expanded)
def test_read_root(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to URL Shortener API"}


def test_api_docs(client):
    """Test that the API documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_schema(client):
    """Test that the OpenAPI schema is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    
    # Verify some basic structure of the OpenAPI schema
    schema = response.json()
    assert "paths" in schema
    assert "components" in schema
    assert "schemas" in schema["components"]
    
    # Verify some of our API paths are in the schema
    assert "/links/shorten" in schema["paths"]
    assert "/links/{short_code}" in schema["paths"]
    assert "/auth/login" in schema["paths"]

# Add more tests for your specific endpoints below
# e.g., test_create_short_link, test_redirect_short_link, etc. 