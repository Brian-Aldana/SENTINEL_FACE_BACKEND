from flask_restx import Namespace, Resource, fields
from flask import request
from api.controllers.alert_controller import get_all, get_by_id, resolve, remove

ns = Namespace("alerts", description="Alertas de seguridad")

alert_model = ns.model("Alert", {
    "alert_id":    fields.Integer,
    "alert_type":  fields.String,
    "severity":    fields.String,
    "description": fields.String,
    "resolved":    fields.Boolean,
    "created_at":  fields.String,
    "event_time":  fields.String,
})

resolve_model = ns.model("Resolve", {
    "admin_id": fields.Integer(required=True),
})


@ns.route("")
class AlertList(Resource):
    @ns.response(200, "Lista de alertas")
    def get(self):
        resolved = request.args.get("resolved", 0)
        return {"alerts": get_all(resolved)}


@ns.route("/<int:alert_id>")
class AlertItem(Resource):
    @ns.response(200, "Alerta encontrada", alert_model)
    @ns.response(404, "No encontrada")
    def get(self, alert_id):
        alert, error = get_by_id(alert_id)
        if error:
            ns.abort(404, error)
        return alert

    @ns.response(200, "Alerta eliminada")
    @ns.response(404, "No encontrada")
    def delete(self, alert_id):
        ok, error = remove(alert_id)
        if error:
            ns.abort(404, error)
        return {"success": True}


@ns.route("/<int:alert_id>/resolve")
class AlertResolve(Resource):
    @ns.expect(resolve_model)
    @ns.response(200, "Alerta resuelta")
    @ns.response(404, "No encontrada")
    def patch(self, alert_id):
        data     = request.get_json(silent=True) or {}
        admin_id = data.get("admin_id")
        ok, error = resolve(alert_id, admin_id)
        if error:
            ns.abort(404, error)
        return {"success": True}