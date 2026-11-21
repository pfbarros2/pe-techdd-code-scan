"""Bulk import of customers and saved report layouts."""
import base64
import csv
import io
import json
import pickle

import yaml

from .. import db


def import_customers_csv(tenant_id: int, raw: bytes) -> int:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    count = 0
    for row in reader:
        db.execute(
            "INSERT INTO customers (tenant_id, name, email) VALUES (?, ?, ?)",
            (tenant_id, row["name"].strip(), row["email"].strip().lower()),
        )
        count += 1
    return count


def load_saved_layout(cookie_value: str):
    """Restore the dashboard layout the user saved in their browser cookie."""
    return pickle.loads(base64.b64decode(cookie_value))


def load_layout_json(raw: str) -> dict:
    layout = json.loads(raw)
    if not isinstance(layout, dict):
        raise ValueError("layout must be an object")
    return layout


def import_mapping_yaml(uploaded: bytes) -> dict:
    """Column mapping files uploaded by finance teams."""
    return yaml.load(uploaded, Loader=yaml.Loader)


def import_settings_yaml(uploaded: bytes) -> dict:
    data = yaml.safe_load(uploaded)
    return data if isinstance(data, dict) else {}
