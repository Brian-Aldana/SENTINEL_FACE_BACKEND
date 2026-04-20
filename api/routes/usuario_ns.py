from flask_restx import Namespace, Resource, fields
from flask import request
from api.controllers.usuario_controller import (
    get_all, get_by_id, create, deactivate, activate, assign_role, remove_role
)

ns = Namespace("usuarios", description="Gestión de usuarios del sistema")

usuario_model = ns.model("Usuario", {
    "usuario_id": fields.Integer,
    "full_name":  fields.String,
    "email":      fields.String,
    "is_active":  fields.Boolean,
    "roles":      fields.List(fields.String),
    "created_at": fields.String,
    "last_login": fields.String,
})

create_model = ns.model("CrearUsuario", {
    "full_name":    fields.String(required=True),
    "email":        fields.String(required=True),
    "password":     fields.String(required=True),
    "roles":        fields.List(fields.String),
    "requestor_id": fields.Integer(required=True),
})

role_action_model = ns.model("AccionRol", {
    "role_id":      fields.Integer(required=True),
    "requestor_id": fields.Integer(required=True),
})

status_model = ns.model("CambioEstado", {
    "requestor_id": fields.Integer(required=True),
})


@ns.route("")
class UsuarioList(Resource):
    @ns.response(200, "Lista de usuarios")
    def get(self):
        include_inactive = request.args.get("include_inactive", "false").lower() == "true"
        return {"usuarios": get_all(include_inactive)}

    @ns.expect(create_model)
    @ns.response(201, "Usuario creado")
    @ns.response(400, "Datos inválidos")
    @ns.response(409, "Email duplicado")
    def post(self):
        data        = request.get_json() or {}
        result, err = create(
            data.get("full_name", ""),
            data.get("email", ""),
            data.get("password", ""),
            data.get("roles", []),
            data.get("requestor_id", 1),
        )
        if err:
            code = 409 if "registrado" in err else 400
            ns.abort(code, err)
        return result, 201


@ns.route("/<int:usuario_id>")
class UsuarioItem(Resource):
    @ns.response(200, "Usuario encontrado", usuario_model)
    @ns.response(404, "No encontrado")
    def get(self, usuario_id):
        u, err = get_by_id(usuario_id)
        if err:
            ns.abort(404, err)
        return u


@ns.route("/<int:usuario_id>/deactivate")
class UsuarioDeactivate(Resource):
    @ns.expect(status_model)
    @ns.response(200, "Usuario desactivado")
    @ns.response(400, "Ya inactivo")
    @ns.response(404, "No encontrado")
    def patch(self, usuario_id):
        data    = request.get_json() or {}
        ok, err = deactivate(usuario_id, data.get("requestor_id", 1))
        if err:
            code = 404 if "no encontrado" in err.lower() else 400
            ns.abort(code, err)
        return {"success": True, "is_active": False}


@ns.route("/<int:usuario_id>/activate")
class UsuarioActivate(Resource):
    @ns.expect(status_model)
    @ns.response(200, "Usuario activado")
    @ns.response(400, "Ya activo")
    @ns.response(404, "No encontrado")
    def patch(self, usuario_id):
        data    = request.get_json() or {}
        ok, err = activate(usuario_id, data.get("requestor_id", 1))
        if err:
            code = 404 if "no encontrado" in err.lower() else 400
            ns.abort(code, err)
        return {"success": True, "is_active": True}


@ns.route("/<int:usuario_id>/roles")
class UsuarioRoles(Resource):
    @ns.expect(role_action_model)
    @ns.response(200, "Rol asignado")
    @ns.response(400, "Ya asignado")
    def post(self, usuario_id):
        data    = request.get_json() or {}
        ok, err = assign_role(usuario_id, data.get("role_id"), data.get("requestor_id", 1))
        if err:
            ns.abort(400, err)
        return {"success": True}

    @ns.expect(role_action_model)
    @ns.response(200, "Rol removido")
    @ns.response(400, "No tiene ese rol")
    def delete(self, usuario_id):
        data    = request.get_json() or {}
        ok, err = remove_role(usuario_id, data.get("role_id"), data.get("requestor_id", 1))
        if err:
            ns.abort(400, err)
        return {"success": True}
