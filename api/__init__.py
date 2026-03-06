from flask import Flask
from flask_restx import Api
from flask_cors import CORS

from api.routes.auth_ns      import ns as auth_ns
from api.routes.employee_ns  import ns as employee_ns
from api.routes.log_ns       import ns as log_ns
from api.routes.alert_ns     import ns as alert_ns
from api.routes.audit_ns     import ns as audit_ns
from api.routes.recognize_ns import ns as recognize_ns

api = Api(
    title="Sentinel Face API",
    version="2.0",
    description="Sistema de control de acceso biométrico con reconocimiento facial",
    doc="/swagger",
    prefix="/api",
)

api.add_namespace(auth_ns)
api.add_namespace(employee_ns)
api.add_namespace(log_ns)
api.add_namespace(alert_ns)
api.add_namespace(audit_ns)
api.add_namespace(recognize_ns)


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    CORS(app)
    api.init_app(app)
    return app