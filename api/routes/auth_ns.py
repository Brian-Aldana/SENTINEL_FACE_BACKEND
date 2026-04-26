from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from api.controllers.auth_controller import login

ns = Namespace("auth", description="Autenticación de usuarios")

login_model = ns.model("Login", {
    "email":    fields.String(required=True),
    "password": fields.String(required=True),
})

auth_response = ns.model("AuthResponse", {
    "success":      fields.Boolean,
    "access_token": fields.String,
    "usuario_id":   fields.Integer,
    "name":         fields.String,
    "email":        fields.String,
    "roles":        fields.List(fields.String),
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

        token = create_access_token(identity={
            "usuario_id": result["usuario_id"],
            "email":      result["email"],
            "roles":      result["roles"],
        })

        return {**result, "access_token": token}


@ns.route("/refresh")
class AuthRefresh(Resource):
    @jwt_required()
    @ns.response(200, "Token renovado")
    @ns.response(401, "Token inválido o expirado")
    def post(self):
        identity  = get_jwt_identity()
        new_token = create_access_token(identity=identity)
        return {"access_token": new_token}
