import pytest
from app.models.access_rule import AccessRule


@pytest.fixture
def access_rule_id(setup_access_rule):
    return str(setup_access_rule.id)


@pytest.fixture(scope="function")
def test_access_rule(db, faker):
    """Create a test access rule for use in tests."""
    access_rule_data = {
        "kind": faker.random_element(
            elements=("ip_whitelist", "domain_restriction", "user_agent_block")
        ),
        "value": faker.ipv4() if faker.boolean() else faker.domain_name(),
        "note": faker.text(max_nb_chars=100),
    }

    access_rule = AccessRule(**access_rule_data)
    db.add(access_rule)
    db.commit()
    db.refresh(access_rule)

    return access_rule


@pytest.fixture(scope="function")
def setup_access_rule(db, faker):
    """Create a test access rule for use in tests."""
    access_rule_data = {
        "kind": faker.random_element(
            elements=("ip_whitelist", "domain_restriction", "user_agent_block")
        ),
        "value": faker.ipv4() if faker.boolean() else faker.domain_name(),
        "note": faker.text(max_nb_chars=100),
    }

    access_rule = AccessRule(**access_rule_data)
    db.add(access_rule)
    db.commit()
    db.refresh(access_rule)

    return access_rule


@pytest.fixture(scope="function")
def setup_another_access_rule(db, faker):
    """Create another test access rule for use in tests."""
    access_rule_data = {
        "kind": faker.random_element(
            elements=("ip_whitelist", "domain_restriction", "user_agent_block")
        ),
        "value": faker.ipv4() if faker.boolean() else faker.domain_name(),
        "note": faker.text(max_nb_chars=100),
    }

    access_rule = AccessRule(**access_rule_data)
    db.add(access_rule)
    db.commit()
    db.refresh(access_rule)

    return access_rule


@pytest.fixture(scope="function")
def setup_ip_whitelist_rule(db, faker):
    """Create a specific IP whitelist access rule for testing."""
    access_rule_data = {
        "kind": "ip_whitelist",
        "value": faker.ipv4(),
        "note": "Test IP whitelist rule",
    }

    access_rule = AccessRule(**access_rule_data)
    db.add(access_rule)
    db.commit()
    db.refresh(access_rule)

    return access_rule


@pytest.fixture(scope="function")
def setup_domain_restriction_rule(db, faker):
    """Create a specific domain restriction access rule for testing."""
    access_rule_data = {
        "kind": "domain_restriction",
        "value": faker.domain_name(),
        "note": "Test domain restriction rule",
    }

    access_rule = AccessRule(**access_rule_data)
    db.add(access_rule)
    db.commit()
    db.refresh(access_rule)

    return access_rule
