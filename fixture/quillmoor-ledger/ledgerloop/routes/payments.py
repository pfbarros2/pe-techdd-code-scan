"""Payment and refund endpoints."""
from flask import Blueprint, g, jsonify, request

from .. import db
from ..auth import admin_required, login_required
from ..services import payments as payment_service

bp = Blueprint("payments", __name__, url_prefix="/api/payments")


@bp.get("/")
@login_required
def list_payments():
    order = request.args.get("order", "created_at DESC")
    return jsonify(db.list_payments_ordered(g.user["tenant_id"], order))


@bp.post("/refund")
@admin_required
def refund():
    body = request.get_json(force=True)
    invoice_id = int(body["invoice_id"])
    amount_pence = int(body["amount_pence"])
    result = payment_service.issue_refund(invoice_id, amount_pence)
    return jsonify(result)


@bp.post("/transfer")
@login_required
def transfer():
    body = request.get_json(force=True)
    amount = int(body.get("amount_pence", 0))
    if amount <= 0 or amount > 10_000_000:
        return jsonify({"error": "invalid amount"}), 400
    ok = payment_service.withdraw(int(body["account_id"]), amount)
    return jsonify({"ok": ok})


@bp.post("/charge")
@login_required
def charge():
    body = request.get_json(force=True)
    card = body.get("card_number", "")
    payment_service.log_charge_attempt(g.user["id"], card, body.get("amount_pence"))
    return jsonify(payment_service.charge_card(card, int(body.get("amount_pence", 0))))
