from flask_restx import Namespace, Resource, fields
from flask import request, Response
from flask_jwt_extended import jwt_required
from api.controllers.employee_controller import get_all, get_by_id, register, deactivate, get_image
from api.decorators import admin_required

ns = Namespace("employees", description="Gestión de empleados")

employee_model = ns.model("Employee", {
    "employee_id":   fields.Integer,
    "full_name":     fields.String,
    "document_id":   fields.String,
    "is_active":     fields.Boolean,
    "registered_by": fields.String,
    "created_at":    fields.String,
    "updated_at":    fields.String,
})

deactivate_model = ns.model("DeactivateEmployee", {
    "usuario_id": fields.String(required=True),
})


@ns.route("")
class EmployeeList(Resource):
    @jwt_required()
    @ns.response(200, "Lista de empleados")
    def get(self):
        return {"employees": get_all()}

    @admin_required
    @ns.response(201, "Empleado registrado")
    @ns.response(403, "Rol de administrador requerido")
    @ns.response(400, "Datos inválidos")
    @ns.response(409, "Documento duplicado")
    def post(self):
        name       = request.form.get("full_name", "").strip()
        document   = request.form.get("document_id", "").strip()
        usuario_id = request.form.get("usuario_id")
        image_file = request.files.get("photo")

        if not name or not image_file:
            ns.abort(400, "Nombre e imagen son requeridos")

        result, error = register(name, document, usuario_id, image_file.read())
        if error:
            code = 409 if "duplicado" in error.lower() else 400
            ns.abort(code, error)
        return result, 201


@ns.route("/<int:employee_id>")
class EmployeeItem(Resource):
    @jwt_required()
    @ns.response(200, "Empleado encontrado", employee_model)
    @ns.response(404, "No encontrado")
    def get(self, employee_id):
        emp, error = get_by_id(employee_id)
        if error:
            ns.abort(404, error)
        return emp

    @admin_required
    @ns.response(405, "Operación no permitida — usar PATCH /deactivate")
    def delete(self, employee_id):
        ns.abort(
            405,
            "El borrado físico de empleados está deshabilitado. "
            "Use PATCH /employees/{id}/deactivate para desactivar el registro."
        )


@ns.route("/<int:employee_id>/deactivate")
class EmployeeDeactivate(Resource):
    @admin_required
    @ns.expect(deactivate_model)
    @ns.response(200, "Empleado desactivado")
    @ns.response(400, "Ya inactivo")
    @ns.response(403, "Rol de administrador requerido")
    @ns.response(404, "No encontrado")
    def patch(self, employee_id):
        data       = request.get_json(silent=True) or {}
        usuario_id = data.get("usuario_id")
        ok, err    = deactivate(employee_id, usuario_id)
        if err:
            code = 404 if "no encontrado" in err.lower() else 400
            ns.abort(code, err)
        return {"success": True, "is_active": False}


@ns.route("/<int:employee_id>/image")
class EmployeeImage(Resource):
    @jwt_required()
    @ns.response(200, "Imagen de registro del empleado")
    @ns.response(404, "Imagen no encontrada")
    def get(self, employee_id):
        img = get_image(employee_id)
        if not img:
            ns.abort(404, "Imagen no encontrada")
        return Response(img, mimetype="image/jpeg")
