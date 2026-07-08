
import datetime as dt

import jwt
import pytest
from fastapi import HTTPException

from auth import security


def test_password_hash_roundtrip():
    h = security.hash_password("s3cret-pw")
    assert h != "s3cret-pw"
    assert security.verify_password("s3cret-pw", h) is True
    assert security.verify_password("wrong-pw", h) is False


def test_password_hash_is_salted():
    a = security.hash_password("same")
    b = security.hash_password("same")
    assert a != b
    assert security.verify_password("same", a)
    assert security.verify_password("same", b)


def test_verify_password_handles_garbage_hash():
    assert security.verify_password("anything", "not-a-real-bcrypt-hash") is False


def test_token_roundtrip():
    tok = security.create_access_token(user_id="u1", email="a@b.com", org_id="org1", role="admin")
    payload = security.decode_token(tok)
    assert payload["sub"] == "u1"
    assert payload["email"] == "a@b.com"
    assert payload["org_id"] == "org1"
    assert payload["role"] == "admin"


def test_tampered_token_rejected():
    tok = security.create_access_token(user_id="u1", email="a@b.com", org_id="org1", role="admin")
    tampered = tok[:-3] + ("aaa" if tok[-3:] != "aaa" else "bbb")
    with pytest.raises(jwt.PyJWTError):
        security.decode_token(tampered)


def test_token_signed_with_other_secret_rejected():
    tok = security.create_access_token(user_id="u1", email="a@b.com", org_id="org1", role="admin")
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(tok, "a-different-secret", algorithms=["HS256"])


def test_expired_token_rejected():
    now = dt.datetime.now(dt.timezone.utc)
    expired = jwt.encode(
        {"sub": "u1", "email": "a@b.com", "org_id": "org1", "role": "admin",
         "iat": now - dt.timedelta(hours=2), "exp": now - dt.timedelta(hours=1)},
        security._secret(), algorithm="HS256",
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_token(expired)


def test_require_role_allows_permitted_role():
    checker = security.require_role("admin", "manager")
    ctx = {"user_id": "u", "email": "a@b.com", "org_id": "o", "role": "admin"}
    assert checker(current=ctx) == ctx


def test_require_role_blocks_forbidden_role():
    checker = security.require_role("admin", "manager")
    ctx = {"user_id": "u", "email": "a@b.com", "org_id": "o", "role": "agent"}
    with pytest.raises(HTTPException) as exc:
        checker(current=ctx)
    assert exc.value.status_code == 403
