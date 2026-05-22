from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from api.controllers.auth_controller import login, change_user_password
from api import limiter

ns = Namespace("auth", description="Autenticación de usuarios")

login_model = ns.model("Login", {
    "email":    fields.String(required=True),
    "password": fields.String(required=True),
})

change_password_model = ns.model("ChangePassword", {
    "current_password": fields.String(required=True),
    "new_password":     fields.String(required=True),
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
    @limiter.limit("5 per minute")
    @ns.expect(login_model)
    @ns.response(200, "Login exitoso", auth_response)
    @ns.response(400, "Campos requeridos")
    @ns.response(401, "Credenciales inválidas")
    @ns.response(429, "Demasiados intentos")
    def post(self):
        data     = request.get_json() or {}
        email    = data.get("email", "").strip()
        password = data.get("password", "")

        if not email or not password:
            ns.abort(400, "Email y contraseña son requeridos")

        result, error = login(email, password)
        if error:
            ns.abort(401, error)

        # B-06: Dict directo — sin json.dumps
        token = create_access_token(identity={
            "usuario_id": result["usuario_id"],
            "email":      result["email"],
            "roles":      result["roles"],
        })

        return {**result, "access_token": token}


@ns.route("/refresh")
class AuthRefresh(Resource):
    @jwt_required(verify_type=False)  # B-03: Acepta tokens expirados para poder renovarlos
    @ns.response(200, "Token renovado")
    @ns.response(401, "Token inválido o expirado")
    def post(self):
        identity  = get_jwt_identity()
        new_token = create_access_token(identity=identity)
        return {"access_token": new_token}


@ns.route("/change-password")
class AuthChangePassword(Resource):
    @jwt_required()
    @ns.expect(change_password_model)
    @ns.response(200, "Contraseña cambiada exitosamente")
    @ns.response(400, "Datos inválidos")
    @ns.response(401, "Token inválido o expirado")
    def post(self):
        identity = get_jwt_identity()
        usuario_id = identity.get("usuario_id")
        data = request.get_json() or {}
        current_password = data.get("current_password", "")
        new_password = data.get("new_password", "")

        if not current_password or not new_password:
            ns.abort(400, "Contraseña actual y nueva son requeridas")

        success, error = change_user_password(usuario_id, current_password, new_password)
        if not success:
            ns.abort(400, error)

        return {"success": True, "message": "Contraseña cambiada exitosamente"}



