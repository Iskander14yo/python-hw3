import pytest
from app.services.link_service import generate_short_code


def test_generate_short_code():
    """Test that short code generation produces unique codes of the right length."""
    # Test default length
    code1 = generate_short_code()
    assert len(code1) == 6
    
    # Test custom length
    code2 = generate_short_code(length=8)
    assert len(code2) == 8
    
    # Test uniqueness
    code3 = generate_short_code()
    assert code1 != code3
    
    # Test character set
    allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    for char in code1:
        assert char in allowed_chars
    
    # Test multiple generations
    codes = set()
    for _ in range(100):
        code = generate_short_code()
        # Ensure no duplicates in 100 generations
        assert code not in codes
        codes.add(code) 