from flask_restx import Namespace, Resource, fields
from flask import request
from api.controllers.employee_controller import get_all, get_by_id, register, remove

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


@ns.route("")
class EmployeeList(Resource):
    @ns.response(200, "Lista de empleados")
    def get(self):
        return {"employees": get_all()}

    @ns.response(201, "Empleado registrado")
    @ns.response(400, "Datos inválidos")
    @ns.response(409, "Documento duplicado")
    def post(self):
        name       = request.form.get("name", "").strip()
        document   = request.form.get("document_id", "").strip()
        usuario_id = request.form.get("usuario_id")
        image_file = request.files.get("image")

        if not name or not image_file:
            ns.abort(400, "Nombre e imagen son requeridos")

        result, error = register(name, document, usuario_id, image_file.read())
        if error:
            code = 409 if "duplicado" in error.lower() else 400
            ns.abort(code, error)
        return result, 201


@ns.route("/<int:employee_id>")
class EmployeeItem(Resource):
    @ns.response(200, "Empleado encontrado", employee_model)
    @ns.response(404, "No encontrado")
    def get(self, employee_id):
        emp, error = get_by_id(employee_id)
        if error:
            ns.abort(404, error)
        return emp

    @ns.response(200, "Empleado eliminado")
    @ns.response(404, "No encontrado")
    def delete(self, employee_id):
        usuario_id = request.args.get("usuario_id")
        ok, error  = remove(employee_id, usuario_id)
        if error:
            ns.abort(404, error)
        return {"success": True}
