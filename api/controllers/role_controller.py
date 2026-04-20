from api.models import role as RoleModel
from api.models import audit as AuditModel


def get_all(include_inactive: bool = False):
    return RoleModel.find_all(include_inactive)


def get_by_id(role_id: int):
    role = RoleModel.find_by_id(role_id)
    if not role:
        return None, "Rol no encontrado"
    return role, None


def create(name: str, description: str, requestor_id):
    if not name:
        return None, "El nombre del rol es requerido"
    try:
        new_id = RoleModel.create(name.strip().lower(), description)
    except Exception as e:
        if "Duplicate" in str(e):
            return None, "Ya existe un rol con ese nombre"
        return None, str(e)
    AuditModel.record(requestor_id, "CREATE_ROLE", "roles", new_id,
                      {"name": name})
    return {"success": True, "role_id": new_id}, None


def deactivate(role_id: int, requestor_id):
    name, err = RoleModel.deactivate(role_id)
    if err:
        return False, err
    AuditModel.record(requestor_id, "DEACTIVATE_ROLE", "roles", role_id,
                      {"name": name})
    return True, None


def activate(role_id: int, requestor_id):
    name, err = RoleModel.activate(role_id)
    if err:
        return False, err
    AuditModel.record(requestor_id, "ACTIVATE_ROLE", "roles", role_id,
                      {"name": name})
    return True, None
