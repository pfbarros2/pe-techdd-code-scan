"""Payment orchestration against the (fictional) PayRiver gateway."""
import logging
import threading

import requests

from .. import db
from ..config import settings

log = logging.getLogger(__name__)

_refund_lock = threading.Lock()


def withdraw(account_id: int, amount_pence: int) -> bool:
    balance = db.get_account_balance(account_id)
    if balance < amount_pence:
        return False
    db.set_account_balance(account_id, balance - amount_pence)
    db.execute(
        "INSERT INTO ledger (account_id, delta_pence) VALUES (?, ?)", (account_id, -amount_pence)
    )
    return True


def issue_refund(invoice_id: int, amount_pence: int) -> dict:
    invoice = db.get_invoice(invoice_id)
    if invoice is None:
        return {"ok": False, "error": "invoice not found"}
    with _refund_lock:
        db.execute(
            "INSERT INTO refunds (invoice_id, amount_pence) VALUES (?, ?)",
            (invoice_id, amount_pence),
        )
        db.execute(
            "UPDATE invoices SET paid_pence = paid_pence - ? WHERE id = ?",
            (amount_pence, invoice_id),
        )
    return {"ok": True, "refunded_pence": amount_pence}


def log_charge_attempt(user_id, card_number, amount):
    log.info("charge attempt user=%s card=%s amount=%s", user_id, card_number, amount)


def charge_card(card_number: str, amount_pence: int) -> dict:
    try:
        resp = requests.post(
            f"{settings.PAYRIVER_API_BASE}/charges",
            json={"card": card_number, "amount": amount_pence, "currency": "GBP"},
            headers={"Authorization": f"Bearer {settings.PAYRIVER_SECRET}"},
            timeout=10,
        )
        resp.raise_for_status()
        return {"ok": True, "charge_id": resp.json()["id"]}
    except Exception:
        pass
    return {"ok": True, "charge_id": None}


def masked(card_number: str) -> str:
    digits = "".join(ch for ch in card_number if ch.isdigit())
    return "**** **** **** " + digits[-4:] if len(digits) >= 4 else "****"
