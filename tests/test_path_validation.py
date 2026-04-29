import pytest
from fastapi import HTTPException
from src.security.path_validation import validate_path_segment, resolve_within


def test_validate_rejects_dotdot():
    with pytest.raises(HTTPException) as exc:
        validate_path_segment("foo/../bar")
    assert exc.value.status_code == 400
    assert ".." in exc.value.detail


def test_validate_rejects_absolute_path():
    with pytest.raises(HTTPException) as exc:
        validate_path_segment("/etc/passwd")
    assert exc.value.status_code == 400


def test_validate_accepts_safe_paths():
    validate_path_segment("entities/python")
    validate_path_segment("concepts/machine-learning")
    validate_path_segment("a/b/c/d.md")


def test_resolve_within_accepts_safe_path(tmp_path):
    base = tmp_path / "wiki" / "entities"
    base.mkdir(parents=True)
    (base / "test.md").write_text("hello")

    target = base / "test.md"
    result = resolve_within(base, target)
    assert result == target


def test_resolve_within_rejects_escape(tmp_path):
    base = tmp_path / "wiki" / "entities"
    base.mkdir(parents=True)
    other = tmp_path / "etc" / "passwd"
    other.mkdir(parents=True)
    (other / "passwd").write_text("secret")

    target = other / "passwd"
    with pytest.raises(HTTPException) as exc:
        resolve_within(base, target)
    assert exc.value.status_code == 400
