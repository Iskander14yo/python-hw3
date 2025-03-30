import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from app.db.init_db import init_db
from app.models.models import User
from app.services.user_service import create_user
from app.models.schemas import UserCreate


def test_init_db():
    """Test database initialization function."""
    # Mock db session
    mock_db = MagicMock(spec=Session)
    
    # Mock admin user creation
    with patch('app.db.init_db.create_user') as mock_create_user:
        # Mock environment variables
        env_vars = {
            "ADMIN_USERNAME": "admin",
            "ADMIN_EMAIL": "admin@example.com",
            "ADMIN_PASSWORD": "adminpassword"
        }
        
        with patch.dict('os.environ', env_vars):
            # Mock db query for checking if admin exists
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            # Call init_db
            init_db(mock_db)
            
            # Assertions
            mock_create_user.assert_called_once()
            # Verify the arguments provided to create_user
            call_args = mock_create_user.call_args
            assert call_args[0][0] == mock_db  # First arg is db
            assert isinstance(call_args[0][1], UserCreate)
            assert call_args[0][1].username == "admin"
            assert call_args[0][1].email == "admin@example.com"
            assert call_args[0][1].password == "adminpassword"
            assert call_args[1]["is_admin"] is True


def test_init_db_admin_exists():
    """Test initialization when admin already exists."""
    # Mock db session
    mock_db = MagicMock(spec=Session)
    
    # Mock environment variables
    env_vars = {
        "ADMIN_USERNAME": "admin",
        "ADMIN_EMAIL": "admin@example.com",
        "ADMIN_PASSWORD": "adminpassword"
    }
    
    # Mock existing admin user
    existing_admin = User(
        id=1,
        username="admin",
        email="admin@example.com",
        is_admin=True
    )
    
    with patch.dict('os.environ', env_vars):
        # Mock db query to return existing admin
        mock_db.query.return_value.filter.return_value.first.return_value = existing_admin
        
        # Mock create_user to ensure it's not called
        with patch('app.db.init_db.create_user') as mock_create_user:
            # Call init_db
            init_db(mock_db)
            
            # Assert create_user was not called
            mock_create_user.assert_not_called()


def test_init_db_missing_env_vars():
    """Test database initialization with missing environment variables."""
    # Mock db session
    mock_db = MagicMock(spec=Session)
    
    # Mock environment variables with missing values
    env_vars = {
        # Missing ADMIN_USERNAME
        "ADMIN_EMAIL": "admin@example.com",
        "ADMIN_PASSWORD": "adminpassword"
    }
    
    with patch.dict('os.environ', env_vars, clear=True):
        # Mock print function to avoid actual output
        with patch('builtins.print') as mock_print:
            # Call init_db
            init_db(mock_db)
            
            # Assert that no user creation was attempted
            mock_db.query.assert_not_called()
            
            # Further verification can be made by checking mock_print calls
            # but that's optional depending on implementation 