import os
from flask import Flask
from flask_restx import Api
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from api.routes.auth_ns      import ns as auth_ns
from api.routes.usuario_ns   import ns as usuario_ns
from api.routes.role_ns      import ns as role_ns
from api.routes.employee_ns  import ns as employee_ns
from api.routes.log_ns       import ns as log_ns
from api.routes.alert_ns     import ns as alert_ns
from api.routes.audit_ns     import ns as audit_ns
from api.routes.recognize_ns import ns as recognize_ns

api = Api(
    title="Sentinel Face API",
    version="3.1",
    description="Sistema de control de acceso biométrico con reconocimiento facial",
    doc="/swagger",
    prefix="/api",
)

api.add_namespace(auth_ns)
api.add_namespace(usuario_ns)
api.add_namespace(role_ns)
api.add_namespace(employee_ns)
api.add_namespace(log_ns)
api.add_namespace(alert_ns)
api.add_namespace(audit_ns)
api.add_namespace(recognize_ns)


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET_KEY no está definida en las variables de entorno.")
    app.config["JWT_SECRET_KEY"]       = jwt_secret
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 86400  # 24 horas en segundos

    JWTManager(app)
    CORS(app)
    api.init_app(app)
    return app
