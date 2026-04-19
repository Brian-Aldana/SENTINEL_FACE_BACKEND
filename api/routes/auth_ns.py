from flask_restx import Namespace, Resource, fields
from flask import request
from api.controllers.auth_controller import login

ns = Namespace("auth", description="Autenticación de usuarios")

login_model = ns.model("Login", {
    "email":    fields.String(required=True),
    "password": fields.String(required=True),
})

auth_response = ns.model("AuthResponse", {
    "success":    fields.Boolean,
    "usuario_id": fields.Integer,
    "name":       fields.String,
    "email":      fields.String,
    "roles":      fields.List(fields.String),
})


@ns.route("/login")
class AuthLogin(Resource):
    @ns.expect(login_model)
    @ns.response(200, "Login exitoso", auth_response)
    @ns.response(400, "Campos requeridos")
    @ns.response(401, "Credenciales inválidas")
    def post(self):
        data     = request.get_json() or {}
        email    = data.get("email", "").strip()
        password = data.get("password", "")
        if not email or not password:
            ns.abort(400, "Email y contraseña son requeridos")
        result, error = login(email, password)
        if error:
            ns.abort(401, error)
        return result
