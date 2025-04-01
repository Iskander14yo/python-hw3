import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.services.link_service import (
    create_link,
    get_link_by_short_code,
    get_link_stats,
    update_link,
    delete_link,
    search_by_original_url,
    cleanup_expired_links
)
from app.models.schemas import LinkCreate, LinkUpdate
from app.models.models import Link, User


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
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
def mock_db():
    """Create a mock database session for testing."""
    db = MagicMock(spec=Session)
    return db


def test_create_link_custom_alias_too_short(mock_db, mock_user):
    """Test creating a link with a custom alias that is too short."""
    # Prepare test data with short custom alias
    link_data = LinkCreate(
        original_url="https://example.com",
        custom_alias="abc",  # Too short (less than 4 chars)
        expires_at=None
    )
    
    # Call the function and expect exception
    with pytest.raises(HTTPException) as exc_info:
        create_link(mock_db, link_data, mock_user)
    
    # Assertions
    assert exc_info.value.status_code == 400
    assert "Custom alias must be at least 4 characters" in str(exc_info.value.detail)
    mock_db.add.assert_not_called()


def test_create_link_existing_custom_alias(mock_db, mock_user):
    """Test creating a link with a custom alias that already exists."""
    # Prepare test data
    link_data = LinkCreate(
        original_url="https://example.com",
        custom_alias="existing",
        expires_at=None
    )
    
    # Mock the database response for existing alias
    existing_link = Link(
        id=1,
        short_code="existing",
        original_url="https://other-example.com",
        custom_alias="existing",
        is_active=True
    )
    mock_db.query.return_value.filter.return_value.first.return_value = existing_link
    
    # Call the function and expect exception
    with pytest.raises(HTTPException) as exc_info:
        create_link(mock_db, link_data, mock_user)
    
    # Assertions
    assert exc_info.value.status_code == 400
    assert "Custom alias already exists" in str(exc_info.value.detail)
    mock_db.add.assert_not_called()


def test_create_link_existing_url_for_user(mock_db, mock_user):
    """Test creating a link with a URL that the user has already shortened."""
    # Prepare test data
    link_data = LinkCreate(
        original_url="https://example.com",
        custom_alias=None,
        expires_at=None
    )
    
    # Mock the database response for existing URL
    existing_link = Link(
        id=1,
        short_code="abc123",
        original_url="https://example.com",
        user_id=mock_user.id,
        is_active=True
    )
    
    # First query should return None (no custom alias)
    # Second query should find the existing URL for this user
    mock_db.query.return_value.filter.return_value.first.side_effect = [None, existing_link]
    
    # Call the function
    result = create_link(mock_db, link_data, mock_user)
    
    # Assertions
    assert result == existing_link
    mock_db.add.assert_not_called()  # Should not add a new link


# def test_create_link_expired_date_in_past(mock_db, mock_user):
#     """Test creating a link with an expiration date in the past."""
#     # Prepare test data with expiration in the past
#     expires_at = datetime.now(timezone.utc) - timedelta(days=1)
#     link_data = LinkCreate(
#         original_url="https://example.com",
#         custom_alias=None,
#         expires_at=expires_at
#     )
    
#     # Call the function and expect exception
#     with pytest.raises(HTTPException) as exc_info:
#         create_link(mock_db, link_data, mock_user)
    
#     # Assertions
#     assert exc_info.value.status_code == 400
#     assert "Expiration date must be in the future" in str(exc_info.value.detail)
#     mock_db.add.assert_not_called()


# def test_create_link_anonymous_user(mock_db):
#     """Test creating a link without a user (anonymous)."""
#     # Prepare test data
#     link_data = LinkCreate(
#         original_url="https://example.com",
#         custom_alias=None,
#         expires_at=None
#     )
    
#     # Mock the response from generate_short_code
#     with patch('app.services.link_service.generate_short_code', return_value="abc123"):
#         # Create link
#         link = create_link(mock_db, link_data, user=None)
        
#         # Assertions
#         assert link.short_code == "abc123"
#         assert link.original_url == "https://example.com"
#         assert link.user_id is None  # Anonymous user
#         mock_db.add.assert_called_once()
#         mock_db.commit.assert_called_once()
#         mock_db.refresh.assert_called_once()


def test_get_link_by_short_code_cache_hit(mock_db):
    """Test retrieving a link by short code with a Redis cache hit."""
    # Create mock link
    link = Link(
        id=1,
        short_code="abc123",
        original_url="https://example.com",
        created_at=datetime.now(timezone.utc),
        clicks=0,
        is_active=True
    )
    
    # Mock the database response
    mock_db.query.return_value.filter.return_value.first.return_value = link
    
    # Mock Redis with a cache hit
    redis_mock = MagicMock()
    redis_mock.get.return_value = "https://example.com"
    
    with patch('app.services.link_service.get_redis', return_value=redis_mock):
        # Get link
        result = get_link_by_short_code(mock_db, "abc123")
        
        # Assertions
        assert result == link
        assert result.clicks == 1  # Should increment on access
        mock_db.commit.assert_called_once()
        # Should not set cache because it was a cache hit
        redis_mock.set.assert_not_called()
        # Should verify from database even on cache hit
        mock_db.query.assert_called_once()


def test_get_link_by_short_code_no_redirect(mock_db):
    """Test retrieving a link without incrementing clicks (no redirect)."""
    # Create mock link
    link = Link(
        id=1,
        short_code="abc123",
        original_url="https://example.com",
        created_at=datetime.now(timezone.utc),
        clicks=5,
        is_active=True
    )
    
    # Mock the database response
    mock_db.query.return_value.filter.return_value.first.return_value = link
    
    # Mock Redis
    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    
    with patch('app.services.link_service.get_redis', return_value=redis_mock):
        # Get link with is_redirect=False
        result = get_link_by_short_code(mock_db, "abc123", is_redirect=False)
        
        # Assertions
        assert result == link
        assert result.clicks == 5  # Should not increment
        # Should still set in cache
        redis_mock.set.assert_called_once()


