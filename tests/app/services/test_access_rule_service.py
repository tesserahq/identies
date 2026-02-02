import pytest
from uuid import uuid4
from sqlalchemy.orm import Session
from app.models.access_rule import AccessRule
from app.schemas.access_rule import AccessRuleCreate, AccessRuleUpdate
from app.services.access_rule_service import AccessRuleService
from app.constants.access_rule_types import AccessRuleTypes


@pytest.fixture
def sample_access_rule_data():
    return {
        "kind": "ip_whitelist",
        "value": "192.168.1.1",
        "note": "Test IP whitelist rule",
    }


@pytest.fixture
def sample_access_rule(db: Session, sample_access_rule_data):
    access_rule = AccessRule(**sample_access_rule_data)
    db.add(access_rule)
    db.commit()
    db.refresh(access_rule)
    return access_rule


def test_create_access_rule(db: Session, sample_access_rule_data):
    """Test creating a new access rule."""
    # Create access rule
    access_rule_create = AccessRuleCreate(**sample_access_rule_data)
    access_rule = AccessRuleService(db).create_access_rule(access_rule_create)

    # Assertions
    assert access_rule.id is not None
    assert access_rule.kind == sample_access_rule_data["kind"]
    assert access_rule.value == sample_access_rule_data["value"]
    assert access_rule.note == sample_access_rule_data["note"]
    assert access_rule.created_at is not None
    assert access_rule.updated_at is not None


def test_get_access_rule(db: Session, sample_access_rule):
    """Test getting an access rule by ID."""
    # Get access rule
    retrieved_access_rule = AccessRuleService(db).get_access_rule(sample_access_rule.id)

    # Assertions
    assert retrieved_access_rule is not None
    assert retrieved_access_rule.id == sample_access_rule.id
    assert retrieved_access_rule.kind == sample_access_rule.kind
    assert retrieved_access_rule.value == sample_access_rule.value


def test_get_access_rule_by_kind_value(db: Session, sample_access_rule):
    """Test getting an access rule by kind and value combination."""
    # Get access rule by kind and value
    retrieved_access_rule = AccessRuleService(db).get_access_rule_by_kind_value(
        sample_access_rule.kind, sample_access_rule.value
    )

    # Assertions
    assert retrieved_access_rule is not None
    assert retrieved_access_rule.id == sample_access_rule.id
    assert retrieved_access_rule.kind == sample_access_rule.kind
    assert retrieved_access_rule.value == sample_access_rule.value


def test_get_access_rules(db: Session, sample_access_rule):
    """Test getting all access rules with pagination."""
    # Get all access rules
    access_rules = AccessRuleService(db).get_access_rules()

    # Assertions
    assert len(access_rules) >= 1
    assert any(ar.id == sample_access_rule.id for ar in access_rules)


def test_get_access_rules_with_pagination(db: Session, sample_access_rule):
    """Test getting access rules with pagination parameters."""
    # Create another access rule
    another_rule = AccessRule(
        kind="domain_restriction", value="example.com", note="Test domain restriction"
    )
    db.add(another_rule)
    db.commit()
    db.refresh(another_rule)

    # Get first page with limit 1
    access_rules = AccessRuleService(db).get_access_rules(skip=0, limit=1)

    # Assertions
    assert len(access_rules) == 1

    # Get second page
    access_rules = AccessRuleService(db).get_access_rules(skip=1, limit=1)

    # Assertions
    assert len(access_rules) == 1


def test_update_access_rule(db: Session, sample_access_rule):
    """Test updating an access rule."""
    # Update data
    update_data = {
        "kind": "domain_restriction",
        "value": "updated.example.com",
        "note": "Updated test rule",
    }
    access_rule_update = AccessRuleUpdate(**update_data)

    # Update access rule
    updated_access_rule = AccessRuleService(db).update_access_rule(
        sample_access_rule.id, access_rule_update
    )

    # Assertions
    assert updated_access_rule is not None
    assert updated_access_rule.id == sample_access_rule.id
    assert updated_access_rule.kind == update_data["kind"]
    assert updated_access_rule.value == update_data["value"]
    assert updated_access_rule.note == update_data["note"]


def test_update_access_rule_partial(db: Session, sample_access_rule):
    """Test partial update of an access rule."""
    # Update only note
    update_data = {"note": "Updated note only"}
    access_rule_update = AccessRuleUpdate(**update_data)

    # Update access rule
    updated_access_rule = AccessRuleService(db).update_access_rule(
        sample_access_rule.id, access_rule_update
    )

    # Assertions
    assert updated_access_rule is not None
    assert updated_access_rule.id == sample_access_rule.id
    assert updated_access_rule.kind == sample_access_rule.kind  # Unchanged
    assert updated_access_rule.value == sample_access_rule.value  # Unchanged
    assert updated_access_rule.note == update_data["note"]  # Updated


