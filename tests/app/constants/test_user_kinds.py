from app.constants.user_kinds import UserKind


def test_user_kind_values():
    assert UserKind.values() == ["human", "agent", "service_account"]


def test_user_kind_is_a_string():
    assert UserKind.AGENT == "agent"
