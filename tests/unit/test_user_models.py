import pytest
from datetime import datetime, timezone
from app.models.models import User


def test_user_model_creation():
    """Test creating a User model."""
    # Create a user with all fields
    now = datetime.now(timezone.utc)
    
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False,
        created_at=now
    )
    
    # Verify all fields
    assert user.id == 1
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.hashed_password == "hashed_password"
    assert user.is_active is True
    assert user.is_admin is False
    assert user.created_at == now


def test_admin_user_creation():
    """Test creating an admin user."""
    user = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=True,
        created_at=datetime.now(timezone.utc)
    )
    
    assert user.username == "adminuser"
    assert user.email == "admin@example.com"
    assert user.is_active is True
    assert user.is_admin is True  # Admin user 