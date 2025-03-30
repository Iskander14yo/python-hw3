import pytest
from unittest.mock import patch
from datetime import datetime, timezone

from app.models.models import User


@pytest.fixture
def test_user():
    """Create a test user."""
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(timezone.utc)
    )


def test_register_user(client, db_session):
    """Test user registration endpoint."""
    # Mock user creation
    with patch('app.api.auth.create_user') as mock_create:
        # Create a mock user to return
        mock_user = User(
            id=1,
            username="newuser",
            email="new@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_admin=False,
            created_at=datetime.now(timezone.utc)
        )
        mock_create.return_value = mock_user
        
        # Make the request
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123"
            }
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert "id" in data
        
        # Verify mock was called correctly
        mock_create.assert_called_once()


def test_login(client, db_session, test_user):
    """Test login endpoint."""
    # Mock user authentication
    with patch('app.api.auth.authenticate_user', return_value=test_user):
        # Mock token creation
        with patch('app.api.auth.create_access_token') as mock_token:
            mock_token.return_value = "mock_token"
            
            # Make the request
            response = client.post(
                "/auth/login",
                data={"username": "testuser", "password": "password123"}
            )
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "mock_token"
            assert data["token_type"] == "bearer"
            
            # Verify mocks were called correctly
            mock_token.assert_called_once()


def test_login_invalid_credentials(client, db_session):
    """Test login with invalid credentials."""
    # Mock failed authentication
    with patch('app.api.auth.authenticate_user', return_value=False):
        # Make the request
        response = client.post(
            "/auth/login",
            data={"username": "wronguser", "password": "wrongpass"}
        )
        
        # Assertions
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


def test_get_current_user(client, db_session, test_user):
    """Test getting the current user endpoint."""
    # Mock authentication
    with patch('app.api.auth.get_current_active_user', return_value=test_user):
        # Make the request
        response = client.get("/auth/me")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id 