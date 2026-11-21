"""CSV / PDF export endpoints."""
import os
import subprocess

from flask import Blueprint, g, jsonify, request, send_file

from ..auth import login_required
from ..config import settings

bp = Blueprint("exports", __name__, url_prefix="/api/exports")


@bp.get("/download")
@login_required
def download():
    filename = request.args.get("file", "")
    path = os.path.join(settings.EXPORT_DIR, filename)
    return send_file(path, as_attachment=True)


@bp.post("/pdf")
@login_required
def render_pdf():
    report_name = request.get_json(force=True).get("report", "summary")
    out = os.path.join(settings.EXPORT_DIR, f"{g.user['tenant_id']}-{report_name}.pdf")
    subprocess.run(f"wkhtmltopdf /tmp/{report_name}.html {out}", shell=True, check=True)
    return jsonify({"file": os.path.basename(out)})


@bp.post("/archive")
@login_required
def archive_exports():
    tenant_dir = os.path.join(settings.EXPORT_DIR, str(int(g.user["tenant_id"])))
    archive = tenant_dir + ".tar.gz"
    subprocess.run(["tar", "-czf", archive, "-C", tenant_dir, "."], check=True)
    return jsonify({"archive": os.path.basename(archive)})
