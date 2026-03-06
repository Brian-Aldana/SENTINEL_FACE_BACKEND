from api.models import audit as AuditModel


def get_all(limit=100):
    return AuditModel.find_all(limit)


def get_by_id(audit_id: int):
    entry = AuditModel.find_by_id(audit_id)
    if not entry:
        return None, "Registro no encontrado"
    return entry, None