from unittest.mock import MagicMock, patch

import pytest

from app.services.resource_registration import upsert_resource

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
