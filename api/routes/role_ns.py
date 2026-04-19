from flask_restx import Namespace, Resource, fields
from flask import request
from api.controllers.role_controller import get_all, get_by_id, create, remove

ns = Namespace("roles", description="Gestión de roles del sistema")

role_model = ns.model("Rol", {
    "role_id":        fields.Integer,
    "name":           fields.String,
    "description":    fields.String,
    "total_usuarios": fields.Integer,
    "created_at":     fields.String,
})

create_model = ns.model("CrearRol", {
    "name":         fields.String(required=True),
    "description":  fields.String,
    "requestor_id": fields.Integer(required=True),
})


@ns.route("")
class RoleList(Resource):
    @ns.response(200, "Lista de roles")
    def get(self):
        return {"roles": get_all()}

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
    @ns.response(200, "Rol encontrado", role_model)
    @ns.response(404, "No encontrado")
    def get(self, role_id):
        role, err = get_by_id(role_id)
        if err:
            ns.abort(404, err)
        return role

    @ns.response(200, "Rol eliminado")
    @ns.response(404, "No encontrado")
    def delete(self, role_id):
        requestor   = request.args.get("requestor_id", 1)
        ok, err = remove(role_id, requestor)
        if err:
            ns.abort(404, err)
        return {"success": True}
