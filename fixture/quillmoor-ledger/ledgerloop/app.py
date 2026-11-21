"""Flask application factory."""
import logging

from flask import Flask, jsonify, request

from .config import settings
from .routes import auth_routes, exports, invoices, payments
from .services import imports, webhooks
from .auth import login_required


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../web/templates", static_folder="../web/static")
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_UPLOAD_BYTES
    app.config["DEBUG"] = settings.DEBUG
    logging.basicConfig(level=logging.INFO)

    for module in (auth_routes, exports, invoices, payments):
        app.register_blueprint(module.bp)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/layout")
    @login_required
    def layout():
        saved = request.cookies.get("layout")
        if not saved:
            return jsonify({})
        return jsonify(imports.load_saved_layout(saved))

    @app.post("/api/layout/json")
    @login_required
    def layout_json():
        return jsonify(imports.load_layout_json(request.get_data(as_text=True)))

    @app.post("/api/settings/webhook-test")
    @login_required
    def webhook_test():
        url = request.get_json(force=True).get("url", "")
        return jsonify({"preview": webhooks.test_webhook(url)})

    @app.post("/api/imports/mapping")
    @login_required
    def mapping_upload():
        return jsonify(imports.import_mapping_yaml(request.get_data()))

    return app


app = create_app()
