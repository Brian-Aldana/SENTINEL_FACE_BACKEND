from flask_restx import Namespace, Resource, fields
from flask import request
from api.controllers.auth_controller import login

ns = Namespace("auth", description="Autenticación de administradores")

login_model = ns.model("Login", {
    "email":    fields.String(required=True, example="admin@admin.com"),
    "password": fields.String(required=True, example="admin123"),
})

session_model = ns.model("Session", {
    "success":  fields.Boolean,
    "role":     fields.String,
    "admin_id": fields.Integer,
    "name":     fields.String,
    "email":    fields.String,
})


@ns.route("/login")
class Login(Resource):
    @ns.expect(login_model)
    @ns.response(200, "Login exitoso", session_model)
    @ns.response(400, "Campos requeridos")
    @ns.response(401, "Credenciales inválidas")
    def post(self):
        data     = request.get_json(silent=True) or {}
        email    = data.get("email", "").strip()
        password = data.get("password", "")
        if not email or not password:
            ns.abort(400, "Email y contraseña requeridos")
        result, error = login(email, password)
        if error:
            ns.abort(401, error)
        return result