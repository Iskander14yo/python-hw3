import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from app.services.link_service import create_link, generate_short_code
from app.models.schemas import LinkCreate
from app.models.models import Link, User


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    # Mock the query chain for checking existing short codes
    db.query.return_value.filter.return_value.first.return_value = None
    return db


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


def test_create_link_generate_short_code(mock_db):
    """Test create_link with auto-generated short code."""
    # Setup
    link_data = LinkCreate(original_url="https://example.com")
    
    # Mock generate_short_code to return a fixed value
    with patch('app.services.link_service.generate_short_code', return_value='abc123'):
        result = create_link(mock_db, link_data)
        
        # Assertions
        assert result.short_code == 'abc123'
        assert result.original_url == "https://example.com"
        assert result.custom_alias is None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


def test_create_link_with_custom_alias(mock_db):
    """Test create_link with a custom alias."""
    # Setup
    link_data = LinkCreate(
        original_url="https://example.com",
        custom_alias="mylink"
    )
    
    result = create_link(mock_db, link_data)
    
    # Assertions
    assert result.short_code == "mylink"
    assert result.original_url == "https://example.com"
    assert result.custom_alias == "mylink"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


def test_create_link_with_expiration(mock_db):
    """Test create_link with an expiration date."""
    # Setup
    now = datetime.now()
    expires_at = now + timedelta(days=7)
    link_data = LinkCreate(
        original_url="https://example.com",
        expires_at=expires_at
    )
    
    # Mock generate_short_code to return a fixed value
    with patch('app.services.link_service.generate_short_code', return_value='abc123'):
        result = create_link(mock_db, link_data)
        
        # Assertions
        assert result.short_code == 'abc123'
        assert result.original_url == "https://example.com"
        assert result.expires_at == expires_at
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


def test_create_link_with_user(mock_db, test_user):
    """Test create_link with a user."""
    # Setup
    link_data = LinkCreate(original_url="https://example.com")
    
    # Mock generate_short_code to return a fixed value
    with patch('app.services.link_service.generate_short_code', return_value='abc123'):
        result = create_link(mock_db, link_data, test_user)
        
        # Assertions
        assert result.short_code == 'abc123'
        assert result.original_url == "https://example.com"
        assert result.user_id == test_user.id
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once() 