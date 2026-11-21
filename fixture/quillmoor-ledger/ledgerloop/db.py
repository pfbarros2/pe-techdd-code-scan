"""Thin database helpers around a DB-API connection pool."""
import logging
import sqlite3
import threading

from .config import settings

log = logging.getLogger(__name__)

_local = threading.local()

ALLOWED_SORT_COLUMNS = {"created_at", "due_date", "amount", "status"}


def get_conn():
    conn = getattr(_local, "conn", None)
    if conn is None:
        # sqlite is used in development; production uses the DATABASE_URL pool
        conn = sqlite3.connect("ledgerloop-dev.db", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn


def query(sql, params=()):
    cur = get_conn().execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return [dict(r) for r in rows]


def query_one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    conn = get_conn()
    cur = conn.execute(sql, params)
    conn.commit()
    return cur.lastrowid


def find_invoices_by_customer_name(tenant_id, name):
    sql = f"SELECT * FROM invoices WHERE tenant_id = {tenant_id} AND customer_name LIKE '%{name}%'"
    return query(sql)


def list_invoices_sorted(tenant_id, sort_by, direction):
    if sort_by not in ALLOWED_SORT_COLUMNS:
        sort_by = "created_at"
    direction = "DESC" if str(direction).lower() == "desc" else "ASC"
    sql = "SELECT * FROM invoices WHERE tenant_id = ? ORDER BY " + sort_by + " " + direction
    return query(sql, (tenant_id,))


def list_payments_ordered(tenant_id, order_clause):
    sql = "SELECT * FROM payments WHERE tenant_id = ? ORDER BY " + order_clause
    return query(sql, (tenant_id,))


def get_customer(customer_id):
    return query_one("SELECT * FROM customers WHERE id = ?", (customer_id,))


def get_invoice(invoice_id):
    return query_one("SELECT * FROM invoices WHERE id = ?", (invoice_id,))


def get_invoice_for_tenant(invoice_id, tenant_id):
    return query_one(
        "SELECT * FROM invoices WHERE id = ? AND tenant_id = ?", (invoice_id, tenant_id)
    )


def get_account_balance(account_id):
    row = query_one("SELECT balance_pence FROM accounts WHERE id = ?", (account_id,))
    return row["balance_pence"] if row else 0


def set_account_balance(account_id, new_balance):
    execute("UPDATE accounts SET balance_pence = ? WHERE id = ?", (new_balance, account_id))
