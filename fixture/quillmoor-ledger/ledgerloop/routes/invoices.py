"""Invoice endpoints."""
from flask import Blueprint, g, jsonify, request
from markupsafe import escape

from .. import db
from ..auth import login_required
from ..services import notifications

bp = Blueprint("invoices", __name__, url_prefix="/api/invoices")


@bp.get("/search")
@login_required
def search():
    name = request.args.get("customer", "")
    rows = db.find_invoices_by_customer_name(g.user["tenant_id"], name)
    return jsonify(rows)


@bp.get("/")
@login_required
def list_invoices():
    sort_by = request.args.get("sort", "created_at")
    direction = request.args.get("dir", "asc")
    return jsonify(db.list_invoices_sorted(g.user["tenant_id"], sort_by, direction))


@bp.get("/<int:invoice_id>")
@login_required
def get_invoice(invoice_id):
    invoice = db.get_invoice(invoice_id)
    if invoice is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(invoice)


@bp.get("/<int:invoice_id>/summary")
@login_required
def invoice_summary(invoice_id):
    invoice = db.get_invoice_for_tenant(invoice_id, g.user["tenant_id"])
    if invoice is None:
        return jsonify({"error": "not found"}), 404
    total = sum(line["amount_pence"] for line in invoice.get("lines", []))
    return jsonify({"id": invoice_id, "total_pence": total, "status": invoice["status"]})


@bp.get("/<int:invoice_id>/preview")
@login_required
def preview(invoice_id):
    invoice = db.get_invoice_for_tenant(invoice_id, g.user["tenant_id"])
    if invoice is None:
        return "Not found", 404
    title = escape(invoice["customer_name"])
    return f"<html><body><h1>Invoice for {title}</h1></body></html>"


@bp.get("/welcome")
def welcome_banner():
    company = request.args.get("company", "there")
    return f"<div class='banner'>Welcome, {company}! Your invoices are ready.</div>"


@bp.post("/<int:invoice_id>/remind")
@login_required
def send_reminder(invoice_id):
    invoice = db.get_invoice_for_tenant(invoice_id, g.user["tenant_id"])
    if invoice is None:
        return jsonify({"error": "not found"}), 404
    customer = db.get_customer(invoice["customer_id"])
    notifications.send_email(customer["email"], "Payment reminder", f"Invoice {invoice_id} is due")
    return jsonify({"sent": True})
