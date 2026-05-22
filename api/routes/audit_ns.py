from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required
from api.controllers.audit_controller import get_all, get_by_id

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
    @jwt_required()
    @ns.response(200, "Registros de auditoría paginados")
    def get(self):
        limit = request.args.get("limit", 20, type=int)
        page  = request.args.get("page",  1,  type=int)
        data  = get_all(limit, page)
        return {
            "audit":    data["items"],
            "total":    data["total"],
            "page":     data["page"],
            "limit":    data["limit"],
            "has_more": data["has_more"],
        }


@ns.route("/<int:audit_id>")
class AuditItem(Resource):
    @jwt_required()
    @ns.response(200, "Registro encontrado", audit_model)
    @ns.response(404, "No encontrado")
    def get(self, audit_id):
        entry, error = get_by_id(audit_id)
        if error:
            ns.abort(404, error)
        return entry