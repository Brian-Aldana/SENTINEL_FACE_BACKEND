import os
from flask import Flask
from flask_restx import Api
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ── Rate limiter (inicializado antes de importar rutas para evitar imports circulares) ──
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # Sin límite global; aplicar por ruta
    storage_uri=os.getenv("RATELIMIT_STORAGE_URL", "memory://"),
)

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

import jwt
from flask_jwt_extended.exceptions import JWTExtendedException, NoAuthorizationError

@api.errorhandler(NoAuthorizationError)
def handle_auth_error(e):
    return {'message': str(e)}, 401

@api.errorhandler(JWTExtendedException)
def handle_jwt_exceptions(e):
    return {'message': str(e)}, 401

@api.errorhandler(jwt.ExpiredSignatureError)
def handle_expired_error(e):
    return {'message': 'El token ha expirado'}, 401

@api.errorhandler(jwt.InvalidTokenError)
def handle_invalid_error(e):
    return {'message': 'El token es inválido'}, 401


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET_KEY no está definida en las variables de entorno.")
    app.config["JWT_SECRET_KEY"] = jwt_secret

    # B-09: JWT TTL configurable — default 1 hora (antes: 24h)
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600)
    )

    JWTManager(app)

    # B-01: CORS restringido a orígenes configurados
    # Si ALLOWED_ORIGINS está vacío → permitir todo (seguro para APIs consumidas solo por apps móviles)
    # Si ALLOWED_ORIGINS tiene valores → restringir a esos orígenes (necesario si hay frontend web)
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
    allowed_origins = [o.strip() for o in allowed_origins if o.strip()]
    CORS(
        app,
        origins=allowed_origins if allowed_origins else "*",
        supports_credentials=bool(allowed_origins),
    )

    # B-04: Inicializar rate limiter
    limiter.init_app(app)

    api.init_app(app)

    # B-02: Seed inicial — solo si la DB no tiene el usuario admin (una sola vez al inicio)
    from api.models import usuario as UsuarioModel
    with app.app_context():
        try:
            UsuarioModel.ensure_default_usuario()
        except Exception as e:
            app.logger.warning(f"No se pudo crear el usuario por defecto: {e}")

    return app
