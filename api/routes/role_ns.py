from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required
from api.controllers.role_controller import (
    get_all, get_by_id, create, deactivate, activate
)

ns = Namespace("roles", description="Gestión de roles del sistema")

role_model = ns.model("Rol", {
    "role_id":        fields.Integer,
    "name":           fields.String,
    "description":    fields.String,
    "is_active":      fields.Boolean,
    "total_usuarios": fields.Integer,
    "created_at":     fields.String,
})

create_model = ns.model("CrearRol", {
    "name":         fields.String(required=True),
    "description":  fields.String,
    "requestor_id": fields.Integer(required=True),
})

status_model = ns.model("CambioEstadoRol", {
    "requestor_id": fields.Integer(required=True),
})


@ns.route("")
class RoleList(Resource):
    @jwt_required()
    @ns.response(200, "Lista de roles")
    def get(self):
        include_inactive = request.args.get("include_inactive", "false").lower() == "true"
        return {"roles": get_all(include_inactive)}

    @jwt_required()
    @ns.expect(create_model)
    @ns.response(201, "Rol creado", role_model)
    @ns.response(400, "Datos inválidos")
    @ns.response(409, "Nombre duplicado")
    def post(self):
        data        = request.get_json() or {}
        result, err = create(
            data.get("name", ""),
            data.get("description"),
            data.get("requestor_id", 1),
        )
        if err:
            code = 409 if "existe" in err else 400
            ns.abort(code, err)
        return result, 201


@ns.route("/<int:role_id>")
class RoleItem(Resource):
    @jwt_required()
    @ns.response(200, "Rol encontrado", role_model)
    @ns.response(404, "No encontrado")
    def get(self, role_id):
        role, err = get_by_id(role_id)
        if err:
            ns.abort(404, err)
        return role


@ns.route("/<int:role_id>/deactivate")
class RoleDeactivate(Resource):
    @jwt_required()
    @ns.expect(status_model)
    @ns.response(200, "Rol desactivado")
    @ns.response(400, "Ya inactivo")
    @ns.response(404, "No encontrado")
    def patch(self, role_id):
        data    = request.get_json() or {}
        ok, err = deactivate(role_id, data.get("requestor_id", 1))
        if err:
            code = 404 if "no encontrado" in err.lower() else 400
            ns.abort(code, err)
        return {"success": True, "is_active": False}


@ns.route("/<int:role_id>/activate")
class RoleActivate(Resource):
    @jwt_required()
    @ns.expect(status_model)
    @ns.response(200, "Rol activado")
    @ns.response(400, "Ya activo")
    @ns.response(404, "No encontrado")
    def patch(self, role_id):
        data    = request.get_json() or {}
        ok, err = activate(role_id, data.get("requestor_id", 1))
        if err:
            code = 404 if "no encontrado" in err.lower() else 400
            ns.abort(code, err)
        return {"success": True, "is_active": True}