def test_get_link_stats(mock_db):
    """Test getting link statistics."""
    # Create mock link
    link = Link(
        id=1,
        short_code="abc123",
        original_url="https://example.com",
        created_at=datetime.now(timezone.utc),
        clicks=10,
        is_active=True
    )
    
    # Mock the database response
    mock_db.query.return_value.filter.return_value.first.return_value = link
    
    # Get link stats
    result = get_link_stats(mock_db, "abc123")
    
    # Assertions
    assert result == link
    mock_db.query.assert_called_once_with(Link)


def test_update_link_not_found(mock_db, mock_user):
    """Test updating a non-existent link."""
    # Mock the database response
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    # Prepare update data
    update_data = LinkUpdate(
        original_url="https://updated-example.com"
    )
    
    # Call the function
    result = update_link(mock_db, "nonexistent", update_data, mock_user)
    
    # Assertions
    assert result is None
    mock_db.commit.assert_not_called()


def test_update_link_unauthorized(mock_db, mock_user):
    """Test updating a link owned by another user."""
    # Create a link owned by another user
    other_user_id = 999  # Different from mock_user.id
    link = Link(
        id=1,
        short_code="abc123",
        original_url="https://example.com",
        user_id=other_user_id,
        is_active=True
    )
    
    # Mock the database response
    mock_db.query.return_value.filter.return_value.first.return_value = link
    
    # Prepare update data
    update_data = LinkUpdate(
        original_url="https://updated-example.com"
    )
    
    # Call the function and expect exception
    with pytest.raises(HTTPException) as exc_info:
        update_link(mock_db, "abc123", update_data, mock_user)
    
    # Assertions
    assert exc_info.value.status_code == 403
    assert "Not authorized to update this link" in str(exc_info.value.detail)
    mock_db.commit.assert_not_called()


def test_update_link_custom_alias_too_short(mock_db, mock_user):
    """Test updating a link with a custom alias that is too short."""
    # Create a link owned by the test user
    link = Link(
        id=1,
        short_code="abc123",
        original_url="https://example.com",
        custom_alias=None,
        user_id=mock_user.id,
        is_active=True
    )
    
    # Mock the database response
    mock_db.query.return_value.filter.return_value.first.return_value = link
    
    # Prepare update data with short alias
    update_data = LinkUpdate(
        custom_alias="abc"  # Too short
    )
    
    # Call the function and expect exception
    with pytest.raises(HTTPException) as exc_info:
        update_link(mock_db, "abc123", update_data, mock_user)
    
    # Assertions
    assert exc_info.value.status_code == 400
    assert "Custom alias must be at least 4 characters" in str(exc_info.value.detail)
    mock_db.commit.assert_not_called()


def test_delete_link_not_found(mock_db, mock_user):
    """Test deleting a non-existent link."""
    # Mock the database response
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    # Call the function
    result = delete_link(mock_db, "nonexistent", mock_user)
    
    # Assertions
    assert result is False
    mock_db.commit.assert_not_called()


def test_delete_link_unauthorized(mock_db, mock_user):
    """Test deleting a link owned by another user."""
    # Create a link owned by another user
    other_user_id = 999  # Different from mock_user.id
    link = Link(
        id=1,
        short_code="abc123",
        original_url="https://example.com",
        user_id=other_user_id,
        is_active=True
    )
    
    # Mock the database response
    mock_db.query.return_value.filter.return_value.first.return_value = link
    
    # Call the function and expect exception
    with pytest.raises(HTTPException) as exc_info:
        delete_link(mock_db, "abc123", mock_user)
    
    # Assertions
    assert exc_info.value.status_code == 403
    assert "Not authorized to delete this link" in str(exc_info.value.detail)
    mock_db.commit.assert_not_called()


def test_search_by_original_url(mock_db):
    """Test searching links by original URL."""
    # Create mock links
    links = [
        Link(
            id=1,
            short_code="abc123",
            original_url="https://example.com/page1",
            is_active=True
        ),
        Link(
            id=2,
            short_code="def456",
            original_url="https://example.com/page2",
            is_active=True
        )
    ]
    
    # Mock the database response
    mock_db.query.return_value.filter.return_value.all.return_value = links
    
    # Call the function
    result = search_by_original_url(mock_db, "example.com")
    
    # Assertions
    assert len(result) == 2
    assert result[0].short_code == "abc123"
    assert result[1].short_code == "def456"
    mock_db.query.assert_called_once_with(Link)


def test_cleanup_expired_links(mock_db):
    """Test cleaning up expired links."""
    # Create mock links that have expired
    expired_links = [
        Link(
            id=1,
            short_code="abc123",
            original_url="https://example.com/page1",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            is_active=True
        ),
        Link(
            id=2,
            short_code="def456",
            original_url="https://example.com/page2",
            expires_at=datetime.now(timezone.utc) - timedelta(days=2),
            is_active=True
        )
    ]
    
    # Mock the database response
    mock_db.query.return_value.filter.return_value.all.return_value = expired_links
    
    # Mock Redis
    redis_mock = MagicMock()
    
    with patch('app.services.link_service.get_redis', return_value=redis_mock):
        # Call the function
        count = cleanup_expired_links(mock_db)
        
        # Assertions
        assert count == 2
        assert expired_links[0].is_active is False
        assert expired_links[1].is_active is False
        mock_db.commit.assert_called_once()
        assert redis_mock.delete.call_count == 2  # Should delete both from cache 