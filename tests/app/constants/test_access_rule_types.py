"""Tests for AccessRuleTypes constants."""

from app.constants.access_rule_types import AccessRuleTypes


class TestAccessRuleTypes:
    """Test cases for AccessRuleTypes constants."""

    def test_email_constant(self):
        """Test that EMAIL constant is defined correctly."""
        assert AccessRuleTypes.EMAIL == "email"

    def test_domain_constant(self):
        """Test that DOMAIN constant is defined correctly."""
        assert AccessRuleTypes.DOMAIN == "domain"

    def test_get_all_types(self):
        """Test that get_all_types returns all valid types."""
        types = AccessRuleTypes.get_all_types()
        assert isinstance(types, list)
        assert len(types) == 2
        assert "email" in types
        assert "domain" in types

    def test_is_valid_type_with_valid_types(self):
        """Test is_valid_type with valid types."""
        assert AccessRuleTypes.is_valid_type("email") is True
        assert AccessRuleTypes.is_valid_type("domain") is True

    def test_is_valid_type_with_invalid_types(self):
        """Test is_valid_type with invalid types."""
        assert AccessRuleTypes.is_valid_type("invalid") is False
        assert AccessRuleTypes.is_valid_type("ip_whitelist") is False
        assert AccessRuleTypes.is_valid_type("") is False
        assert AccessRuleTypes.is_valid_type(None) is False

    def test_get_valid_types_message(self):
        """Test that get_valid_types_message returns proper message."""
        message = AccessRuleTypes.get_valid_types_message()
        assert isinstance(message, str)
        assert "email" in message
        assert "domain" in message
        assert "Valid access rule types are:" in message
