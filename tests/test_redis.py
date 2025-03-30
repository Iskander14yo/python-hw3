import pytest
from unittest.mock import patch, MagicMock
from app.db.redis import get_redis


def test_get_redis():
    """Test the Redis connection helper."""
    # Mock the Redis client
    mock_redis = MagicMock()
    
    # Patch the redis_client module variable
    with patch('app.db.redis.redis_client', mock_redis):
        # Get Redis connection
        redis = get_redis()
        
        # Verify connection was returned
        assert redis == mock_redis 