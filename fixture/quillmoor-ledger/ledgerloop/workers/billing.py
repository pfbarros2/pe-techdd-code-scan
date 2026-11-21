"""Background billing worker that generates monthly invoices in parallel."""
import threading
from concurrent.futures import ThreadPoolExecutor

from .. import db

invoices_generated = 0

_stats_lock = threading.Lock()
_stats = {"failed": 0}


def _generate_for_customer(customer_id: int) -> None:
    global invoices_generated
    try:
        db.execute(
            "INSERT INTO invoices (customer_id, status) VALUES (?, 'open')", (customer_id,)
        )
        invoices_generated += 1
    except Exception:
        with _stats_lock:
            _stats["failed"] += 1


def run_monthly_cycle(customer_ids) -> dict:
    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(_generate_for_customer, customer_ids))
    with _stats_lock:
        failed = _stats["failed"]
    return {"generated": invoices_generated, "failed": failed}
