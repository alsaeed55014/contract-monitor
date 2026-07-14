import json

import pytest

from src.core.auth import AuthManager


@pytest.fixture
def manager(tmp_path):
    return AuthManager(tmp_path / "users.json")


def test_creates_and_persists_default_admin(tmp_path):
    users_file = tmp_path / "users.json"

    manager = AuthManager(users_file)

    assert manager.authenticate(" ADMIN ", "admin123")["role"] == "admin"
    persisted = json.loads(users_file.read_text(encoding="utf-8"))
    assert persisted["users"]["admin"]["permissions"] == ["all"]


def test_add_authenticate_and_reject_duplicate_user(manager):
    added, message = manager.add_user(
        " Alice ",
        "secret",
        role="viewer",
        name_ar="أليس",
        name_en="Alice",
    )

    assert (added, message) == (True, "User added successfully")
    assert manager.authenticate("ALICE", "secret")["permissions"] == ["read"]
    assert manager.authenticate("alice", "wrong") is None
    assert manager.add_user("alice", "other") == (False, "User already exists")


def test_update_password_and_role(manager):
    manager.add_user("editor", "old-password")

    assert manager.update_password(" EDITOR ", "new-password") is True
    assert manager.authenticate("editor", "old-password") is None
    assert manager.authenticate("editor", "new-password") is not None
    assert manager.update_role("editor", "admin") is True
    assert manager.users["editor"]["permissions"] == ["all"]
    assert manager.update_role("missing", "admin") is False


def test_delete_user_but_protect_admin(manager):
    manager.add_user("viewer", "password")

    assert manager.delete_user(" VIEWER ") is True
    assert manager.delete_user("viewer") is False
    assert manager.delete_user("admin") is False


def test_invalid_json_recovers_with_default_admin(tmp_path, capsys):
    users_file = tmp_path / "users.json"
    users_file.write_text("{invalid", encoding="utf-8")

    manager = AuthManager(users_file)

    assert "Error loading users:" in capsys.readouterr().out
    assert manager.authenticate("admin", "admin123") is not None
