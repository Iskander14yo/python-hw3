import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from jose import jwt
from datetime import datetime, timedelta, timezone

from app.models.models import User, Link
from app.main import app
from app.core.auth import SECRET_KEY, ALGORITHM


# Setup test client
client = TestClient(app)


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


@pytest.fixture
def test_admin():
    """Create a test admin user."""
    return User(
        id=2,
        username="admin",
        email="admin@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=True,
        created_at=datetime.now(timezone.utc)
    )


def create_test_token(user_id, username, expires_delta=None):
    """Create a test JWT token."""
    to_encode = {"sub": username, "id": user_id}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_register_user():
    """Test registering a new user."""
    with patch("app.api.auth.create_user") as mock_create_user:
        # Setup mock
        mock_user = User(
            id=1,
            username="newuser",
            email="new@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_admin=False
        )
        mock_create_user.return_value = mock_user
        
        # Test endpoint
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123"
            }
        )
        
        # Assertions
        assert response.status_code == 201
        assert response.json()["username"] == "newuser"
        assert response.json()["email"] == "new@example.com"
        assert "hashed_password" not in response.json()
        mock_create_user.assert_called_once()


def test_login():
    """Test user login."""
    with patch("app.api.auth.authenticate_user") as mock_auth, \
         patch("app.api.auth.create_access_token") as mock_token:
        # Setup mocks
        mock_user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True
        )
        mock_auth.return_value = mock_user
        mock_token.return_value = "test_token"
        
        # Test endpoint
        response = client.post(
            "/api/auth/token",
            data={
                "username": "testuser",
                "password": "password123"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Assertions
        assert response.status_code == 200
        assert response.json()["access_token"] == "test_token"
        assert response.json()["token_type"] == "bearer"
        mock_auth.assert_called_once()
        mock_token.assert_called_once()


def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    with patch("app.api.auth.authenticate_user") as mock_auth:
        # Setup mock for failed authentication
        mock_auth.return_value = False
        
        # Test endpoint
        response = client.post(
            "/api/auth/token",
            data={
                "username": "testuser",
                "password": "wrong_password"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Assertions
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
        mock_auth.assert_called_once()


def test_get_user_me(test_user):
    """Test getting current user info."""
    token = create_test_token(test_user.id, test_user.username)
    
    with patch("app.api.auth.get_current_active_user") as mock_get_user:
        # Setup mock
        mock_get_user.return_value = test_user
        
        # Test endpoint
        response = client.get(
            "/api/auth/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assertions
        assert response.status_code == 200
        assert response.json()["username"] == test_user.username
        assert response.json()["email"] == test_user.email
        assert "hashed_password" not in response.json()
        mock_get_user.assert_called_once()


def test_update_user(test_user):
    """Test updating user information."""
    token = create_test_token(test_user.id, test_user.username)
    
    with patch("app.api.auth.get_current_active_user") as mock_get_user, \
         patch("app.api.auth.update_user") as mock_update:
        # Setup mocks
        mock_get_user.return_value = test_user
        updated_user = User(
            id=test_user.id,
            username=test_user.username,
            email="updated@example.com",
            hashed_password="new_hashed_password",
            is_active=True
        )
        mock_update.return_value = updated_user
        
        # Test endpoint
        response = client.put(
            "/api/auth/users/me",
            json={"email": "updated@example.com", "password": "newpassword"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assertions
        assert response.status_code == 200
        assert response.json()["email"] == "updated@example.com"
        mock_get_user.assert_called_once()
        mock_update.assert_called_once()


def test_create_link(test_user):
    """Test creating a new shortened link."""
    token = create_test_token(test_user.id, test_user.username)
    
    with patch("app.api.links.get_current_user") as mock_get_user, \
         patch("app.api.links.create_link") as mock_create:
        # Setup mocks
        mock_get_user.return_value = test_user
        link = Link(
            id=1,
            short_code="abc123",
            original_url="https://example.com",
            created_at=datetime.now(timezone.utc),
            user_id=test_user.id,
            is_active=True
        )
        mock_create.return_value = link
        
        # Test endpoint
        response = client.post(
            "/api/links/",
            json={"original_url": "https://example.com"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assertions
        assert response.status_code == 201
        assert response.json()["short_code"] == "abc123"
        assert response.json()["original_url"] == "https://example.com"
        mock_get_user.assert_called_once()
        mock_create.assert_called_once()


def test_create_link_anonymous():
    """Test creating a link without authentication."""
    with patch("app.api.links.get_optional_current_user") as mock_get_user, \
         patch("app.api.links.create_link") as mock_create:
        # Setup mocks
        mock_get_user.return_value = None
        link = Link(
            id=1,
            short_code="abc123",
            original_url="https://example.com",
            created_at=datetime.now(timezone.utc),
            user_id=None,
            is_active=True
        )
        mock_create.return_value = link
        
        # Test endpoint
        response = client.post(
            "/api/links/",
            json={"original_url": "https://example.com"}
        )
        
        # Assertions
        assert response.status_code == 201
        assert response.json()["short_code"] == "abc123"
        assert response.json()["original_url"] == "https://example.com"
        mock_get_user.assert_called_once()
        mock_create.assert_called_once()


def test_get_link(test_user):
    """Test getting a link by short code."""
    with patch("app.api.links.get_link_by_short_code") as mock_get_link:
        # Setup mock
        link = Link(
            id=1,
            short_code="abc123",
            original_url="https://example.com",
            created_at=datetime.now(timezone.utc),
            clicks=10,
            is_active=True
        )
        mock_get_link.return_value = link
        
        # Test endpoint
        response = client.get("/api/links/abc123")
        
        # Assertions
        assert response.status_code == 200
        assert response.json()["short_code"] == "abc123"
        assert response.json()["original_url"] == "https://example.com"
        assert response.json()["clicks"] == 10
        mock_get_link.assert_called_once_with(MagicMock(), "abc123", is_redirect=False)


def test_get_link_not_found():
    """Test getting a non-existent link."""
    with patch("app.api.links.get_link_by_short_code") as mock_get_link:
        # Setup mock
        mock_get_link.return_value = None
        
        # Test endpoint
        response = client.get("/api/links/nonexistent")
        
        # Assertions
        assert response.status_code == 404
        assert "Link not found" in response.json()["detail"]
        mock_get_link.assert_called_once()


def test_update_link(test_user):
    """Test updating a link."""
    token = create_test_token(test_user.id, test_user.username)
    
    with patch("app.api.links.get_current_active_user") as mock_get_user, \
         patch("app.api.links.update_link") as mock_update:
        # Setup mocks
        mock_get_user.return_value = test_user
        updated_link = Link(
            id=1,
            short_code="abc123",
            original_url="https://updated-example.com",
            created_at=datetime.now(timezone.utc),
            user_id=test_user.id,
            is_active=True
        )
        mock_update.return_value = updated_link
        
        # Test endpoint
        response = client.put(
            "/api/links/abc123",
            json={"original_url": "https://updated-example.com"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assertions
        assert response.status_code == 200
        assert response.json()["short_code"] == "abc123"
        assert response.json()["original_url"] == "https://updated-example.com"
        mock_get_user.assert_called_once()
        mock_update.assert_called_once()


def test_update_link_not_found(test_user):
    """Test updating a non-existent link."""
    token = create_test_token(test_user.id, test_user.username)
    
    with patch("app.api.links.get_current_active_user") as mock_get_user, \
         patch("app.api.links.update_link") as mock_update:
        # Setup mocks
        mock_get_user.return_value = test_user
        mock_update.return_value = None
        
        # Test endpoint
        response = client.put(
            "/api/links/nonexistent",
            json={"original_url": "https://updated-example.com"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assertions
        assert response.status_code == 404
        assert "Link not found" in response.json()["detail"]
        mock_get_user.assert_called_once()
        mock_update.assert_called_once()


def test_delete_link(test_user):
    """Test deleting a link."""
    token = create_test_token(test_user.id, test_user.username)
    
    with patch("app.api.links.get_current_active_user") as mock_get_user, \
         patch("app.api.links.delete_link") as mock_delete:
        # Setup mocks
        mock_get_user.return_value = test_user
        mock_delete.return_value = True
        
        # Test endpoint
        response = client.delete(
            "/api/links/abc123",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assertions
        assert response.status_code == 204
        mock_get_user.assert_called_once()
        mock_delete.assert_called_once()


def test_delete_link_not_found(test_user):
    """Test deleting a non-existent link."""
    token = create_test_token(test_user.id, test_user.username)
    
    with patch("app.api.links.get_current_active_user") as mock_get_user, \
         patch("app.api.links.delete_link") as mock_delete:
        # Setup mocks
        mock_get_user.return_value = test_user
        mock_delete.return_value = False
        
        # Test endpoint
        response = client.delete(
            "/api/links/nonexistent",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assertions
        assert response.status_code == 404
        assert "Link not found" in response.json()["detail"]
        mock_get_user.assert_called_once()
        mock_delete.assert_called_once()


def test_admin_get_user_stats(test_admin):
    """Test getting user statistics as admin."""
    token = create_test_token(test_admin.id, test_admin.username)
    
    with patch("app.api.admin.get_current_admin_user") as mock_get_admin, \
         patch("app.api.admin.get_user_stats") as mock_stats:
        # Setup mocks
        mock_get_admin.return_value = test_admin
        mock_stats.return_value = {
            "total_users": 10,
            "active_users": 8,
            "top_users_by_links": [
                {"username": "user1", "link_count": 15},
                {"username": "user2", "link_count": 10}
            ]
        }
        
        # Test endpoint
        response = client.get(
            "/api/admin/stats/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assertions
        assert response.status_code == 200
        assert response.json()["total_users"] == 10
        assert response.json()["active_users"] == 8
        assert len(response.json()["top_users_by_links"]) == 2
        mock_get_admin.assert_called_once()
        mock_stats.assert_called_once()


def test_admin_get_link_stats(test_admin):
    """Test getting link statistics as admin."""
    token = create_test_token(test_admin.id, test_admin.username)
    
    with patch("app.api.admin.get_current_admin_user") as mock_get_admin, \
         patch("app.api.admin.get_link_stats") as mock_stats:
        # Setup mocks
        mock_get_admin.return_value = test_admin
        mock_stats.return_value = {
            "total_links": 100,
            "active_links": 95,
            "total_clicks": 500,
            "popular_links": [
                {"short_code": "abc123", "clicks": 50},
                {"short_code": "def456", "clicks": 30}
            ]
        }
        
        # Test endpoint
        response = client.get(
            "/api/admin/stats/links",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assertions
        assert response.status_code == 200
        assert response.json()["total_links"] == 100
        assert response.json()["active_links"] == 95
        assert response.json()["total_clicks"] == 500
        assert len(response.json()["popular_links"]) == 2
        mock_get_admin.assert_called_once()
        mock_stats.assert_called_once()


def test_admin_delete_user(test_admin):
    """Test deleting a user as admin."""
    token = create_test_token(test_admin.id, test_admin.username)
    
    with patch("app.api.admin.get_current_admin_user") as mock_get_admin, \
         patch("app.api.admin.delete_user") as mock_delete:
        # Setup mocks
        mock_get_admin.return_value = test_admin
        mock_delete.return_value = True
        
        # Test endpoint
        response = client.delete(
            "/api/admin/users/testuser",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assertions
        assert response.status_code == 204
        mock_get_admin.assert_called_once()
        mock_delete.assert_called_once_with(MagicMock(), "testuser")


def test_admin_delete_user_not_found(test_admin):
    """Test deleting a non-existent user as admin."""
    token = create_test_token(test_admin.id, test_admin.username)
    
    with patch("app.api.admin.get_current_admin_user") as mock_get_admin, \
         patch("app.api.admin.delete_user") as mock_delete:
        # Setup mocks
        mock_get_admin.return_value = test_admin
        mock_delete.return_value = False
        
        # Test endpoint
        response = client.delete(
            "/api/admin/users/nonexistent",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assertions
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
        mock_get_admin.assert_called_once()
        mock_delete.assert_called_once()


def test_admin_deactivate_old_links(test_admin):
    """Test deactivating old links as admin."""
    token = create_test_token(test_admin.id, test_admin.username)
    
    with patch("app.api.admin.get_current_admin_user") as mock_get_admin, \
         patch("app.api.admin.deactivate_old_links") as mock_deactivate:
        # Setup mocks
        mock_get_admin.return_value = test_admin
        mock_deactivate.return_value = 5
        
        # Test endpoint
        response = client.post(
            "/api/admin/links/deactivate-old?days=30",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assertions
        assert response.status_code == 200
        assert response.json()["deactivated_count"] == 5
        mock_get_admin.assert_called_once()
        mock_deactivate.assert_called_once_with(MagicMock(), 30)


def test_admin_route_unauthorized(test_user):
    """Test accessing admin route with non-admin user."""
    token = create_test_token(test_user.id, test_user.username)
    
    with patch("app.api.admin.get_current_admin_user") as mock_get_admin:
        # Setup mock to raise exception for non-admin user
        mock_get_admin.side_effect = HTTPException(status_code=403, detail="Not an admin")
        
        # Test endpoint
        response = client.get(
            "/api/admin/stats/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assertions
        assert response.status_code == 403
        mock_get_admin.assert_called_once()


# Import this at the end to avoid circular imports
from fastapi import HTTPException 