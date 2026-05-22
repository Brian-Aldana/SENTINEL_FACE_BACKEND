from werkzeug.security import check_password_hash
from api.models import usuario as UsuarioModel
from api.models import audit as AuditModel


def login(email: str, password: str):
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


def change_user_password(usuario_id: int, current_password: str, new_password: str):
    if not current_password or not new_password:
        return False, "La contraseña actual y la nueva son requeridas"
    if len(new_password) < 6:
        return False, "La nueva contraseña debe tener al menos 6 caracteres"
    
    success, result = UsuarioModel.change_password(usuario_id, current_password, new_password)
    if not success:
        return False, result
        
    AuditModel.record(usuario_id, "CHANGE_PASSWORD", "usuarios", usuario_id,
                      {"full_name": result})
    return True, None

