from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restx import abort


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        # identity ya es un dict — no necesita deserialización manual
        roles = identity.get("roles", []) if isinstance(identity, dict) else []
        if "admin" not in roles:
            abort(403, "Se requiere el rol 'admin' para esta operación")
        return fn(*args, **kwargs)

    return wrapper
