import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from jose import jwt, JWTError
from datetime import datetime, timedelta
from app.core.auth import (
    verify_password,
    get_password_hash,
    get_user,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    get_optional_current_user,
    SECRET_KEY,
    ALGORITHM
)
from app.models.models import User


@patch('app.core.auth.pwd_context')
def test_verify_password(mock_pwd_context):
    """Test the password verification function"""
    # Setup mock
    mock_pwd_context.verify.return_value = True
    
    # Test function
    result = verify_password("password", "hashed_password")
    assert result is True
    
    # Test with different return value
    mock_pwd_context.verify.return_value = False
    result = verify_password("wrong_password", "hashed_password")
    assert result is False


@patch('app.core.auth.pwd_context')
def test_get_password_hash(mock_pwd_context):
    """Test the password hashing function"""
    # Setup mock
    mock_pwd_context.hash.return_value = "hashed_password"
    
    # Test function
    result = get_password_hash("password")
    assert result == "hashed_password"
    mock_pwd_context.hash.assert_called_once_with("password")


def test_get_user():
    """Test getting a user by username"""
    # Create mock DB session
    mock_db = MagicMock()
    
    # Create mock user
    user = User(
        id=1, 
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True
    )
    
    # Setup mock query
    mock_db.query.return_value.filter.return_value.first.return_value = user
    
    # Test function
    result = get_user(mock_db, "testuser")
    assert result == user
    mock_db.query.assert_called_once()
    
    # Test for non-existent user
    mock_db.query.return_value.filter.return_value.first.return_value = None
    result = get_user(mock_db, "nonexistent")
    assert result is None


@patch('app.core.auth.verify_password')
def test_authenticate_user(mock_verify_password):
    """Test user authentication function"""
    # Create mock DB session
    mock_db = MagicMock()
    
    # Create mock user
    user = User(
        id=1, 
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True
    )
    
    # Setup mock query and verification
    mock_db.query.return_value.filter.return_value.first.return_value = user
    mock_verify_password.return_value = True
    
    # Test successful authentication
    result = authenticate_user(mock_db, "testuser", "password")
    assert result == user
    mock_verify_password.assert_called_once_with("password", "hashed_password")
    
    # Test failed authentication - wrong password
    mock_verify_password.reset_mock()
    mock_verify_password.return_value = False
    result = authenticate_user(mock_db, "testuser", "wrong_password")
    assert result is False
    
    # Test failed authentication - user doesn't exist
    mock_db.query.return_value.filter.return_value.first.return_value = None
    result = authenticate_user(mock_db, "nonexistent", "password")
    assert result is False


@patch('app.core.auth.jwt.encode')
def test_create_access_token(mock_jwt_encode):
    """Test token creation function"""
    # Setup mock
    mock_jwt_encode.return_value = "mock_token"
    
    # Test with default expiration
    data = {"sub": "testuser"}
    token = create_access_token(data)
    assert token == "mock_token"
    
    # Verify jwt.encode was called with correct arguments
    mock_jwt_encode.assert_called_once()
    args, kwargs = mock_jwt_encode.call_args
    assert args[0]["sub"] == "testuser"
    assert "exp" in args[0]
    assert args[1] == SECRET_KEY  # Use the actual SECRET_KEY from the module
    assert kwargs["algorithm"] == ALGORITHM
    
    # Test with custom expiration
    mock_jwt_encode.reset_mock()
    expires = timedelta(minutes=15)
    token = create_access_token(data, expires)
    assert token == "mock_token"
    mock_jwt_encode.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_user():
    """Test getting current user from token"""
    # Setup mock db and user
    mock_db = MagicMock()
    user = User(
        id=1, 
        username="testuser",
        email="test@example.com",
        hashed_password="hashed",
        is_active=True
    )
    mock_db.query.return_value.filter.return_value.first.return_value = user
    
    # Mock jwt.decode function directly in the test
    with patch('app.core.auth.jwt.decode', return_value={"sub": "testuser"}):
        # Test successful user retrieval
        retrieved_user = await get_current_user(token="valid_token", db=mock_db)
        assert retrieved_user == user
    
    # Test with invalid token
    with patch('app.core.auth.jwt.decode', side_effect=JWTError("Invalid token")):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="invalid_token", db=mock_db)
        assert exc_info.value.status_code == 401
    
    # Test with valid token but user not found
    with patch('app.core.auth.jwt.decode', return_value={"sub": "testuser"}):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="valid_token", db=mock_db)
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_active_user():
    """Test getting active user"""
    # Test with active user
    active_user = User(
        id=1,
        username="active",
        email="active@example.com",
        is_active=True
    )
    retrieved_user = await get_current_active_user(current_user=active_user)
    assert retrieved_user == active_user
    
    # Test with inactive user
    inactive_user = User(
        id=2,
        username="inactive",
        email="inactive@example.com",
        is_active=False
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(current_user=inactive_user)
    assert exc_info.value.status_code == 400
    assert "Inactive user" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_admin_user():
    """Test getting admin user"""
    # Test with admin user
    admin_user = User(
        id=1,
        username="admin",
        email="admin@example.com",
        is_active=True,
        is_admin=True
    )
    retrieved_user = await get_current_admin_user(current_user=admin_user)
    assert retrieved_user == admin_user
    
    # Test with non-admin user
    regular_user = User(
        id=2,
        username="regular",
        email="regular@example.com",
        is_active=True,
        is_admin=False
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin_user(current_user=regular_user)
    assert exc_info.value.status_code == 403
    assert "does not have admin privileges" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_optional_current_user():
    """Test optional user authentication"""
    # Setup mock db and user
    mock_db = MagicMock()
    user = User(
        id=1, 
        username="testuser",
        email="test@example.com",
        hashed_password="hashed",
        is_active=True
    )
    mock_db.query.return_value.filter.return_value.first.return_value = user
    
    # Test with valid token
    with patch('app.core.auth.jwt.decode', return_value={"sub": "testuser"}):
        retrieved_user = await get_optional_current_user(token="valid_token", db=mock_db)
        assert retrieved_user == user
    
    # Test with no token
    no_token_user = await get_optional_current_user(token=None, db=mock_db)
    assert no_token_user is None
    
    # Test with invalid token
    with patch('app.core.auth.jwt.decode', side_effect=JWTError("Invalid token")):
        invalid_token_user = await get_optional_current_user(token="invalid_token", db=mock_db)
        assert invalid_token_user is None
    
    # Test with valid token but missing user
    with patch('app.core.auth.jwt.decode', return_value={"sub": "testuser"}):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        missing_user = await get_optional_current_user(token="valid_token", db=mock_db)
        assert missing_user is None 