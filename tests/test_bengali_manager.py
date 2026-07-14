import json

import pytest

from src.data import bengali_manager


@pytest.fixture
def data_file(tmp_path, monkeypatch):
    path = tmp_path / "bengali_data.json"
    monkeypatch.setattr(bengali_manager, "BENGALI_DATA_FILE", str(path))
    return path


def test_missing_file_starts_with_empty_collections(data_file):
    manager = bengali_manager.BengaliDataManager()

    assert manager.data == {"suppliers": [], "employers": [], "workers": []}
    assert not data_file.exists()


def test_load_repairs_invalid_entries_and_missing_ids(data_file):
    data_file.write_text(
        json.dumps(
            {
                "workers": [{"name": "Worker"}, "invalid"],
                "suppliers": [{"name": "Supplier"}],
                "employers": None,
            }
        ),
        encoding="utf-8",
    )

    manager = bengali_manager.BengaliDataManager()

    assert len(manager.data["workers"]) == 1
    assert len(manager.data["workers"][0]["worker_uuid"]) == 12
    assert len(manager.data["suppliers"][0]["id"]) == 12
    assert manager.data["employers"] == []
    assert json.loads(data_file.read_text(encoding="utf-8")) == manager.data


def test_supplier_and_employer_crud(data_file):
    manager = bengali_manager.BengaliDataManager()

    assert manager.add_supplier("invalid") is False
    assert manager.add_supplier({"name": "Supplier", "phone": "123"}) is True
    assert manager.add_supplier({"name": "Supplier", "phone": "456"}) is True
    assert len(manager.get_suppliers()) == 1
    supplier_id = manager.get_suppliers()[0]["id"]
    assert manager.update_supplier(supplier_id, {"name": "Updated"}) is True
    assert manager.update_supplier("missing", {}) is False
    assert manager.delete_supplier(supplier_id) is True
    assert manager.delete_supplier(supplier_id) is False

    assert manager.add_employer({"name": "Employer", "city": "Riyadh"}) is True
    employer_id = manager.get_employers()[0]["id"]
    assert manager.update_employer(employer_id, {"name": "Updated"}) is True
    assert manager.update_employer("missing", {}) is False
    assert manager.delete_employer(employer_id) is True
    assert manager.delete_employer(employer_id) is False


def test_worker_crud_preserves_identity_and_timestamp(data_file):
    manager = bengali_manager.BengaliDataManager()
    worker = {"name": "Worker", "timestamp": "2026-07-14"}

    assert manager.add_worker(worker) is True
    worker_id = worker["worker_uuid"]
    assert len(worker_id) == 12
    assert manager.update_worker(worker_id, {"name": "Updated"}) is True
    assert manager.get_workers()[0] == {
        "name": "Updated",
        "worker_uuid": worker_id,
        "timestamp": "2026-07-14",
    }
    assert manager.update_worker("missing", {}) is False
    assert manager.delete_worker(worker_id) is True
    assert manager.delete_worker(worker_id) is False


def test_return_worker_decrements_batches_and_removes_individuals(data_file):
    manager = bengali_manager.BengaliDataManager()
    manager.data["workers"] = [
        {"worker_uuid": "batch", "headcount": 3},
        {"worker_uuid": "single"},
        {"worker_uuid": "invalid-count", "headcount": "unknown"},
    ]

    assert manager.return_worker("batch") is True
    assert manager.get_workers()[0]["headcount"] == 2
    assert manager.return_worker("batch", amount=2) is True
    assert manager.return_worker("single") is True
    assert manager.return_worker("invalid-count") is True
    assert manager.return_worker("missing") is False
    assert manager.get_workers() == []
