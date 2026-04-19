from werkzeug.security import check_password_hash
from api.models import usuario as UsuarioModel


def login(email: str, password: str):
    UsuarioModel.ensure_default_usuario()
    usuario = UsuarioModel.find_by_email(email)
    if not usuario or not check_password_hash(usuario["password_hash"], password):
        return None, "Credenciales inválidas"
    UsuarioModel.update_last_login(usuario["usuario_id"])
    return {
        "success":     True,
        "usuario_id":  usuario["usuario_id"],
        "name":        usuario["full_name"],
        "email":       usuario["email"],
        "roles":       usuario.get("roles", []),
    }, None
