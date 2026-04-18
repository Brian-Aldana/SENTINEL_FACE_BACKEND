# Sentinel Face — Backend

Sistema de control de acceso biométrico con reconocimiento facial y detección de vida activa. El backend expone una API REST que gestiona empleados, registros de acceso, alertas de seguridad y auditoría administrativa.

---

## Tecnologías

| Capa | Tecnología |
|------|-----------|
| Lenguaje | Python 3.10+ |
| Framework | Flask + Flask-RESTX |
| Base de datos | MariaDB 10.11 |
| Reconocimiento facial | InsightFace (buffalo_l) |
| Liveness pasivo | MiniFASNetV2 (ONNX) |
| Liveness activo | MediaPipe Face Mesh |
| Servidor WSGI | Gunicorn |
| Contenedores | Docker + Docker Compose |
| Documentación API | Swagger UI (`/swagger`) |

---

## Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) y [Docker Compose](https://docs.docker.com/compose/install/) instalados
- Puerto `5000` disponible (API)
- Puerto `3307` disponible (MariaDB expuesto al host)

---

## Configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/Brian-Aldana/SENTINEL_FACE_BACKEND.git
cd SENTINEL_FACE_BACKEND
```

### 2. Crear el archivo `.env`

Copia el archivo de ejemplo y rellena los valores:

```bash
cp .env.example .env
```

Edita `.env` con tus credenciales:

```env
DB_HOST=db
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_contraseña
DB_NAME=nombre_de_la_base_de_datos
```

> **Nota:** `DB_HOST=db` es el nombre del servicio en Docker Compose. No cambiar a `localhost` a menos que se ejecute fuera de Docker.

### 3. Agregar los modelos de IA

Coloca los archivos de modelo en la carpeta `models/` en la raíz del proyecto:

```
models/
└── 2.7_80x80_MiniFASNetV2.onnx
```

InsightFace descarga automáticamente el modelo `buffalo_l` en el primer arranque.

---

## Ejecución

```bash
docker compose up --build
```

El primer arranque puede tardar varios minutos mientras Docker descarga las imágenes y se inicializan los modelos de IA.

Una vez activo:

| Servicio | URL |
|---------|-----|
| API REST | `http://localhost:5000/api` |
| Swagger UI | `http://localhost:5000/swagger` |
| MariaDB (host) | `localhost:3307` |

Para detener:

```bash
docker compose down
```

Para detener y eliminar los datos de la base de datos:

```bash
docker compose down -v
```

---

## Estructura del proyecto

```
SENTINEL_FACE_BACKEND/
├── app.py                  # Entry point — factory pattern
├── db.py                   # Conexión a MariaDB
├── face_logic.py           # Pipeline de reconocimiento facial
├── liveness.py             # Detector MiniFASNetV2
├── blink_detector.py       # Detector de parpadeo MediaPipe
├── init.sql                # Esquema inicial de la base de datos
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
└── api/
    ├── __init__.py         # Flask app factory + registro de namespaces
    ├── models/             # Capa de acceso a datos (queries SQL)
    │   ├── admin.py
    │   ├── employee.py
    │   ├── log.py
    │   ├── alert.py
    │   └── audit.py
    ├── controllers/        # Lógica de negocio
    │   ├── auth_controller.py
    │   ├── employee_controller.py
    │   ├── log_controller.py
    │   ├── alert_controller.py
    │   └── audit_controller.py
    └── routes/             # Endpoints HTTP + documentación Swagger
        ├── auth_ns.py
        ├── employee_ns.py
        ├── log_ns.py
        ├── alert_ns.py
        ├── audit_ns.py
        └── recognize_ns.py
```

---

## Endpoints principales

La documentación completa e interactiva está disponible en `http://localhost:5000/swagger`.

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Autenticación de administrador |
| `GET` | `/api/employees` | Listar empleados |
| `POST` | `/api/employees` | Registrar empleado con embedding biométrico |
| `DELETE` | `/api/employees/{id}` | Eliminar empleado |
| `POST` | `/api/recognize` | Reconocimiento facial con liveness |
| `GET` | `/api/logs` | Historial de accesos |
| `GET` | `/api/logs/{id}/image` | Imagen capturada de un evento |
| `GET` | `/api/alerts` | Alertas de seguridad |
| `PATCH` | `/api/alerts/{id}/resolve` | Resolver una alerta |
| `GET` | `/api/audit` | Registros de auditoría |

---

## Arquitectura de seguridad biométrica

El endpoint `/api/recognize` ejecuta un pipeline de tres capas:

```
Frames de video
      │
      ▼
1. Liveness activo — detección de parpadeo (MediaPipe)
      │ falla → DENIED + alerta SPOOFING
      ▼
2. Liveness pasivo — MiniFASNetV2 (anti-spoofing)
      │ falla → DENIED + alerta SPOOFING
      ▼
3. Reconocimiento facial — InsightFace (similitud coseno)
      │ confianza < 0.50 → DENIED
      ▼
      GRANTED — acceso concedido
```

---

## Base de datos

El esquema se inicializa automáticamente desde `init.sql` al primer arranque del contenedor MariaDB. Las tablas principales son:

| Tabla | Propósito |
|-------|-----------|
| `admins` | Administradores del sistema |
| `employees` | Empleados con embeddings biométricos |
| `access_logs` | Registro de cada evento de acceso |
| `security_alerts` | Alertas generadas por eventos sospechosos |
| `audit_log` | Auditoría de acciones administrativas (append-only) |

---

## Variables de entorno

| Variable | Descripción | Ejemplo |
|---------|-------------|---------|
| `DB_HOST` | Host de MariaDB dentro de Docker | `db` |
| `DB_PORT` | Puerto interno de MariaDB | `3306` |
| `DB_USER` | Usuario de la base de datos | `root` |
| `DB_PASSWORD` | Contraseña de la base de datos | — |
| `DB_NAME` | Nombre de la base de datos | — |

---

## Notas de desarrollo

- **Swagger** disponible en `/swagger` con todos los endpoints documentados e interactivos.
- El modelo InsightFace se descarga automáticamente en `~/.insightface/models/buffalo_l/` en el primer arranque — requiere conexión a internet.
- La tabla `audit_log` es **append-only** por diseño: no expone endpoint de eliminación para garantizar trazabilidad.
- Para desarrollo local sin Docker, cambiar `DB_HOST=db` a `DB_HOST=localhost` y `DB_PORT=3306` al puerto expuesto `3307`.

---

## Licencia

Proyecto académico — Ingeniería de Software, 2026.
