"""Login, password reset and redirects."""
from urllib.parse import urlparse

from flask import Blueprint, jsonify, redirect, request

from .. import db
from ..auth import authenticate, issue_token
from ..config import settings
from ..utils.crypto import generate_reset_token, hash_password

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.post("/login")
def login():
    body = request.get_json(force=True)
    user = authenticate(body.get("email"), body.get("password"))
    if not user:
        return jsonify({"error": "invalid credentials"}), 401
    return jsonify({"token": issue_token(user)})


@bp.post("/password-reset")
def password_reset():
    email = request.get_json(force=True).get("email")
    token = generate_reset_token()
    db.execute("UPDATE users SET reset_token = ? WHERE email = ?", (token, email))
    return jsonify({"status": "if the account exists, an email was sent"})


@bp.post("/register")
def register():
    body = request.get_json(force=True)
    password = body.get("password", "")
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return jsonify({"error": "password too short"}), 400
    db.execute(
        "INSERT INTO users (email, password_hash, role, tenant_id) VALUES (?, ?, 'member', ?)",
        (body.get("email"), hash_password(password), body.get("tenant_id")),
    )
    return jsonify({"created": True}), 201


@bp.get("/continue")
def continue_after_login():
    target = request.args.get("next", "/")
    return redirect(target)


@bp.get("/docs-redirect")
def docs_redirect():
    target = request.args.get("to", "https://docs.quillmoor.example/")
    host = urlparse(target).hostname
    if host not in settings.ALLOWED_REDIRECT_HOSTS:
        target = "https://docs.quillmoor.example/"
    return redirect(target)
