from fastapi.testclient import TestClient
import pytest
from app.main import app

def test_delete_user(client, admin_headers, test_user):
    """Test deleting a user as admin"""
    response = client.delete(f"/admin/users/{test_user.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully"

    # Verify user is deleted
    response = client.get(f"/admin/users", headers=admin_headers)
    users = response.json()
    assert not any(user["id"] == test_user.id for user in users)

def test_get_recent_links(client, admin_headers, test_link):
    """Test getting recent links as admin"""
    response = client.get("/admin/links/recent", headers=admin_headers)
    assert response.status_code == 200
    links = response.json()
    assert isinstance(links, list)
    assert any(link["short_code"] == test_link.short_code for link in links)

def test_force_delete_link(client, admin_headers, test_link):
    """Test force deleting a link as admin"""
    response = client.delete(
        f"/admin/links/{test_link.short_code}", 
        headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Link deleted successfully"

    # Verify link is deleted
    response = client.get(f"/links/{test_link.short_code}/stats")
    assert response.status_code == 404

def test_get_all_users(client, admin_headers, test_user):
    """Test getting all users as admin"""
    response = client.get("/admin/users", headers=admin_headers)
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert any(user["id"] == test_user.id for user in users)

def test_unauthorized_access(client, user_headers):
    """Test unauthorized access to admin endpoints"""
    # Try accessing with non-admin user
    endpoints = [
        ("GET", "/admin/users"),
        ("GET", "/admin/links/recent"),
        ("DELETE", "/admin/users/1"),
        ("DELETE", "/admin/links/abc123")
    ]
    
    for method, endpoint in endpoints:
        if method == "GET":
            response = client.get(endpoint, headers=user_headers)
        else:
            response = client.delete(endpoint, headers=user_headers)
        assert response.status_code == 403 