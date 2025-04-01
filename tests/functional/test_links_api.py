from fastapi.testclient import TestClient
import pytest
from datetime import datetime, timedelta, timezone
from app.main import app

def test_shorten_url_anonymous(client):
    """Test URL shortening without authentication"""
    link_data = {
        "original_url": "https://example.com",
        "custom_alias": None,
        "expires_at": None
    }
    response = client.post("/links/shorten", json=link_data)
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == link_data["original_url"]
    assert len(data["short_code"]) == 6

def test_shorten_url_authenticated(client, user_headers):
    """Test URL shortening with authentication"""
    link_data = {
        "original_url": "https://example.com",
        "custom_alias": "custom",
        "expires_at": None
    }
    response = client.post("/links/shorten", json=link_data, headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == link_data["original_url"]
    assert data["short_code"] == link_data["custom_alias"]

def test_search_links(client, test_link):
    """Test searching links by original URL"""
    response = client.get(f"/links/search?original_url={test_link.original_url}")
    assert response.status_code == 200
    links = response.json()
    assert isinstance(links, list)
    assert any(link["short_code"] == test_link.short_code for link in links)

def test_redirect_to_url(client, test_link):
    """Test URL redirection"""
    response = client.get(f"/links/{test_link.short_code}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == test_link.original_url

def test_get_link_stats(client, test_link):
    """Test getting link statistics"""
    response = client.get(f"/links/{test_link.short_code}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == test_link.short_code
    assert data["original_url"] == test_link.original_url
    assert "clicks" in data

def test_update_link(client, test_link, user_headers):
    """Test updating link information"""
    update_data = {
        "original_url": "https://updated-example.com",
        "custom_alias": None,
        "expires_at": None
    }
    response = client.put(
        f"/links/{test_link.short_code}",
        json=update_data,
        headers=user_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == update_data["original_url"]

def test_delete_link(client, test_link, user_headers):
    """Test deleting a link"""
    response = client.delete(
        f"/links/{test_link.short_code}",
        headers=user_headers
    )
    assert response.status_code == 204

    # Verify link is deleted
    response = client.get(f"/links/{test_link.short_code}/stats")
    assert response.status_code == 404

def test_expired_link(client):
    """Test handling of expired links"""
    # Create a link that expires immediately
    link_data = {
        "original_url": "https://example.com",
        "custom_alias": None,
        "expires_at": (datetime.now() - timedelta(days=1)).isoformat()
    }
    response = client.post("/links/shorten", json=link_data)
    assert response.status_code == 200
    short_code = response.json()["short_code"]

    # Try to access expired link
    response = client.get(f"/links/{short_code}")
    assert response.status_code == 404

def test_invalid_short_code(client):
    """Test handling of invalid short codes"""
    response = client.get("/links/invalid123")
    assert response.status_code == 404

def test_unauthorized_link_update(client, test_link):
    """Test unauthorized link update"""
    update_data = {
        "original_url": "https://updated-example.com",
        "custom_alias": None,
        "expires_at": None
    }
    # Try to update without authentication
    response = client.put(f"/links/{test_link.short_code}", json=update_data)
    assert response.status_code == 401 