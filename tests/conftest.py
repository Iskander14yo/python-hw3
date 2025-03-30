import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set testing environment variable
os.environ["TESTING"] = "True"
# Use SQLite in-memory database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# We need to patch the database connection before importing app
with patch('app.db.database.create_engine'):
    # Also patch the startup event to prevent it from running
    with patch('app.main.startup_event', MagicMock()):
        from app.main import app
        from app.db.database import Base, get_db
        from app.models.models import User, Link

# Create test database engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

# Create test session
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Patch the app's database engine with our test engine
with patch('app.db.database.engine', test_engine):
    # Create the tables in the test database
    Base.metadata.create_all(bind=test_engine)

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with a database session."""
    # Override the get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Mock init_db and cleanup_expired_links to prevent them from running
    with patch('app.db.init_db.init_db'), patch('app.services.link_service.cleanup_expired_links'):
        # Override the get_db dependency
        app.dependency_overrides[get_db] = override_get_db
        
        with TestClient(app) as test_client:
            yield test_client
        
        app.dependency_overrides.clear()

@pytest.fixture(scope="function", autouse=True)
def mock_redis():
    """Mock Redis connection for all tests."""
    redis_mock = MagicMock()
    # Mock common Redis methods
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = True
    
    with patch('app.db.redis.get_redis', return_value=redis_mock):
        yield redis_mock 