import pytest
from unittest.mock import patch
from datetime import datetime, timezone

from app.models.models import User, Link


@pytest.fixture
def admin_user():
    """Create an admin user for testing."""
    return User(
        id=1,
        username="adminuser",
        email="admin@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=True,
        created_at=datetime.now(timezone.utc)
    )


def test_get_all_users(client, db_session, admin_user):
    """Test getting all users endpoint."""
    # Mock authentication
    with patch('app.api.admin.get_current_admin_user', return_value=admin_user):
        # Mock get_all_users
        with patch('app.api.admin.get_all_users') as mock_get_users:
            # Create mock users to return
            mock_users = [
                admin_user,
                User(
                    id=2,
                    username="user2",
                    email="user2@example.com",
                    hashed_password="hashed_password",
                    is_active=True,
                    is_admin=False,
                    created_at=datetime.now(timezone.utc)
                )
            ]
            mock_get_users.return_value = mock_users
            
            # Make the request
            response = client.get("/admin/users")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["username"] == "adminuser"
            assert data[1]["username"] == "user2"
            
            # Verify mock was called correctly
            mock_get_users.assert_called_once_with(db_session)


def test_get_all_links(client, db_session, admin_user):
    """Test getting all links endpoint."""
    # Mock authentication
    with patch('app.api.admin.get_current_admin_user', return_value=admin_user):
        # Mock get_all_links
        with patch('app.api.admin.get_all_links') as mock_get_links:
            # Create mock links to return
            mock_links = [
                Link(
                    id=1,
                    short_code="abc123",
                    original_url="https://example.com/page1",
                    created_at=datetime.now(timezone.utc),
                    clicks=5,
                    is_active=True
                ),
                Link(
                    id=2,
                    short_code="def456",
                    original_url="https://example.com/page2",
                    created_at=datetime.now(timezone.utc),
                    clicks=10,
                    is_active=True
                )
            ]
            mock_get_links.return_value = mock_links
            
            # Make the request
            response = client.get("/admin/links")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["short_code"] == "abc123"
            assert data[1]["short_code"] == "def456"
            
            # Verify mock was called correctly
            mock_get_links.assert_called_once_with(db_session)


def test_admin_access_required(client, db_session):
    """Test that non-admin users cannot access admin endpoints."""
    # Mock authentication to return non-admin user
    non_admin_user = User(
        id=2,
        username="regularuser",
        email="user@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(timezone.utc)
    )
    
    # Test with a mock that raises an HTTP exception for non-admin users
    with patch('app.api.admin.get_current_admin_user') as mock_auth:
        from fastapi import HTTPException
        mock_auth.side_effect = HTTPException(status_code=403, detail="Not an admin")
        
        # Try to access admin endpoints
        response = client.get("/admin/users")
        assert response.status_code == 403
        
        response = client.get("/admin/links")
        assert response.status_code == 403


def test_cleanup_expired_links(client, db_session, admin_user):
    """Test the cleanup expired links endpoint."""
    # Mock authentication
    with patch('app.api.admin.get_current_admin_user', return_value=admin_user):
        # Mock cleanup function
        with patch('app.api.admin.cleanup_expired_links') as mock_cleanup:
            mock_cleanup.return_value = 3  # 3 links cleaned up
            
            # Make the request
            response = client.post("/admin/cleanup-expired")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["cleanup_count"] == 3
            
            # Verify mock was called correctly
            mock_cleanup.assert_called_once_with(db_session) 