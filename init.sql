-- ============================================================
--  SENTINEL FACE  —  init.sql
--  Ejecutado automáticamente por MariaDB al crear el contenedor
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ── 1. ROLES ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roles (
    role_id     INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    name        VARCHAR(80)     NOT NULL,
    description VARCHAR(255)        NULL,
    is_active   TINYINT(1)      NOT NULL DEFAULT 1,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id),
    UNIQUE KEY uq_role_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 2. USUARIOS ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usuarios (
    usuario_id    INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    full_name     VARCHAR(150)    NOT NULL,
    email         VARCHAR(150)    NOT NULL,
    password_hash VARCHAR(256)    NOT NULL,
    is_active     TINYINT(1)      NOT NULL DEFAULT 1,
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login    DATETIME            NULL,
    PRIMARY KEY (usuario_id),
    UNIQUE KEY uq_usuario_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 3. USUARIOS_ROLES (tabla intermedia) ─────────────────────
CREATE TABLE IF NOT EXISTS usuarios_roles (
    usuario_id    INT UNSIGNED    NOT NULL,
    role_id       INT UNSIGNED    NOT NULL,
    asignado_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    asignado_por  INT UNSIGNED        NULL,
    PRIMARY KEY (usuario_id, role_id),
    CONSTRAINT fk_ur_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios (usuario_id) ON DELETE CASCADE,
    CONSTRAINT fk_ur_role FOREIGN KEY (role_id)
        REFERENCES roles (role_id) ON DELETE CASCADE,
    CONSTRAINT fk_ur_asignado_por FOREIGN KEY (asignado_por)
        REFERENCES usuarios (usuario_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 4. EMPLEADOS ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS employees (
    employee_id   INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    full_name     VARCHAR(150)    NOT NULL,
    document_id   VARCHAR(50)         NULL,
    embedding     BLOB                NULL,
    is_active     TINYINT(1)      NOT NULL DEFAULT 1,
    registered_by INT UNSIGNED        NULL,
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (employee_id),
    UNIQUE KEY uq_document (document_id),
    CONSTRAINT fk_emp_usuario FOREIGN KEY (registered_by)
        REFERENCES usuarios (usuario_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 5. REGISTRO DE ACCESOS ────────────────────────────────────
CREATE TABLE IF NOT EXISTS access_logs (
    log_id        INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    employee_id   INT UNSIGNED        NULL,
    access_result ENUM('GRANTED','DENIED') NOT NULL,
    confidence    FLOAT               NULL,
    liveness      ENUM('REAL','SPOOFING','UNKNOWN') NOT NULL DEFAULT 'UNKNOWN',
    snapshot_img  MEDIUMBLOB          NULL,
    event_time    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (log_id),
    KEY idx_log_employee (employee_id),
    KEY idx_log_time     (event_time),
    CONSTRAINT fk_log_employee FOREIGN KEY (employee_id)
        REFERENCES employees (employee_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 6. ALERTAS DE SEGURIDAD ───────────────────────────────────
CREATE TABLE IF NOT EXISTS security_alerts (
    alert_id      INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    log_id        INT UNSIGNED        NULL,
    alert_type    ENUM(
                    'SPOOFING_ATTEMPT',
                    'UNKNOWN_FACE',
                    'MULTIPLE_FAILURES',
                    'FORCED_ACCESS'
                  ) NOT NULL,
    severity      ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL DEFAULT 'MEDIUM',
    description   TEXT                NULL,
    resolved      TINYINT(1)      NOT NULL DEFAULT 0,
    resolved_by   INT UNSIGNED        NULL,
    resolved_at   DATETIME            NULL,
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (alert_id),
    KEY idx_alert_type     (alert_type),
    KEY idx_alert_resolved (resolved),
    CONSTRAINT fk_alert_log      FOREIGN KEY (log_id)
        REFERENCES access_logs (log_id) ON DELETE SET NULL,
    CONSTRAINT fk_alert_resolver FOREIGN KEY (resolved_by)
        REFERENCES usuarios (usuario_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 7. AUDITORÍA DE CAMBIOS ───────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id      INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    usuario_id    INT UNSIGNED        NULL,
    action        VARCHAR(80)     NOT NULL,
    target_table  VARCHAR(80)         NULL,
    target_id     INT UNSIGNED        NULL,
    detail        JSON                NULL,
    ip_address    VARCHAR(45)         NULL,
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (audit_id),
    KEY idx_audit_usuario (usuario_id),
    KEY idx_audit_action  (action),
    KEY idx_audit_time    (created_at),
    CONSTRAINT fk_audit_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios (usuario_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── SEEDS ────────────────────────────────────────────────────
INSERT IGNORE INTO roles (name, description)
VALUES ('admin', 'Administrador con acceso completo al sistema');

INSERT IGNORE INTO usuarios (full_name, email, password_hash)
VALUES (
    'Administrador',
    'admin@admin.com',
    'scrypt:32768:8:1$2V7hkBilDTTHhClz$12e84315915768b906340ebde2745131538a7c46cf777a856343c5bb8fc992b3e443cfa19a5992fb5e7daee5937133bf30dc94f0918d60c66d3321a6268aa362'
);

INSERT IGNORE INTO usuarios_roles (usuario_id, role_id)
SELECT u.usuario_id, r.role_id
FROM usuarios u, roles r
WHERE u.email = 'admin@admin.com' AND r.name = 'admin';

SET FOREIGN_KEY_CHECKS = 1;
