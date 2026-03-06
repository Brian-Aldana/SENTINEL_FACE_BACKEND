from api.models import alert as AlertModel
from api.models import audit as AuditModel


def get_all(resolved=0):
    return AlertModel.find_all(resolved)


def get_by_id(alert_id: int):
    alert = AlertModel.find_by_id(alert_id)
    if not alert:
        return None, "Alerta no encontrada"
    return alert, None


def resolve(alert_id: int, admin_id):
    ok = AlertModel.resolve(alert_id, admin_id)
    if not ok:
        return False, "Alerta no encontrada"
    AuditModel.record(admin_id, "RESOLVE_ALERT", "security_alerts", alert_id)
    return True, None


def remove(alert_id: int):
    if not AlertModel.delete(alert_id):
        return False, "Alerta no encontrada"
    return True, None