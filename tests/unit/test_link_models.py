import pytest
from datetime import datetime, timezone, timedelta
from app.models.models import Link, User


def test_link_model_creation():
    """Test creating a Link model."""
    # Create a test user
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(timezone.utc)
    )
    
    # Create a link with all fields
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=7)
    
    link = Link(
        id=1,
        short_code="abc123",
        original_url="https://example.com",
        custom_alias="mylink",
        created_at=now,
        last_used_at=now,
        expires_at=expires_at,
        clicks=5,
        is_active=True,
        user_id=user.id
    )
    
    # Verify all fields
    assert link.id == 1
    assert link.short_code == "abc123"
    assert link.original_url == "https://example.com"
    assert link.custom_alias == "mylink"
    assert link.created_at == now
    assert link.last_used_at == now
    assert link.expires_at == expires_at
    assert link.clicks == 5
    assert link.is_active is True
    assert link.user_id == user.id


def test_link_with_minimal_fields():
    """Test creating a Link with only required fields."""
    link = Link(
        short_code="abc123",
        original_url="https://example.com",
        created_at=datetime.now(timezone.utc),
        clicks=0,  # Set default clicks explicitly
        is_active=True  # Set is_active explicitly
    )
    
    assert link.short_code == "abc123"
    assert link.original_url == "https://example.com"
    assert link.custom_alias is None
    assert link.last_used_at is None
    assert link.expires_at is None
    assert link.clicks == 0
    assert link.is_active is True
    assert link.user_id is None 