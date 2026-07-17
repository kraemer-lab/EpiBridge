from unittest.mock import MagicMock, patch

import pytest

from app.services.resource_registration import (
    RegisterResult,
    register_from_manifest,
    register_resource,
    upsert_resource,
)

VALID_ENTRY = {
    "identifier": "test-resource",
    "name": "Test Resource",
    "alias": "test_resource",
    "provider": "csv",
    "endpoint": {"path": "data.csv"},
    "description": "A test resource",
    "version": "1.0.0",
    "status": "active",
}


@patch("app.services.resource_registration.registry")
def test_upsert_creates_new(mock_registry):
    mock_provider = MagicMock()
    mock_provider.validate_endpoint.return_value = {"path": "data.csv"}
    mock_registry.get.return_value = mock_provider

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    result = upsert_resource(db, VALID_ENTRY)

    assert result.identifier == "test-resource"
    assert result.name == "Test Resource"
    assert result.alias == "test_resource"
    assert result.provider_type == "csv"
    assert result.endpoint == {"path": "data.csv"}
    assert result.version == "1.0.0"
    assert result.status == "active"
    db.add.assert_called_once_with(result)
    db.commit.assert_not_called()


@patch("app.services.resource_registration.registry")
def test_upsert_updates_existing(mock_registry):
    mock_provider = MagicMock()
    mock_provider.validate_endpoint.return_value = {"path": "updated.csv"}
    mock_registry.get.return_value = mock_provider

    existing = MagicMock()
    existing.identifier = "test-resource"

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing

    updated_entry = VALID_ENTRY.copy()
    updated_entry["endpoint"] = {"path": "updated.csv"}
    updated_entry["name"] = "Updated Name"

    result = upsert_resource(db, updated_entry)

    assert result is existing
    assert result.name == "Updated Name"
    assert result.endpoint == {"path": "updated.csv"}
    db.add.assert_not_called()
    db.commit.assert_not_called()


@patch("app.services.resource_registration.registry")
def test_upsert_unknown_provider_raises(mock_registry):
    mock_registry.get.side_effect = ValueError("No provider registered for unknown")

    db = MagicMock()

    entry = VALID_ENTRY.copy()
    entry["provider"] = "unknown"

    with pytest.raises((ValueError, KeyError)):
        upsert_resource(db, entry)


@patch("app.services.resource_registration.registry")
def test_upsert_invalid_endpoint_raises(mock_registry):
    mock_provider = MagicMock()
    mock_provider.validate_endpoint.side_effect = ValueError("path must be non-empty")
    mock_registry.get.return_value = mock_provider

    db = MagicMock()

    entry = VALID_ENTRY.copy()
    entry["endpoint"] = {"path": ""}

    with pytest.raises(ValueError, match="path must be non-empty"):
        upsert_resource(db, entry)


# --- register_resource tests (create-if-not-exists semantics) ----------------

REGISTER_ENTRY = {
    "identifier": "new-resource",
    "name": "New Resource",
    "alias": "new_resource",
    "provider": "csv",
    "endpoint": {"path": "data.csv"},
    "description": "A new resource",
    "version": "1.0.0",
    "status": "active",
}


@patch("app.services.resource_registration.registry")
def test_register_creates_new(mock_registry):
    mock_provider = MagicMock()
    mock_provider.validate_endpoint.return_value = {"path": "data.csv"}
    mock_registry.get.return_value = mock_provider

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    result = register_resource(db, REGISTER_ENTRY)

    assert len(result.created) == 1
    assert len(result.skipped) == 0
    assert len(result.errors) == 0

    resource = result.created[0]
    assert resource.identifier == "new-resource"
    assert resource.name == "New Resource"
    assert resource.alias == "new_resource"
    assert resource.provider_type == "csv"
    assert resource.endpoint == {"path": "data.csv"}
    assert resource.version == "1.0.0"
    assert resource.status == "active"

    db.add.assert_called_once()
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(resource)


@patch("app.services.resource_registration.registry")
def test_register_skips_existing(mock_registry):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock()

    result = register_resource(db, REGISTER_ENTRY)

    assert len(result.created) == 0
    assert len(result.skipped) == 1
    assert result.skipped[0] == "new-resource"
    assert len(result.errors) == 0

    db.add.assert_not_called()
    db.flush.assert_not_called()
    mock_registry.get.assert_not_called()


@patch("app.services.resource_registration.registry")
def test_register_unknown_provider_accumulates_error(mock_registry):
    mock_registry.get.side_effect = ValueError("No provider registered for unknown")

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    entry = REGISTER_ENTRY.copy()
    entry["provider"] = "unknown"

    result = register_resource(db, entry)

    assert len(result.created) == 0
    assert len(result.skipped) == 0
    assert len(result.errors) == 1
    assert "new-resource" in result.errors[0]
    assert "not a valid ProviderType" in result.errors[0]

    db.add.assert_not_called()


@patch("app.services.resource_registration.registry")
def test_register_invalid_endpoint_accumulates_error(mock_registry):
    mock_provider = MagicMock()
    mock_provider.validate_endpoint.side_effect = ValueError("path must be non-empty")
    mock_registry.get.return_value = mock_provider

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    entry = REGISTER_ENTRY.copy()
    entry["endpoint"] = {"path": ""}

    result = register_resource(db, entry)

    assert len(result.created) == 0
    assert len(result.skipped) == 0
    assert len(result.errors) == 1
    assert "new-resource" in result.errors[0]
    assert "path must be non-empty" in result.errors[0]

    db.add.assert_not_called()


# --- register_from_manifest tests --------------------------------------------


@patch("app.services.resource_registration.register_resource")
def test_register_from_manifest_mixed(mock_register):
    def side_effect(db, entry):
        ident = entry["identifier"]
        if ident == "new-a":
            r = MagicMock()
            r.identifier = "new-a"
            r.name = "Resource A"
            return RegisterResult(created=[r], skipped=[], errors=[])
        elif ident == "new-b":
            r = MagicMock()
            r.identifier = "new-b"
            r.name = "Resource B"
            return RegisterResult(created=[r], skipped=[], errors=[])
        elif ident == "existing-a":
            return RegisterResult(created=[], skipped=["existing-a"], errors=[])
        return RegisterResult(created=[], skipped=[], errors=["unknown: error"])

    mock_register.side_effect = side_effect

    db = MagicMock()
    entries = [
        {"identifier": "new-a"},
        {"identifier": "existing-a"},
        {"identifier": "new-b"},
    ]

    result = register_from_manifest(db, entries)

    assert len(result.created) == 2
    assert len(result.skipped) == 1
    assert result.skipped[0] == "existing-a"
    assert len(result.errors) == 0
    assert mock_register.call_count == 3
    db.commit.assert_called_once()


@patch("app.services.resource_registration.register_resource")
def test_register_from_manifest_empty(mock_register):
    db = MagicMock()

    result = register_from_manifest(db, [])

    assert len(result.created) == 0
    assert len(result.skipped) == 0
    assert len(result.errors) == 0
    mock_register.assert_not_called()
    db.commit.assert_not_called()
