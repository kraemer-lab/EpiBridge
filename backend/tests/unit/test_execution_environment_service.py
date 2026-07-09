from unittest.mock import MagicMock

import pytest

from app.services.execution_environment_service import (
    upsert_environment,
    validate_environment_entry,
)

VALID_ENTRY = {
    "identifier": "python-3.13-scientific",
    "name": "Python 3.13 Scientific",
    "runtime": "python-3.13",
    "description": "NumPy, SciPy, Pandas",
    "status": "active",
    "image_reference": "epibridge/python-3.13-scientific:latest",
}


class TestValidateEnvironmentEntry:
    def test_valid_entry(self):
        result = validate_environment_entry(VALID_ENTRY)
        assert result["identifier"] == "python-3.13-scientific"

    def test_missing_required_field(self):
        data = VALID_ENTRY.copy()
        del data["runtime"]
        with pytest.raises(ValueError, match="runtime"):
            validate_environment_entry(data)

    def test_missing_multiple_fields(self):
        data = {"identifier": "foo"}
        with pytest.raises(ValueError, match="name, runtime"):
            validate_environment_entry(data)

    def test_empty_identifier(self):
        data = VALID_ENTRY.copy()
        data["identifier"] = ""
        with pytest.raises(ValueError, match="identifier"):
            validate_environment_entry(data)


def test_upsert_creates_new():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    result = upsert_environment(db, VALID_ENTRY)

    assert result.identifier == "python-3.13-scientific"
    assert result.name == "Python 3.13 Scientific"
    assert result.runtime == "python-3.13"
    assert result.description == "NumPy, SciPy, Pandas"
    assert result.status == "active"
    assert result.image_reference == "epibridge/python-3.13-scientific:latest"
    assert result.definition_path is None
    db.add.assert_called_once_with(result)


def test_upsert_creates_new_with_definition_path():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    entry = VALID_ENTRY.copy()
    entry["definition_path"] = "python-3.13-scientific"

    result = upsert_environment(db, entry)

    assert result.definition_path == "python-3.13-scientific"
    db.add.assert_called_once_with(result)


def test_upsert_updates_existing():
    existing = MagicMock()
    existing.identifier = "python-3.13-scientific"

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing

    updated_entry = VALID_ENTRY.copy()
    updated_entry["name"] = "Updated Name"

    result = upsert_environment(db, updated_entry)

    assert result is existing
    assert result.name == "Updated Name"
    assert result.definition_path is None
    db.add.assert_not_called()


def test_upsert_updates_definition_path():
    existing = MagicMock()
    existing.identifier = "python-3.13-scientific"

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing

    updated_entry = VALID_ENTRY.copy()
    updated_entry["definition_path"] = "python-3.13-scientific"

    result = upsert_environment(db, updated_entry)

    assert result.definition_path == "python-3.13-scientific"
    db.add.assert_not_called()
