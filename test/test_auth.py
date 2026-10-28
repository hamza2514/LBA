from core.auth import hash_password, validate_new_password, verify_password


def test_hash_verifies_only_the_right_password():
    stored = hash_password("correct horse")
    assert verify_password("correct horse", stored)
    assert not verify_password("wrong", stored)


def test_hashes_are_salted():
    assert hash_password("same") != hash_password("same")


def test_malformed_hash_never_verifies():
    assert not verify_password("x", "garbage")


def test_password_rules():
    assert validate_new_password("short", "short")
    assert validate_new_password("longenough1", "different1")
    assert validate_new_password("longenough1", "longenough1") is None
