import os
import pytest
import json
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.encoders import jsonable_encoder
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

# Set testing environment variable
os.environ["TESTING"] = "True"
# Use SQLite in-memory database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# Password utilities
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Import modules from app
with patch('app.services.link_service.datetime') as mock_datetime:
    # Mock datetime to ensure timezone consistency
    mock_datetime.now.return_value = datetime(2023, 1, 1, tzinfo=timezone.utc)
    mock_datetime.timezone = timezone
    
    from app.db.database import Base, get_db
    from app.models.models import User, Link
    from app.core.auth import create_access_token
    from app.api import auth, links, admin

# Create test engine with check_same_thread=False for SQLite
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Create test session factory
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create all tables in the test database
Base.metadata.create_all(bind=test_engine)

class CustomTestClient(TestClient):
    """Custom test client that handles datetime serialization."""
    def request(self, method, url, **kwargs):
        if 'json' in kwargs:
            kwargs['json'] = jsonable_encoder(kwargs['json'])
        return super().request(method, url, **kwargs)

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Connect and begin a transaction
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    
    yield session
    
    # Close the session and rollback the transaction
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function", autouse=True)
def mock_datetime_now():
    """Mock datetime.now to return a consistent timezone-aware datetime."""
    with patch('app.services.link_service.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2023, 1, 1)
        # mock_dt.timezone = timezone
        yield mock_dt

@pytest.fixture(scope="function", autouse=True)
def mock_redis():
    """Mock Redis connection for all tests."""
    redis_mock = MagicMock()
    # Mock Redis get to return None by default
    redis_mock.get.return_value = None
    # Mock Redis set to return True
    redis_mock.set.return_value = True
    # Mock Redis delete to return True
    redis_mock.delete.return_value = True
    # Mock Redis exists to return False
    redis_mock.exists.return_value = False
    # Mock Redis incr to return 1
    redis_mock.incr.return_value = 1
    
    # Create a patch for all Redis calls
    with patch('app.db.redis.get_redis', return_value=redis_mock), \
         patch('app.services.link_service.get_redis', return_value=redis_mock), \
         patch('app.services.admin_service.get_redis', return_value=redis_mock):
        yield redis_mock

@pytest.fixture(scope="function")
def test_app(db_session):
    """Create a test FastAPI app."""
    # Create a new FastAPI app specifically for testing
    app = FastAPI()
    
    # Include the routers
    app.include_router(auth.router)
    app.include_router(links.router)
    app.include_router(admin.router)
    
    # Override the get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db
    
    return app

@pytest.fixture(scope="function")
def client(test_app):
    """Create a test client."""
    return CustomTestClient(test_app)

@pytest.fixture
def test_user_password():
    """Test user password."""
    return "testpassword123"

@pytest.fixture
def test_user(db_session, test_user_password):
    """Create a regular test user."""
    user = User(
        username="testuser",
        email="testuser@example.com",
        hashed_password=pwd_context.hash(test_user_password),
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def admin_user(db_session, test_user_password):
    """Create an admin test user."""
    admin = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password=pwd_context.hash(test_user_password),
        is_active=True,
        is_admin=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin

@pytest.fixture
def user_token(test_user):
    """Create a token for regular user."""
    access_token = create_access_token(data={"sub": test_user.username})
    return access_token

@pytest.fixture
def admin_token(admin_user):
    """Create a token for admin user."""
    access_token = create_access_token(data={"sub": admin_user.username})
    return access_token

@pytest.fixture
def user_headers(user_token):
    """Headers with regular user token."""
    return {"Authorization": f"Bearer {user_token}"}

@pytest.fixture
def admin_headers(admin_token):
    """Headers with admin token."""
    return {"Authorization": f"Bearer {admin_token}"}

@pytest.fixture
def test_link(db_session, test_user):
    """Create a test link."""
    now = datetime.now(timezone.utc)
    link = Link(
        short_code="test123",
        original_url="https://example.com",
        clicks=0,
        is_active=True,
        user_id=test_user.id,
        created_at=now,
        expires_at=now + timedelta(days=7)
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)
    return link 