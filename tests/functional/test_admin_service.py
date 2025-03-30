import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.services.admin_service import (
    get_recent_links,
    delete_user,
    get_all_users,
    force_delete_link
)
from app.models.models import User, Link


@pytest.fixture
def mock_db():
    """Create a mock database session for testing."""
    db = MagicMock(spec=Session)
    return db


def test_get_recent_links(mock_db):
    """Test getting recent links."""
    # Create mock links
    links = [
        Link(
            id=1,
            short_code="abc123",
            original_url="https://example1.com",
            created_at=datetime.now(timezone.utc),
            clicks=10,
            is_active=True
        ),
        Link(
            id=2,
            short_code="def456",
            original_url="https://example2.com",
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
            clicks=5,
            is_active=True
        )
    ]
    
    # Mock query result
    mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = links
    
    # Call the function
    result = get_recent_links(mock_db, limit=2)
    
    # Assertions
    assert len(result) == 2
    assert result[0].short_code == "abc123"
    assert result[1].short_code == "def456"
    mock_db.query.assert_called_once()
    mock_db.query.return_value.order_by.assert_called_once()
    mock_db.query.return_value.order_by.return_value.limit.assert_called_once_with(2)


def test_delete_user(mock_db):
    """Test deleting a user."""
    # Create mock user
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        is_active=True,
        is_admin=False
    )
    
    # Mock query results
    mock_db.query.return_value.filter.return_value.first.return_value = user
    mock_db.query.return_value.filter.return_value.all.return_value = [
        Link(short_code="link1", user_id=1, is_active=True),
        Link(short_code="link2", user_id=1, is_active=True)
    ]
    
    # Mock Redis
    redis_mock = MagicMock()
    
    with patch('app.services.admin_service.get_redis', return_value=redis_mock):
        # Call the function
        result = delete_user(mock_db, 1)
        
        # Assertions
        assert result is True
        mock_db.delete.assert_called_once_with(user)
        mock_db.commit.assert_called_once()
        assert redis_mock.delete.call_count == 2  # Two links to delete from cache


def test_delete_user_admin(mock_db):
    """Test deleting an admin user (should fail)."""
    # Create mock admin user
    admin_user = User(
        id=1,
        username="admin",
        email="admin@example.com",
        is_active=True,
        is_admin=True
    )
    
    # Mock query results
    mock_db.query.return_value.filter.return_value.first.return_value = admin_user
    
    # Call the function
    result = delete_user(mock_db, 1)
    
    # Assertions
    assert result is False
    mock_db.delete.assert_not_called()
    mock_db.commit.assert_not_called()


def test_delete_user_not_found(mock_db):
    """Test deleting a non-existent user."""
    # Mock query results for non-existent user
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    # Call the function
    result = delete_user(mock_db, 999)
    
    # Assertions
    assert result is False
    mock_db.delete.assert_not_called()
    mock_db.commit.assert_not_called()


def test_get_all_users(mock_db):
    """Test getting all users."""
    # Create mock users
    users = [
        User(id=1, username="user1", email="user1@example.com", is_active=True),
        User(id=2, username="user2", email="user2@example.com", is_active=True)
    ]
    
    # Mock query result
    mock_db.query.return_value.all.return_value = users
    
    # Call the function
    result = get_all_users(mock_db)
    
    # Assertions
    assert len(result) == 2
    assert result[0].username == "user1"
    assert result[1].username == "user2"
    mock_db.query.assert_called_once_with(User)


def test_force_delete_link(mock_db):
    """Test force deleting a link."""
    # Create mock link
    link = Link(
        id=1,
        short_code="abc123",
        original_url="https://example.com",
        is_active=True
    )
    
    # Mock query result
    mock_db.query.return_value.filter.return_value.first.return_value = link
    
    # Mock Redis
    redis_mock = MagicMock()
    
    with patch('app.services.admin_service.get_redis', return_value=redis_mock):
        # Call the function
        result = force_delete_link(mock_db, "abc123")
        
        # Assertions
        assert result is True
        assert link.is_active is False
        mock_db.commit.assert_called_once()
        redis_mock.delete.assert_called_once_with("link:abc123")


def test_force_delete_link_not_found(mock_db):
    """Test force deleting a non-existent link."""
    # Mock query result
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    # Call the function
    result = force_delete_link(mock_db, "nonexistent")
    
    # Assertions
    assert result is False
    mock_db.commit.assert_not_called() 