import pytest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from app.models.models import Link, User


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
def test_link():
    """Create a test link."""
    return Link(
        id=1,
        short_code="abc123",
        original_url="https://example.com",
        created_at=datetime.now(timezone.utc),
        last_used_at=None,
        clicks=0,
        is_active=True,
        user_id=1
    )


def test_shorten_url(client, db_session, test_user):
    """Test creating a shortened URL."""
    # Mock authentication
    with patch('app.api.links.get_optional_current_user', return_value=test_user):
        # Mock link creation
        with patch('app.api.links.create_link') as mock_create:
            # Create a mock link to return
            mock_link = Link(
                id=1,
                short_code="abc123",
                original_url="https://example.com",
                created_at=datetime.now(timezone.utc),
                clicks=0,
                is_active=True,
                user_id=test_user.id
            )
            mock_create.return_value = mock_link
            
            # Make the request
            response = client.post(
                "/links/shorten",
                json={"original_url": "https://example.com"}
            )
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["short_code"] == "abc123"
            assert data["original_url"] == "https://example.com"
            
            # Verify the mock was called with correct args
            mock_create.assert_called_once()


def test_search_links(client, db_session):
    """Test searching for links by original URL."""
    # Mock the search function
    with patch('app.api.links.search_by_original_url') as mock_search:
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
        mock_search.return_value = mock_links
        
        # Make the request
        response = client.get("/links/search?original_url=example.com")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["short_code"] == "abc123"
        assert data[1]["short_code"] == "def456"
        
        # Verify mock was called correctly
        mock_search.assert_called_once_with(db_session, "example.com")


def test_redirect_to_url(client, db_session, test_link):
    """Test redirecting to the original URL."""
    # Mock get_link_by_short_code
    with patch('app.api.links.get_link_by_short_code', return_value=test_link):
        # Make the request
        response = client.get(f"/links/{test_link.short_code}")
        
        # Assertions
        assert response.status_code == 307
        assert response.headers["location"] == test_link.original_url


def test_get_link_info(client, db_session, test_link):
    """Test getting link statistics."""
    # Mock get_link_by_short_code
    with patch('app.api.links.get_link_by_short_code', return_value=test_link):
        # Make the request
        response = client.get(f"/links/{test_link.short_code}/stats")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["short_code"] == test_link.short_code
        assert data["original_url"] == test_link.original_url
        assert data["clicks"] == test_link.clicks


def test_link_not_found(client, db_session):
    """Test behavior when a link is not found."""
    # Mock get_link_by_short_code to return None
    with patch('app.api.links.get_link_by_short_code', return_value=None):
        # Test redirect endpoint
        response = client.get("/links/nonexistent")
        assert response.status_code == 404
        
        # Test stats endpoint
        response = client.get("/links/nonexistent/stats")
        assert response.status_code == 404


def test_update_link(client, db_session, test_user, test_link):
    """Test updating a link."""
    # Mock authentication
    with patch('app.api.links.get_current_active_user', return_value=test_user):
        # Mock update_link
        updated_link = test_link
        updated_link.original_url = "https://updated-example.com"
        
        with patch('app.api.links.update_link', return_value=updated_link):
            # Make the request
            response = client.put(
                f"/links/{test_link.short_code}",
                json={"original_url": "https://updated-example.com"}
            )
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["original_url"] == "https://updated-example.com"


def test_delete_link(client, db_session, test_user):
    """Test deleting a link."""
    # Mock authentication
    with patch('app.api.links.get_current_active_user', return_value=test_user):
        # Mock delete_link to return True (success)
        with patch('app.api.links.delete_link', return_value=True):
            # Make the request
            response = client.delete("/links/abc123")
            
            # Assertions
            assert response.status_code == 204


def test_delete_link_not_found(client, db_session, test_user):
    """Test deleting a non-existent link."""
    # Mock authentication
    with patch('app.api.links.get_current_active_user', return_value=test_user):
        # Mock delete_link to return False (not found)
        with patch('app.api.links.delete_link', return_value=False):
            # Make the request
            response = client.delete("/links/nonexistent")
            
            # Assertions
            assert response.status_code == 404 