from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restx import abort
import json


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        if isinstance(identity, str):
            try:
                identity = json.loads(identity)
            except json.JSONDecodeError:
                pass
        roles = identity.get("roles", []) if isinstance(identity, dict) else []
        if "admin" not in roles:
            abort(403, "Se requiere el rol 'admin' para esta operación")
        return fn(*args, **kwargs)

    return wrapper
