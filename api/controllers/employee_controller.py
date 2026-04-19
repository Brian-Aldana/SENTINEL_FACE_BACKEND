import re
from api.models import employee as EmployeeModel
from api.models import audit as AuditModel
from face_logic import process_registration


def _sanitize(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9\sáéíóúÁÉÍÓÚñÑ\-\.]", "", text).strip()


def get_all():
    return EmployeeModel.find_all()


def get_by_id(employee_id: int):
    emp = EmployeeModel.find_by_id(employee_id)
    if not emp:
        return None, "Empleado no encontrado"
    return emp, None


def register(name: str, document_id: str, usuario_id, image_bytes: bytes):
    clean_name = _sanitize(name)
    if not clean_name:
        return None, "Nombre con caracteres inválidos"

    try:
        embedding = process_registration(image_bytes, skip_liveness=True)
    except ValueError as e:
        return None, str(e)

    try:
        new_id = EmployeeModel.create(
            clean_name, document_id or None, embedding.tobytes(), usuario_id
        )
    except Exception as e:
        if "Duplicate" in str(e):
            return None, "El documento ya está registrado"
        return None, str(e)

    AuditModel.record(usuario_id, "CREATE_EMPLOYEE", "employees", new_id,
                      {"full_name": clean_name, "document_id": document_id})
    return {"success": True, "employee_id": new_id}, None


def remove(employee_id: int, usuario_id):
    full_name = EmployeeModel.delete(employee_id)
    if full_name is None:
        return False, "Empleado no encontrado"
    AuditModel.record(usuario_id, "DELETE_EMPLOYEE", "employees", employee_id,
                      {"full_name": full_name})
    return True, None
