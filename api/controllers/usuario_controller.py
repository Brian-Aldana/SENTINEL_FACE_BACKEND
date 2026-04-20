from api.models import usuario as UsuarioModel
from api.models import audit as AuditModel


def get_all(include_inactive: bool = False):
    return UsuarioModel.find_all(include_inactive)


def get_by_id(usuario_id: int):
    u = UsuarioModel.find_by_id(usuario_id)
    if not u:
        return None, "Usuario no encontrado"
    return u, None


def create(full_name: str, email: str, password: str, roles: list, requestor_id):
    if not full_name or not email or not password:
        return None, "Nombre, email y contraseña son requeridos"
    try:
        new_id = UsuarioModel.create(full_name, email, password, roles)
    except Exception as e:
        if "Duplicate" in str(e):
            return None, "El email ya está registrado"
        return None, str(e)
    AuditModel.record(requestor_id, "CREATE_USUARIO", "usuarios", new_id,
                      {"full_name": full_name, "email": email, "roles": roles})
    return {"success": True, "usuario_id": new_id}, None


def deactivate(usuario_id: int, requestor_id):
    full_name, err = UsuarioModel.deactivate(usuario_id)
    if err:
        return False, err
    AuditModel.record(requestor_id, "DEACTIVATE_USUARIO", "usuarios", usuario_id,
                      {"full_name": full_name})
    return True, None


def activate(usuario_id: int, requestor_id):
    full_name, err = UsuarioModel.activate(usuario_id)
    if err:
        return False, err
    AuditModel.record(requestor_id, "ACTIVATE_USUARIO", "usuarios", usuario_id,
                      {"full_name": full_name})
    return True, None


def assign_role(usuario_id: int, role_id: int, requestor_id):
    ok = UsuarioModel.assign_role(usuario_id, role_id, requestor_id)
    if not ok:
        return False, "El rol ya está asignado a este usuario"
    AuditModel.record(requestor_id, "ASSIGN_ROLE", "usuarios_roles", usuario_id,
                      {"role_id": role_id})
    return True, None


def remove_role(usuario_id: int, role_id: int, requestor_id):
    ok = UsuarioModel.remove_role(usuario_id, role_id)
    if not ok:
        return False, "El usuario no tiene ese rol"
    AuditModel.record(requestor_id, "REMOVE_ROLE", "usuarios_roles", usuario_id,
                      {"role_id": role_id})
    return True, None
