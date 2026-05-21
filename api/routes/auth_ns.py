from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from api.controllers.auth_controller import login
from api import limiter

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


@ns.route("/run-migration-temp")
class RunMigration(Resource):
    def get(self):
        from db import get_db
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        logs = []
        try:
            # Check if column photo_img exists
            cursor.execute("SHOW COLUMNS FROM employees LIKE 'photo_img'")
            col = cursor.fetchone()
            if col:
                logs.append("photo_img column already exists in employees table.")
            else:
                logs.append("photo_img column does not exist. Adding it...")
                cursor.execute("ALTER TABLE employees ADD COLUMN photo_img MEDIUMBLOB NULL;")
                conn.commit()
                logs.append("ALTER TABLE employees ADD COLUMN photo_img MEDIUMBLOB NULL executed successfully.")
            
            # Fetch current columns
            cursor.execute("SHOW COLUMNS FROM employees")
            columns = cursor.fetchall()
            logs.append(f"Current columns in employees table: {columns}")
            return {"success": True, "logs": logs}
        except Exception as e:
            return {"success": False, "error": str(e), "logs": logs}
        finally:
            cursor.close()
            conn.close()

