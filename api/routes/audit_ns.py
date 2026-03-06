from flask_restx import Namespace, Resource, fields
from flask import request
from api.controllers.audit_controller import get_all, get_by_id, remove

ns = Namespace("audit", description="Auditoría de acciones administrativas")

audit_model = ns.model("AuditEntry", {
    "audit_id":     fields.Integer,
    "action":       fields.String,
    "target_table": fields.String,
    "target_id":    fields.Integer,
    "detail":       fields.Raw,
    "ip_address":   fields.String,
    "created_at":   fields.String,
    "admin_name":   fields.String,
})


@ns.route("")
class AuditList(Resource):
    @ns.response(200, "Registros de auditoría")
    def get(self):
        limit = request.args.get("limit", 100)
        return {"audit": get_all(limit)}


@ns.route("/<int:audit_id>")
class AuditItem(Resource):
    @ns.response(200, "Registro encontrado", audit_model)
    @ns.response(404, "No encontrado")
    def get(self, audit_id):
        entry, error = get_by_id(audit_id)
        if error:
            ns.abort(404, error)
        return entry

    @ns.response(200, "Registro eliminado")
    @ns.response(404, "No encontrado")
    def delete(self, audit_id):
        ok, error = remove(audit_id)
        if error:
            ns.abort(404, error)
        return {"success": True}