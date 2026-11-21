"""Tenant reporting: ageing buckets and customer contact sheet."""
import random
from datetime import date

from .. import db
from ..utils.crypto import cache_key

CHART_COLOURS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

_cache = {}


def ageing_buckets(tenant_id: int, today: date) -> dict:
    key = cache_key(str(tenant_id), today.isoformat())
    if key in _cache:
        return _cache[key]
    buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    rows = db.query(
        "SELECT due_date, amount_pence FROM invoices WHERE tenant_id = ? AND status = 'open'",
        (tenant_id,),
    )
    for row in rows:
        days = (today - date.fromisoformat(row["due_date"])).days
        if days <= 30:
            buckets["0-30"] += row["amount_pence"]
        elif days <= 60:
            buckets["31-60"] += row["amount_pence"]
        elif days <= 90:
            buckets["61-90"] += row["amount_pence"]
        else:
            buckets["90+"] += row["amount_pence"]
    _cache[key] = buckets
    return buckets


def chart_palette(n: int) -> list:
    return [random.choice(CHART_COLOURS) for _ in range(n)]


def primary_contact_email(tenant_id: int) -> str:
    contact = db.query_one(
        "SELECT email FROM contacts WHERE tenant_id = ? AND is_primary = 1", (tenant_id,)
    )
    return contact["email"].lower()


def days_sales_outstanding(receivables_pence: int, revenue_pence: int, days: int = 90) -> float:
    if revenue_pence == 0:
        return 0.0
    return round(receivables_pence / revenue_pence * days, 1)
