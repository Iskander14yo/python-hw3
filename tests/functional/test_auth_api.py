from fastapi.testclient import TestClient
import pytest
from app.main import app

def test_login_success(client, test_user, test_user_password):
    """Test successful login"""
    response = client.post(
        "/token",
        data={
            "username": test_user.username,
            "password": test_user_password
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    response = client.post(
        "/token",
        data={
            "username": "nonexistent",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

def test_register_success(client):
    """Test successful user registration"""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "strongpassword123"
    }
    response = client.post("/register", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "password" not in data  # Password should not be in response

def test_register_duplicate_username(client, test_user):
    """Test registration with existing username"""
    user_data = {
        "username": test_user.username,  # Using existing username
        "email": "different@example.com",
        "password": "strongpassword123"
    }
    response = client.post("/register", json=user_data)
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]

def test_register_duplicate_email(client, test_user):
    """Test registration with existing email"""
    user_data = {
        "username": "differentuser",
        "email": test_user.email,  # Using existing email
        "password": "strongpassword123"
    }
    response = client.post("/register", json=user_data)
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]
