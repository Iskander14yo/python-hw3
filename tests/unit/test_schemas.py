import pytest
from datetime import datetime, timezone
from app.models.schemas import LinkCreate, LinkUpdate, Link, User, UserCreate


def test_link_create_schema():
    """Test creating a LinkCreate schema."""
    # Test with minimum required fields
    link_data = LinkCreate(original_url="https://example.com")
    assert link_data.original_url == "https://example.com"
    assert link_data.custom_alias is None
    assert link_data.expires_at is None
    
    # Test with all fields
    now = datetime.now(timezone.utc)
    link_data_full = LinkCreate(
        original_url="https://example.com",
        custom_alias="mylink",
        expires_at=now
    )
    assert link_data_full.original_url == "https://example.com"
    assert link_data_full.custom_alias == "mylink"
    assert link_data_full.expires_at == now


def test_link_update_schema():
    """Test creating a LinkUpdate schema."""
    # Test with empty fields
    link_update = LinkUpdate()
    assert link_update.original_url is None
    assert link_update.custom_alias is None
    assert link_update.expires_at is None
    
    # Test with some fields
    link_update = LinkUpdate(original_url="https://updated.example.com")
    assert link_update.original_url == "https://updated.example.com"
    assert link_update.custom_alias is None
    
    # Test with all fields
    now = datetime.now(timezone.utc)
    link_update = LinkUpdate(
        original_url="https://updated.example.com",
        custom_alias="updatedlink",
        expires_at=now
    )
    assert link_update.original_url == "https://updated.example.com"
    assert link_update.custom_alias == "updatedlink"
    assert link_update.expires_at == now


def test_user_create_schema():
    """Test creating a UserCreate schema."""
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="password123"
    )
    assert user_data.username == "testuser"
    assert user_data.email == "test@example.com"
    assert user_data.password == "password123" 