import pytest

from app.utils.security import (
    generate_agent_claim_code,
    hash_secret,
    parse_agent_claim_code,
    secrets_match,
)


def test_generated_codes_round_trip():
    code, claim_id, secret = generate_agent_claim_code()

    assert code == f"ac_{claim_id}.{secret}"
    assert parse_agent_claim_code(code) == (claim_id, secret)


def test_generated_codes_are_unique_and_high_entropy():
    codes = {generate_agent_claim_code()[0] for _ in range(50)}

    assert len(codes) == 50
    assert all(len(c.split(".")[1]) >= 32 for c in codes)


@pytest.mark.parametrize(
    "bad", ["", "x", "ac_", "ac_a", "ac_a.b.c", "ac_.b", "ac_a.", "ak_a.b"]
)
def test_parse_rejects_malformed_codes(bad):
    with pytest.raises(ValueError):
        parse_agent_claim_code(bad)


def test_secrets_match_compares_against_the_hash():
    assert secrets_match("secret", hash_secret("secret")) is True
    assert secrets_match("other", hash_secret("secret")) is False
