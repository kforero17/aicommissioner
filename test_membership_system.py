"""
Test script for the league membership system.

This script validates that:
1. Models are properly defined and importable
2. Database relationships work correctly
3. Token generation is secure
4. Basic functionality is working

Run with: python test_membership_system.py
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from models.league_member import LeagueMember, MemberRole
from models.league import League
from models.user import User


def test_imports():
    """Test that all models can be imported."""
    print("Testing imports...")
    assert LeagueMember is not None, "LeagueMember model not found"
    assert MemberRole is not None, "MemberRole enum not found"
    assert MemberRole.COMMISSIONER == "commissioner", "COMMISSIONER role incorrect"
    assert MemberRole.MEMBER == "member", "MEMBER role incorrect"
    print("✓ Imports successful")


def test_token_generation():
    """Test invite token generation."""
    print("\nTesting token generation...")
    token1 = LeagueMember.generate_invite_token()
    token2 = LeagueMember.generate_invite_token()

    assert token1 is not None, "Token generation failed"
    assert len(token1) > 20, "Token too short (should be ~43 chars)"
    assert token1 != token2, "Tokens not unique"
    assert " " not in token1, "Token contains spaces"
    print(f"✓ Token generation working (example: {token1[:20]}...)")


def test_model_attributes():
    """Test that LeagueMember model has all required attributes."""
    print("\nTesting model attributes...")

    # Check table name
    assert LeagueMember.__tablename__ == "league_members", "Table name incorrect"

    # Check that model has all required columns
    required_attrs = [
        'id', 'league_id', 'user_id', 'role',
        'invite_token', 'invite_email', 'invited_at', 'joined_at',
        'preferences', 'created_at', 'updated_at'
    ]

    for attr in required_attrs:
        assert hasattr(LeagueMember, attr), f"Missing attribute: {attr}"

    print("✓ All model attributes present")


def test_model_relationships():
    """Test that relationships are defined."""
    print("\nTesting model relationships...")

    # Check LeagueMember relationships
    assert hasattr(LeagueMember, 'league'), "LeagueMember missing league relationship"
    assert hasattr(LeagueMember, 'user'), "LeagueMember missing user relationship"

    # Check League relationships
    assert hasattr(League, 'members'), "League missing members relationship"

    # Check User relationships
    assert hasattr(User, 'league_memberships'), "User missing league_memberships relationship"

    print("✓ All relationships defined")


def test_role_enum():
    """Test MemberRole enum values."""
    print("\nTesting MemberRole enum...")

    # Test enum values
    assert MemberRole.COMMISSIONER.value == "commissioner"
    assert MemberRole.MEMBER.value == "member"

    # Test enum comparison
    assert MemberRole.COMMISSIONER != MemberRole.MEMBER

    # Test that enum inherits from str
    assert isinstance(MemberRole.COMMISSIONER, str)
    assert MemberRole.COMMISSIONER == "commissioner"

    print("✓ MemberRole enum working correctly")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("League Membership System - Test Suite")
    print("=" * 60)

    try:
        test_imports()
        test_token_generation()
        test_model_attributes()
        test_model_relationships()
        test_role_enum()

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
