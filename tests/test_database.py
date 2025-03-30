import pytest
from unittest.mock import patch, MagicMock
from app.db.database import get_db


def test_get_db():
    """Test the database session generator."""
    # Create a mock session
    mock_session = MagicMock()
    mock_session_local = MagicMock()
    mock_session_local.return_value = mock_session
    
    # Patch the SessionLocal factory
    with patch('app.db.database.SessionLocal', mock_session_local):
        # Get a DB session from the generator
        db_gen = get_db()
        db = next(db_gen)
        
        # Verify the correct session was returned
        assert db == mock_session
        
        # Try to exhaust the generator to trigger the finally block
        try:
            next(db_gen)
        except StopIteration:
            pass
        
        # Verify session was closed
        mock_session.close.assert_called_once() 