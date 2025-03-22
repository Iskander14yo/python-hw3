from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import Base, get_db
from app.models.models import User
from app.core.auth import get_password_hash

# Set up test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Test data
test_user = {"username": "testuser", "email": "test@example.com", "password": "testpassword"}

test_link = {"original_url": "https://www.example.com/very/long/link", "custom_alias": "testlink"}


@pytest.fixture
def test_db():
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Override the get_db dependency
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Create test user
    db = TestingSessionLocal()
    hashed_password = get_password_hash(test_user["password"])
    db_user = User(
        username=test_user["username"], email=test_user["email"], hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()

    yield db

    # Teardown
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides = {}


@pytest.fixture
def client(test_db):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def token(client):
    response = client.post(
        "/token", data={"username": test_user["username"], "password": test_user["password"]}
    )
    return response.json()["access_token"]


def test_create_user(client):
    response = client.post(
        "/register",
        json={"username": "newuser", "email": "new@example.com", "password": "newpassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"


def test_login(client):
    response = client.post(
        "/token", data={"username": test_user["username"], "password": test_user["password"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_create_link(client, token):
    # Create with authentication
    response = client.post(
        "/links/shorten", json=test_link, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == test_link["original_url"]
    assert data["custom_alias"] == test_link["custom_alias"]

    # Create without authentication (should also work)
    response = client.post(
        "/links/shorten", json={"original_url": "https://www.example.com/another/long/link"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == "https://www.example.com/another/long/link"
    assert data["user_id"] is None  # No user associated


def test_get_link_info(client, token):
    # First create a link
    client.post("/links/shorten", json=test_link, headers={"Authorization": f"Bearer {token}"})

    # Then get its info
    response = client.get(f"/links/{test_link['custom_alias']}")
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == test_link["original_url"]
    assert data["custom_alias"] == test_link["custom_alias"]


def test_get_link_stats(client, token):
    # First create a link
    client.post("/links/shorten", json=test_link, headers={"Authorization": f"Bearer {token}"})

    # Then get its stats
    response = client.get(f"/links/{test_link['custom_alias']}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == test_link["original_url"]
    assert data["clicks"] == 0  # No clicks yet


def test_update_link(client, token):
    # First create a link
    client.post("/links/shorten", json=test_link, headers={"Authorization": f"Bearer {token}"})

    # Then update it
    updated_url = "https://www.example.com/updated/url"
    response = client.put(
        f"/links/{test_link['custom_alias']}",
        json={"original_url": updated_url},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == updated_url
    assert data["custom_alias"] == test_link["custom_alias"]


def test_delete_link(client, token):
    # First create a link
    client.post("/links/shorten", json=test_link, headers={"Authorization": f"Bearer {token}"})

    # Then delete it
    response = client.delete(
        f"/links/{test_link['custom_alias']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(f"/links/{test_link['custom_alias']}")
    assert response.status_code == 404


def test_search_links(client, token):
    # First create a link
    client.post("/links/shorten", json=test_link, headers={"Authorization": f"Bearer {token}"})

    # Then search for it
    response = client.get(f"/links/search?original_url={test_link['original_url']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["original_url"] == test_link["original_url"]