def test_delete_access_rule(db: Session, sample_access_rule):
    """Test deleting an access rule."""
    access_rule_service = AccessRuleService(db)

    # Delete access rule
    success = access_rule_service.delete_access_rule(sample_access_rule.id)

    # Assertions
    assert success is True
    deleted_access_rule = access_rule_service.get_access_rule(sample_access_rule.id)
    assert deleted_access_rule is None


def test_access_rule_not_found_cases(db: Session):
    """Test various not found cases."""
    access_rule_service = AccessRuleService(db)
    non_existent_id = uuid4()

    # Get non-existent access rule
    assert access_rule_service.get_access_rule(non_existent_id) is None

    # Get by non-existent kind/value combination
    assert (
        access_rule_service.get_access_rule_by_kind_value("nonexistent", "value")
        is None
    )

    # Update non-existent access rule
    update_data = {"note": "Updated note"}
    access_rule_update = AccessRuleUpdate(**update_data)
    assert (
        access_rule_service.update_access_rule(non_existent_id, access_rule_update)
        is None
    )

    # Delete non-existent access rule
    assert access_rule_service.delete_access_rule(non_existent_id) is False


def test_search_access_rules_with_filters(db: Session, sample_access_rule):
    """Test search method with dynamic filters."""
    # Search using ilike filter on kind
    filters = {"kind": {"operator": "ilike", "value": "%whitelist%"}}
    results = AccessRuleService(db).search(filters)

    assert isinstance(results, list)
    assert any(ar.id == sample_access_rule.id for ar in results)

    # Search using exact match
    filters = {"kind": sample_access_rule.kind}
    results = AccessRuleService(db).search(filters)

    assert len(results) >= 1
    assert any(ar.id == sample_access_rule.id for ar in results)

    # Search with no match
    filters = {"kind": {"operator": "==", "value": "nonexistent"}}
    results = AccessRuleService(db).search(filters)

    assert len(results) == 0


def test_search_access_rules_by_value(db: Session, sample_access_rule):
    """Test searching access rules by value."""
    # Search by exact value
    filters = {"value": sample_access_rule.value}
    results = AccessRuleService(db).search(filters)

    assert len(results) >= 1
    assert any(ar.id == sample_access_rule.id for ar in results)

    # Search by partial value using ilike
    partial_value = sample_access_rule.value.split(".")[0]  # Get first part of IP
    filters = {"value": {"operator": "ilike", "value": f"{partial_value}%"}}
    results = AccessRuleService(db).search(filters)

    assert len(results) >= 1
    assert any(ar.id == sample_access_rule.id for ar in results)


def test_search_access_rules_by_note(db: Session, sample_access_rule):
    """Test searching access rules by note."""
    # Search by note content
    filters = {"note": {"operator": "ilike", "value": "%test%"}}
    results = AccessRuleService(db).search(filters)

    assert len(results) >= 1
    assert any(ar.id == sample_access_rule.id for ar in results)


def test_create_access_rule_without_note(db: Session):
    """Test creating an access rule without optional note field."""
    access_rule_data = {
        "kind": "user_agent_block",
        "value": "malicious-bot",
    }

    access_rule_create = AccessRuleCreate(**access_rule_data)
    access_rule = AccessRuleService(db).create_access_rule(access_rule_create)

    # Assertions
    assert access_rule.id is not None
    assert access_rule.kind == access_rule_data["kind"]
    assert access_rule.value == access_rule_data["value"]
    assert access_rule.note is None


def test_unique_constraint_kind_value(db: Session, sample_access_rule):
    """Test that the unique constraint on kind+value combination works."""
    # Try to create another access rule with same kind and value
    duplicate_data = {
        "kind": sample_access_rule.kind,
        "value": sample_access_rule.value,
        "note": "Duplicate rule",
    }

    access_rule_create = AccessRuleCreate(**duplicate_data)

    # This should raise an IntegrityError due to unique constraint
    with pytest.raises(Exception):  # SQLAlchemy IntegrityError
        AccessRuleService(db).create_access_rule(access_rule_create)


