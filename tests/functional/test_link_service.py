import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.services.link_service import (
    generate_short_code, 
    create_link, 
    get_link_by_short_code,
    update_link,
    delete_link,
    search_by_original_url
)
from app.models.schemas import LinkCreate, LinkUpdate
from app.models.models import Link, User


def test_generate_short_code():
    """Test that short code generation produces unique codes of the right length."""
    # Test default length
    code1 = generate_short_code()
    assert len(code1) == 6
    
    # Test custom length
    code2 = generate_short_code(length=8)
    assert len(code2) == 8
    
    # Test uniqueness
    code3 = generate_short_code()
    assert code1 != code3


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
    
    # Mock query results
    db.query.return_value.filter.return_value.first.return_value = None
    
    return db


def test_create_link(mock_db, mock_user):
    """Test creating a new shortened link."""
    # Prepare test data
    link_data = LinkCreate(
        original_url="https://example.com",
        custom_alias=None,
        expires_at=None
    )
    
    # Mock the response from generate_short_code
    with patch('app.services.link_service.generate_short_code', return_value="abc123"):
        # Create link
        link = create_link(mock_db, link_data, mock_user)
        
        # Assertions
        assert link.short_code == "abc123"
        assert link.original_url == "https://example.com"
        assert link.user_id == mock_user.id
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


def test_create_link_with_custom_alias(mock_db, mock_user):
    """Test creating a link with a custom alias."""
    # Prepare test data
    link_data = LinkCreate(
        original_url="https://example.com",
        custom_alias="mylink",
        expires_at=None
    )
    
    # Create link
    link = create_link(mock_db, link_data, mock_user)
    
    # Assertions
    assert link.short_code == "mylink"
    assert link.original_url == "https://example.com"
    assert link.custom_alias == "mylink"
    assert link.user_id == mock_user.id
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


def test_create_link_with_expiration(mock_db, mock_user):
    """Test creating a link with an expiration date."""
    # Prepare test data
    expires_at = datetime.now() + timedelta(days=7)
    link_data = LinkCreate(
        original_url="https://example.com",
        custom_alias=None,
        expires_at=expires_at
    )
    
    # Mock the response from generate_short_code
    with patch('app.services.link_service.generate_short_code', return_value="abc123"):
        # Create link
        link = create_link(mock_db, link_data, mock_user)
        
        # Assertions
        assert link.short_code == "abc123"
        assert link.original_url == "https://example.com"
        assert link.expires_at == expires_at
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


def test_get_link_by_short_code(mock_db):
    """Test retrieving a link by its short code."""
    # Mock the database response
    link = Link(
        id=1,
        short_code="abc123",
        original_url="https://example.com",
        created_at=datetime.now(timezone.utc),
        clicks=0,
        is_active=True
    )
    mock_db.query.return_value.filter.return_value.first.return_value = link
    
    # Mock Redis
    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    
    with patch('app.services.link_service.get_redis', return_value=redis_mock):
        # Get link
        result = get_link_by_short_code(mock_db, "abc123")
        
        # Assertions
        assert result == link
        assert result.clicks == 1  # Should increment on access
        mock_db.commit.assert_called_once()
        redis_mock.set.assert_called_once()


def test_update_link(mock_db, mock_user):
    """Test updating a link."""
    # Mock the database response
    link = Link(
        id=1,
        short_code="abc123",
        original_url="https://example.com",
        custom_alias=None,
        created_at=datetime.now(timezone.utc),
        clicks=0,
        is_active=True,
        user_id=mock_user.id
    )
    mock_db.query.return_value.filter.return_value.first.return_value = link
    
    # Prepare update data
    update_data = LinkUpdate(
        original_url="https://updated-example.com",
        custom_alias=None,
        expires_at=None
    )
    
    # Mock Redis
    redis_mock = MagicMock()
    
    with patch('app.services.link_service.get_redis', return_value=redis_mock):
        # Update link
        result = update_link(mock_db, "abc123", update_data, mock_user)
        
        # Assertions
        assert result == link
        assert result.original_url == "https://updated-example.com"
        mock_db.commit.assert_called_once()
        redis_mock.delete.assert_called_once()


def test_delete_link(mock_db, mock_user):
    """Test deleting a link."""
    # Mock the database response
    link = Link(
        id=1,
        short_code="abc123",
        original_url="https://example.com",
        created_at=datetime.now(timezone.utc),
        clicks=0,
        is_active=True,
        user_id=mock_user.id
    )
    mock_db.query.return_value.filter.return_value.first.return_value = link
    
    # Mock Redis
    redis_mock = MagicMock()
    
    with patch('app.services.link_service.get_redis', return_value=redis_mock):
        # Delete link
        result = delete_link(mock_db, "abc123", mock_user)
        
        # Assertions
        assert result is True
        assert link.is_active is False
        mock_db.commit.assert_called_once()
        redis_mock.delete.assert_called_once()


def test_search_by_original_url(mock_db):
    """Test searching for links by original URL."""
    # Mock the database response
    links = [
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
    mock_db.query.return_value.filter.return_value.all.return_value = links
    
    # Search for links
    results = search_by_original_url(mock_db, "example.com")
    
    # Assertions
    assert len(results) == 2
    assert results[0].short_code == "abc123"
    assert results[1].short_code == "def456" 