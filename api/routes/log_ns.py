from flask_restx import Namespace, Resource, fields
from flask import request, Response
from flask_jwt_extended import jwt_required
from api.controllers.log_controller import get_all, get_by_id, recognize, remove, get_image

ns = Namespace("logs", description="Registro de accesos")

log_model = ns.model("AccessLog", {
    "log_id":      fields.Integer,
    "access_result": fields.String,
    "confidence":  fields.Float,
    "liveness":    fields.String,
    "event_time":  fields.String,
    "person_name": fields.String,
})


@ns.route("")
class LogList(Resource):
    @jwt_required()
    @ns.response(200, "Lista de logs")
    def get(self):
        result_filter = request.args.get("result")
        limit         = request.args.get("limit", 50)
        return {"logs": get_all(result_filter, limit)}


@ns.route("/<int:log_id>")
class LogItem(Resource):
    @jwt_required()
    @ns.response(200, "Log encontrado", log_model)
    @ns.response(404, "No encontrado")
    def get(self, log_id):
        log, error = get_by_id(log_id)
        if error:
            ns.abort(404, error)
        return log

    @jwt_required()
    @ns.response(200, "Log eliminado")
    @ns.response(404, "No encontrado")
    def delete(self, log_id):
        ok, error = remove(log_id)
        if error:
            ns.abort(404, error)
        return {"success": True}


@ns.route("/<int:log_id>/image")
class LogImage(Resource):
    @jwt_required()
    @ns.response(200, "Imagen del evento")
    @ns.response(404, "Imagen no encontrada")
    def get(self, log_id):
        img = get_image(log_id)
        if not img:
            ns.abort(404, "Imagen no encontrada")
        return Response(img, mimetype="image/jpeg")