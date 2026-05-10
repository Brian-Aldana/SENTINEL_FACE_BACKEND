# Plan de corrección — SENTINEL_FACE_BACKEND

> Instrucciones para el agente: aplica los pasos en el orden exacto indicado. Cada paso especifica el archivo, la ubicación exacta del cambio y el código resultante. No modifiques ningún otro archivo fuera de los listados.

---

## Paso 1 — `api/models/log.py` — renombrar alias `person_name` → `full_name`

**Problema:** los queries SQL retornan el campo como `person_name` pero toda la app móvil accede a `item.full_name`. Todos los nombres de empleados se muestran como `undefined` en la app.

**Localiza** las dos funciones `find_all` y `find_by_id` en `api/models/log.py`.

En **`find_all`**, reemplaza esta línea del SELECT:

```python
# ANTES
                   e.full_name AS person_name
```

```python
# DESPUÉS
                   e.full_name AS full_name
```

En **`find_by_id`**, aplica el mismo reemplazo en su SELECT:

```python
# ANTES
                   e.full_name AS person_name
```

```python
# DESPUÉS
                   e.full_name AS full_name
```

El modelo Swagger en `log_ns.py` documenta el campo como `person_name`. Actualízalo también para mantener coherencia con la realidad:

En `api/routes/log_ns.py`, en el `log_model`:

```python
# ANTES
    "person_name": fields.String,
```

```python
# DESPUÉS
    "full_name": fields.String,
```

---

## Paso 2 — `api/routes/employee_ns.py` — corregir nombres de campos del form

**Problema:** el backend lee `name` e `image` del form, pero la app manda `full_name` y `photo`. El registro de empleados siempre falla con 400.

**Localiza** el método `post` de la clase `EmployeeList` en `api/routes/employee_ns.py`.

Reemplaza las dos líneas de lectura del form:

```python
# ANTES
        name       = request.form.get("name", "").strip()
        document   = request.form.get("document_id", "").strip()
        usuario_id = request.form.get("usuario_id")
        image_file = request.files.get("image")
```

```python
# DESPUÉS
        name       = request.form.get("full_name", "").strip()
        document   = request.form.get("document_id", "").strip()
        usuario_id = request.form.get("usuario_id")
        image_file = request.files.get("photo")
```

No cambies nada más en ese método.

---

## Paso 3 — Crear endpoint `PATCH /employees/:id/deactivate`

**Problema:** la app llama `PATCH /employees/:id/deactivate` con `{ usuario_id }` pero ese endpoint no existe. El backend solo tiene `DELETE /employees/:id` (hard delete). Se necesita una desactivación lógica (`is_active = 0`) para respetar la auditoría.

### Paso 3a — `api/models/employee.py` — agregar función `deactivate`

Al final del archivo `api/models/employee.py`, después de la función `find_active_with_embeddings`, agrega esta función nueva:

```python
def deactivate(employee_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT full_name, is_active FROM employees WHERE employee_id = %s",
            (employee_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None, "Empleado no encontrado"
        if not row["is_active"]:
            return None, "El empleado ya está inactivo"
        cursor.execute(
            "UPDATE employees SET is_active = 0, updated_at = NOW() WHERE employee_id = %s",
            (employee_id,)
        )
        conn.commit()
        return row["full_name"], None
    finally:
        cursor.close()
        conn.close()
```

### Paso 3b — `api/controllers/employee_controller.py` — agregar función `deactivate`

En `api/controllers/employee_controller.py`, agrega el import de `AuditModel` si no está (ya está) y agrega esta función al final del archivo:

```python
def deactivate(employee_id: int, usuario_id):
    full_name, err = EmployeeModel.deactivate(employee_id)
    if err:
        return False, err
    AuditModel.record(usuario_id, "DEACTIVATE_EMPLOYEE", "employees", employee_id,
                      {"full_name": full_name})
    return True, None
```

