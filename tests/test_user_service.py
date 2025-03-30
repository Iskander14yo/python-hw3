import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.services.user_service import (
    create_user,
    get_user_by_username,
    get_user_by_email,
    authenticate_user
)
from app.models.models import User, Link
from app.models.schemas import UserCreate
from app.core.auth import get_password_hash


@pytest.fixture
def mock_db():
    """Create a mock database session for testing."""
    db = MagicMock(spec=Session)
    return db


def test_get_user_by_username(mock_db):
    """Test getting a user by username."""
    # Create mock user
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True
    )
    
    # Mock query result
    mock_db.query.return_value.filter.return_value.first.return_value = user
    
    # Call the function
    result = get_user_by_username(mock_db, "testuser")
    
    # Assertions
    assert result == user
    mock_db.query.assert_called_once_with(User)
    mock_db.query.return_value.filter.assert_called_once()
    
    # Test for non-existent user
    mock_db.query.return_value.filter.return_value.first.return_value = None
    result = get_user_by_username(mock_db, "nonexistent")
    assert result is None


def test_get_user_by_email(mock_db):
    """Test getting a user by email."""
    # Create mock user
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True
    )
    
    # Mock query result
    mock_db.query.return_value.filter.return_value.first.return_value = user
    
    # Call the function
    result = get_user_by_email(mock_db, "test@example.com")
    
    # Assertions
    assert result == user
    mock_db.query.assert_called_once_with(User)
    mock_db.query.return_value.filter.assert_called_once()
    
    # Test for non-existent email
    mock_db.query.return_value.filter.return_value.first.return_value = None
    result = get_user_by_email(mock_db, "nonexistent@example.com")
    assert result is None


def test_create_user(mock_db):
    """Test creating a new user."""
    # Create mock user data
    user_data = UserCreate(
        username="newuser",
        email="new@example.com",
        password="password123"
    )
    
    # Mock query result for existing users check (none exist)
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    # Call the function
    with patch('app.services.user_service.get_password_hash', return_value="hashed_password"):
        result = create_user(mock_db, user_data)
    
    # Assertions
    assert result.username == "newuser"
    assert result.email == "new@example.com"
    assert result.hashed_password == "hashed_password"
    assert result.is_admin is False
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


def test_create_admin_user(mock_db):
    """Test creating an admin user."""
    # Create mock user data
    user_data = UserCreate(
        username="admin",
        email="admin@example.com",
        password="adminpass"
    )
    
    # Mock query result for existing users check (none exist)
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    # Call the function with is_admin=True
    with patch('app.services.user_service.get_password_hash', return_value="hashed_password"):
        result = create_user(mock_db, user_data, is_admin=True)
    
    # Assertions
    assert result.username == "admin"
    assert result.email == "admin@example.com"
    assert result.hashed_password == "hashed_password"
    assert result.is_admin is True
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


def test_authenticate_user_success(mock_db):
    """Test successful user authentication."""
    # Create mock user with known password
    hashed_password = get_password_hash("password123")
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_password,
        is_active=True
    )
    
    # Mock query result and password verification
    mock_db.query.return_value.filter.return_value.first.return_value = user
    
    with patch('app.services.user_service.verify_password', return_value=True):
        # Call the function
        result = authenticate_user(mock_db, "testuser", "password123")
        
        # Assertions
        assert result == user
        mock_db.query.assert_called_once_with(User)


def test_authenticate_user_wrong_password(mock_db):
    """Test authentication with wrong password."""
    # Create mock user
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True
    )
    
    # Mock query result but verification fails
    mock_db.query.return_value.filter.return_value.first.return_value = user
    
    with patch('app.services.user_service.verify_password', return_value=False):
        # Call the function
        result = authenticate_user(mock_db, "testuser", "wrong_password")
        
        # Assertions
        assert result is None
        mock_db.query.assert_called_once_with(User)


def test_authenticate_user_not_found(mock_db):
    """Test authentication with non-existent user."""
    # Mock query result for non-existent user
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    # Call the function
    result = authenticate_user(mock_db, "nonexistent", "password123")
    
    # Assertions
    assert result is None
    mock_db.query.assert_called_once_with(User) 