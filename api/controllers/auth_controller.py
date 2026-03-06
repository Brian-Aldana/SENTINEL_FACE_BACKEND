from werkzeug.security import check_password_hash
from api.models import admin as AdminModel


def login(email: str, password: str):
    AdminModel.ensure_default_admin()
    admin = AdminModel.find_by_email(email)
    if not admin or not check_password_hash(admin["password_hash"], password):
        return None, "Credenciales inválidas"
    AdminModel.update_last_login(admin["admin_id"])
    return {
        "success":  True,
        "role":     "admin",
        "admin_id": admin["admin_id"],
        "name":     admin["full_name"],
        "email":    admin["email"],
    }, None