### Paso 3c — `api/routes/employee_ns.py` — agregar import y endpoint

**Primero**, actualiza la línea de import del controller al inicio del archivo:

```python
# ANTES
from api.controllers.employee_controller import get_all, get_by_id, register, remove
```

```python
# DESPUÉS
from api.controllers.employee_controller import get_all, get_by_id, register, remove, deactivate
```

**Segundo**, agrega el modelo para el body del endpoint. Después de la definición de `employee_model` y antes del primer `@ns.route`, inserta:

```python
deactivate_model = ns.model("DeactivateEmployee", {
    "usuario_id": fields.String(required=True),
})
```

**Tercero**, agrega la clase del nuevo endpoint. Insértala después de la clase `EmployeeItem` existente y antes del final del archivo:

```python
@ns.route("/<int:employee_id>/deactivate")
class EmployeeDeactivate(Resource):
    @admin_required
    @ns.expect(deactivate_model)
    @ns.response(200, "Empleado desactivado")
    @ns.response(400, "Ya inactivo")
    @ns.response(403, "Rol de administrador requerido")
    @ns.response(404, "No encontrado")
    def patch(self, employee_id):
        data       = request.get_json(silent=True) or {}
        usuario_id = data.get("usuario_id")
        ok, err    = deactivate(employee_id, usuario_id)
        if err:
            code = 404 if "no encontrado" in err.lower() else 400
            ns.abort(code, err)
        return {"success": True, "is_active": False}
```

---

## Paso 4 — `api/models/alert.py` — corregir alias `resolved_by_name` → `resolved_by`

**Problema:** `find_by_id` retorna el campo como `resolved_by_name` pero `alert-detail.tsx` accede a `alert.resolved_by`. El campo "Resuelta por" en el detalle siempre está vacío.

**Localiza** la función `find_by_id` en `api/models/alert.py`.

En el SELECT de esa función, reemplaza:

```python
# ANTES
                   u.full_name AS resolved_by_name
```

```python
# DESPUÉS
                   u.full_name AS resolved_by
```

No toques `find_all` — esa función no retorna ese campo.

---

## Paso 5 — `api/routes/log_ns.py` — proteger DELETE con `@admin_required`

**Problema:** el `DELETE /logs/:id` usa `@jwt_required()`, cualquier usuario autenticado puede borrar logs de auditoría.

**Localiza** el import al inicio de `api/routes/log_ns.py` y agrega el import del decorador:

```python
# ANTES
from flask_jwt_extended import jwt_required
```

```python
# DESPUÉS
from flask_jwt_extended import jwt_required
from api.decorators import admin_required
```

**Luego**, localiza el método `delete` dentro de la clase `LogItem` y reemplaza el decorador:

```python
# ANTES
    @jwt_required()
    @ns.response(200, "Log eliminado")
    @ns.response(404, "No encontrado")
    def delete(self, log_id):
```

```python
# DESPUÉS
    @admin_required
    @ns.response(200, "Log eliminado")
    @ns.response(403, "Rol de administrador requerido")
    @ns.response(404, "No encontrado")
    def delete(self, log_id):
```

---

## Verificación final

Después de aplicar todos los pasos, verifica que los siguientes endpoints respondan correctamente en Railway o en local:

```
POST /api/employees
  body: multipart/form-data
  campos: full_name="Test User", document_id="123", usuario_id="1", photo=<archivo>
  esperado: 201 { success: true, employee_id: N }

PATCH /api/employees/1/deactivate
  header: Authorization: Bearer <token admin>
  body: { "usuario_id": "1" }
  esperado: 200 { success: true, is_active: false }

GET /api/logs
  esperado: los objetos tienen campo "full_name", no "person_name"

GET /api/alerts/1
  esperado: el objeto tiene campo "resolved_by", no "resolved_by_name"

DELETE /api/logs/1
  header: Authorization: Bearer <token sin rol admin>
  esperado: 403
```
