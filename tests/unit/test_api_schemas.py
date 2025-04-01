from fastapi.testclient import TestClient
from app.models.schemas import LinkCreate, LinkUpdate, UserCreate, Token
import pytest
from datetime import datetime, timezone

def test_link_create_schema():
    """Test LinkCreate schema validation"""
    # Valid data
    valid_data = {
        "original_url": "https://example.com",
        "custom_alias": None,
        "expires_at": None
    }
    link_create = LinkCreate(**valid_data)
    assert link_create.original_url == valid_data["original_url"]
    
    # Test with custom alias
    with_alias = {
        "original_url": "https://example.com",
        "custom_alias": "custom",
        "expires_at": None
    }
    link_create = LinkCreate(**with_alias)
    assert link_create.custom_alias == "custom"
    
    # Test with expiration
    expires = datetime.now(timezone.utc)
    with_expiry = {
        "original_url": "https://example.com",
        "custom_alias": None,
        "expires_at": expires
    }
    link_create = LinkCreate(**with_expiry)
    assert link_create.expires_at == expires

def test_link_update_schema():
    """Test LinkUpdate schema validation"""
    # Test valid update
    valid_update = {
        "original_url": "https://updated-example.com",
        "custom_alias": "new-alias",
        "expires_at": None
    }
    link_update = LinkUpdate(**valid_update)
    assert link_update.original_url == valid_update["original_url"]
    assert link_update.custom_alias == valid_update["custom_alias"]

def test_user_create_schema():
    """Test UserCreate schema validation"""
    valid_user = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "strongpassword123"
    }
    user_create = UserCreate(**valid_user)
    assert user_create.username == valid_user["username"]
    assert user_create.email == valid_user["email"]
    assert user_create.password == valid_user["password"]

def test_token_schema():
    """Test Token schema validation"""
    valid_token = {
        "access_token": "some.jwt.token",
        "token_type": "bearer"
    }
    token = Token(**valid_token)
    assert token.access_token == valid_token["access_token"]
    assert token.token_type == valid_token["token_type"] 