# Email evaluation tests
def test_evaluate_email_access_exact_match(db: Session):
    """Test email evaluation with exact email match."""
    # Create an email access rule
    email_rule = AccessRule(
        kind=AccessRuleTypes.EMAIL, value="test@example.com", note="Test email rule"
    )
    db.add(email_rule)
    db.commit()

    service = AccessRuleService(db)

    # Test exact match
    assert service.evaluate_email_access("test@example.com") is True
    # Test case insensitive match
    assert service.evaluate_email_access("TEST@EXAMPLE.COM") is True
    # Test different email
    assert service.evaluate_email_access("other@example.com") is False


def test_evaluate_email_access_domain_match(db: Session):
    """Test email evaluation with domain match."""
    # Create a domain access rule
    domain_rule = AccessRule(
        kind=AccessRuleTypes.DOMAIN, value="datum.net", note="Test domain rule"
    )
    db.add(domain_rule)
    db.commit()

    service = AccessRuleService(db)

    # Test domain match
    assert service.evaluate_email_access("emi@datum.net") is True
    assert service.evaluate_email_access("user@datum.net") is True
    assert service.evaluate_email_access("admin@datum.net") is True
    # Test case insensitive match
    assert service.evaluate_email_access("EMI@DATUM.NET") is True
    # Test different domain
    assert service.evaluate_email_access("emi@example.com") is False


def test_evaluate_email_access_multiple_rules(db: Session):
    """Test email evaluation with multiple rules."""
    # Create both email and domain rules
    email_rule = AccessRule(
        kind=AccessRuleTypes.EMAIL,
        value="specific@example.com",
        note="Specific email rule",
    )
    domain_rule = AccessRule(
        kind=AccessRuleTypes.DOMAIN, value="allowed.com", note="Allowed domain rule"
    )
    db.add_all([email_rule, domain_rule])
    db.commit()

    service = AccessRuleService(db)

    # Test specific email match
    assert service.evaluate_email_access("specific@example.com") is True
    # Test domain match
    assert service.evaluate_email_access("any@allowed.com") is True
    # Test no match
    assert service.evaluate_email_access("other@example.com") is False
    assert service.evaluate_email_access("any@blocked.com") is False


def test_evaluate_email_access_invalid_emails(db: Session):
    """Test email evaluation with invalid email formats."""
    service = AccessRuleService(db)

    # Test invalid emails
    assert service.evaluate_email_access("") is False
    assert service.evaluate_email_access("invalid-email") is False
    assert service.evaluate_email_access("@example.com") is False
    assert service.evaluate_email_access("user@") is False


def test_evaluate_email_access_no_rules(db: Session):
    """Test email evaluation when no access rules exist."""
    service = AccessRuleService(db)

    # Should return False when no rules exist
    assert service.evaluate_email_access("test@example.com") is False


def test_evaluate_email_access_case_insensitive(db: Session):
    """Test that email evaluation is case insensitive."""
    # Create rules with different cases
    email_rule = AccessRule(
        kind=AccessRuleTypes.EMAIL,
        value="Test@Example.COM",
        note="Mixed case email rule",
    )
    domain_rule = AccessRule(
        kind=AccessRuleTypes.DOMAIN, value="DATUM.NET", note="Uppercase domain rule"
    )
    db.add_all([email_rule, domain_rule])
    db.commit()

    service = AccessRuleService(db)

    # Test case insensitive matching
    assert service.evaluate_email_access("test@example.com") is True
    assert service.evaluate_email_access("TEST@EXAMPLE.COM") is True
    assert service.evaluate_email_access("Test@Example.COM") is True

    assert service.evaluate_email_access("user@datum.net") is True
    assert service.evaluate_email_access("USER@DATUM.NET") is True
    assert service.evaluate_email_access("user@DATUM.net") is True


def test_evaluate_email_access_mixed_rule_types(db: Session):
    """Test email evaluation with mixed rule types including non-email rules."""
    # Create various rule types
    email_rule = AccessRule(
        kind=AccessRuleTypes.EMAIL, value="allowed@example.com", note="Email rule"
    )
    domain_rule = AccessRule(
        kind=AccessRuleTypes.DOMAIN, value="trusted.org", note="Domain rule"
    )
    # Add a non-email rule type (should be ignored)
    ip_rule = AccessRule(
        kind="ip_whitelist", value="192.168.1.1", note="IP rule (should be ignored)"
    )
    db.add_all([email_rule, domain_rule, ip_rule])
    db.commit()

    service = AccessRuleService(db)

    # Test email and domain rules work
    assert service.evaluate_email_access("allowed@example.com") is True
    assert service.evaluate_email_access("any@trusted.org") is True
    # Test that non-email rules are ignored
    assert service.evaluate_email_access("test@example.com") is False
    assert service.evaluate_email_access("any@other.org") is False
