from collections.abc import Mapping, Sequence
import hashlib
import json
import secrets

from sqlalchemy import create_engine, text

from app.config import settings
from app.constants import MECANICO_ROLE, SECRETARIA_ROLE


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": settings.postgres_connect_timeout},
)


CREATE_REGISTROS_TALLER_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS registros_taller (
        id BIGSERIAL PRIMARY KEY,
        nombre_taller VARCHAR(160) NOT NULL,
        contact_name VARCHAR(160) NOT NULL,
        phone VARCHAR(40) NOT NULL,
        email VARCHAR(160) NOT NULL,
        zone VARCHAR(120) NOT NULL,
        specialty VARCHAR(120) NOT NULL,
        approval_status VARCHAR(30) NOT NULL DEFAULT 'pendiente',
        password_hash VARCHAR(255),
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        timezone VARCHAR(120),
        utc_offset_minutes INTEGER,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

CREATE_SUCURSALES_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS sucursales (
        id BIGSERIAL PRIMARY KEY,
        nombre VARCHAR(160) NOT NULL,
        direccion VARCHAR(255) NOT NULL,
        zona VARCHAR(120),
        telefono VARCHAR(40),
        email VARCHAR(160),
        latitud DOUBLE PRECISION,
        longitud DOUBLE PRECISION,
        horario_atencion VARCHAR(160),
        responsable VARCHAR(160),
        estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
        fecha_registro TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        fecha_modificacion TIMESTAMPTZ,
        CONSTRAINT sucursales_estado_check CHECK (estado IN ('ACTIVO', 'INACTIVO'))
    )
    """
)

CREATE_MECANICOS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS mecanicos (
        id BIGSERIAL PRIMARY KEY,
        taller_id BIGINT REFERENCES registros_taller(id) ON DELETE CASCADE,
        sucursal_id BIGINT REFERENCES sucursales(id) ON DELETE SET NULL,
        full_name VARCHAR(160) NOT NULL,
        phone VARCHAR(40) NOT NULL,
        email VARCHAR(160) NOT NULL DEFAULT '',
        specialty VARCHAR(120) NOT NULL,
        status VARCHAR(30) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

CREATE_CLIENTES_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS clientes (
        id BIGSERIAL PRIMARY KEY,
        identity_card VARCHAR(40) NOT NULL UNIQUE,
        full_name VARCHAR(160) NOT NULL,
        email VARCHAR(160) NOT NULL UNIQUE,
        phone VARCHAR(40) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(40) NOT NULL DEFAULT 'client',
        status VARCHAR(30) NOT NULL DEFAULT 'active',
        accepted_terms BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

CREATE_VEHICULOS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS vehiculos (
        id BIGSERIAL PRIMARY KEY,
        cliente_id BIGINT REFERENCES clientes(id) ON DELETE CASCADE,
        brand VARCHAR(120) NOT NULL,
        model VARCHAR(120) NOT NULL,
        year INTEGER NOT NULL,
        plate VARCHAR(40) NOT NULL UNIQUE,
        color VARCHAR(80) NOT NULL,
        is_primary BOOLEAN NOT NULL DEFAULT FALSE,
        photo_path VARCHAR(255),
        photo_url VARCHAR(255),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

CREATE_REPORTES_EMERGENCIA_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS reportes_emergencia (
        id BIGSERIAL PRIMARY KEY,
        cliente_id BIGINT REFERENCES clientes(id) ON DELETE SET NULL,
        vehiculo_id BIGINT,
        vehiculo_nombre VARCHAR(160) NOT NULL,
        vehiculo_placa VARCHAR(40) NOT NULL,
        problem_type VARCHAR(120) NOT NULL,
        price INTEGER,
        estado_emergencia VARCHAR(30) NOT NULL DEFAULT 'pendiente',
        problem_type_standardized VARCHAR(120),
        photo_problem_type_standardized VARCHAR(120),
        photo_classification_confidence DOUBLE PRECISION,
        photo_classification_error TEXT,
        description TEXT,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        address VARCHAR(255),
        zone VARCHAR(120),
        taller_cercano_id BIGINT,
        taller_cercano_nombre VARCHAR(160),
        taller_cercano_especialidad VARCHAR(120),
        taller_cercano_zona VARCHAR(120),
        taller_cercano_distancia_metros DOUBLE PRECISION,
        audio_duration_seconds DOUBLE PRECISION,
        audio_transcript TEXT,
        audio_transcript_status VARCHAR(30),
        audio_transcript_error TEXT,
        photo_paths TEXT NOT NULL DEFAULT '[]',
        photo_urls TEXT NOT NULL DEFAULT '[]',
        audio_path VARCHAR(255),
        audio_url VARCHAR(255),
        rejection_reason TEXT,
        rejected_at TIMESTAMPTZ,
        rejected_by_user_id BIGINT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

CREATE_ASIGNACIONES_EMERGENCIA_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS asignaciones_emergencia (
        id BIGSERIAL PRIMARY KEY,
        reporte_emergencia_id BIGINT NOT NULL UNIQUE REFERENCES reportes_emergencia(id) ON DELETE CASCADE,
        taller_id BIGINT NOT NULL REFERENCES registros_taller(id) ON DELETE CASCADE,
        mecanico_id BIGINT NOT NULL REFERENCES mecanicos(id) ON DELETE RESTRICT,
        estado_asignacion VARCHAR(30) NOT NULL DEFAULT 'asignado',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

CREATE_EMERGENCY_TRACKING_EVENTS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS seguimiento_emergencia_tracking (
        id BIGSERIAL PRIMARY KEY,
        emergencia_id BIGINT NOT NULL REFERENCES reportes_emergencia(id) ON DELETE CASCADE,
        mecanico_id BIGINT NOT NULL REFERENCES mecanicos(id) ON DELETE RESTRICT,
        latitud DOUBLE PRECISION NOT NULL,
        longitud DOUBLE PRECISION NOT NULL,
        heading DOUBLE PRECISION,
        speed DOUBLE PRECISION,
        event_type VARCHAR(30) NOT NULL DEFAULT 'moving',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT seguimiento_emergencia_tracking_event_type_check
            CHECK (event_type IN ('started', 'moving', 'arrived', 'cancelled'))
    )
    """
)

CREATE_TOKENS_FCM_DISPOSITIVO_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS tokens_fcm_dispositivo (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        fcm_token TEXT NOT NULL UNIQUE,
        platform VARCHAR(40) NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

CREATE_NOTIFICACIONES_CLIENTE_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS notificaciones_cliente (
        id BIGSERIAL PRIMARY KEY,
        cliente_id BIGINT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
        emergencia_id BIGINT REFERENCES reportes_emergencia(id) ON DELETE SET NULL,
        tipo VARCHAR(50) NOT NULL,
        titulo VARCHAR(160) NOT NULL,
        mensaje TEXT NOT NULL,
        metadata JSONB,
        leida BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        read_at TIMESTAMPTZ
    )
    """
)

CREATE_TOKENS_RECUPERACION_PASSWORD_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS tokens_recuperacion_password (
        id BIGSERIAL PRIMARY KEY,
        account_type VARCHAR(40) NOT NULL,
        account_id BIGINT NOT NULL,
        token_hash VARCHAR(64) NOT NULL UNIQUE,
        expires_at TIMESTAMPTZ NOT NULL,
        used_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

CREATE_RECEPCION_CLIENTES_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS clientes_recepcion (
        id BIGSERIAL PRIMARY KEY,
        full_name VARCHAR(160) NOT NULL,
        identity_card VARCHAR(40) NOT NULL UNIQUE,
        phone VARCHAR(40) NOT NULL,
        email VARCHAR(160) UNIQUE,
        address VARCHAR(255),
        mobile_client_id BIGINT REFERENCES clientes(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

CREATE_RECEPCION_VEHICULOS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS vehiculos_recepcion (
        id BIGSERIAL PRIMARY KEY,
        cliente_id BIGINT NOT NULL REFERENCES clientes_recepcion(id) ON DELETE CASCADE,
        plate VARCHAR(40) NOT NULL UNIQUE,
        brand VARCHAR(120) NOT NULL,
        model VARCHAR(120) NOT NULL,
        year INTEGER NOT NULL CHECK (year BETWEEN 1900 AND 2100),
        color VARCHAR(80) NOT NULL,
        vin VARCHAR(80),
        engine_number VARCHAR(80),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

CREATE_RECEPCION_FICHAS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS fichas_recepcion (
        id BIGSERIAL PRIMARY KEY,
        codigo_ficha VARCHAR(40) NOT NULL UNIQUE,
        cliente_id BIGINT NOT NULL REFERENCES clientes_recepcion(id) ON DELETE RESTRICT,
        vehiculo_id BIGINT NOT NULL REFERENCES vehiculos_recepcion(id) ON DELETE RESTRICT,
        emergencia_id BIGINT REFERENCES reportes_emergencia(id) ON DELETE SET NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'registrada',
        fecha_recepcion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        kilometraje INTEGER,
        nivel_combustible VARCHAR(30),
        recepcionado_por_user_id BIGINT REFERENCES clientes(id) ON DELETE RESTRICT,
        recepcionado_por_role VARCHAR(40) NOT NULL,
        assigned_mechanic_id BIGINT REFERENCES clientes(id) ON DELETE SET NULL,
        observaciones_generales TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT fichas_recepcion_status_check
            CHECK (status IN ('registrada', 'en_diagnostico', 'en_trabajo', 'finalizada', 'entregada')),
        CONSTRAINT fichas_recepcion_kilometraje_check
            CHECK (kilometraje IS NULL OR kilometraje >= 0),
        CONSTRAINT fichas_recepcion_recepcionado_role_check
            CHECK (recepcionado_por_role IN ('admin', 'secretaria')),
        CONSTRAINT fichas_recepcion_nivel_combustible_check
            CHECK (nivel_combustible IS NULL OR nivel_combustible IN ('vacio', '1/4', '1/2', '3/4', 'lleno'))
    )
    """
)

CREATE_RECEPCION_ACCESORIOS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS accesorios_recepcion (
        id BIGSERIAL PRIMARY KEY,
        ficha_id BIGINT NOT NULL REFERENCES fichas_recepcion(id) ON DELETE CASCADE,
        name VARCHAR(120) NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
        notes VARCHAR(255)
    )
    """
)

CREATE_RECEPCION_PROBLEMAS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS problemas_recepcion (
        id BIGSERIAL PRIMARY KEY,
        ficha_id BIGINT NOT NULL REFERENCES fichas_recepcion(id) ON DELETE CASCADE,
        description TEXT NOT NULL,
        priority VARCHAR(20),
        reported_by VARCHAR(20) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT problemas_recepcion_priority_check
            CHECK (priority IS NULL OR priority IN ('baja', 'media', 'alta')),
        CONSTRAINT problemas_recepcion_reported_by_check
            CHECK (reported_by IN ('cliente', 'secretaria'))
    )
    """
)

CREATE_RECEPCION_DIAGNOSTICOS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS diagnosticos_recepcion (
        id BIGSERIAL PRIMARY KEY,
        ficha_id BIGINT NOT NULL REFERENCES fichas_recepcion(id) ON DELETE CASCADE,
        mechanic_id BIGINT NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
        diagnostic_text TEXT NOT NULL,
        estimated_work TEXT,
        estimated_cost NUMERIC(10,2),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT diagnosticos_recepcion_estimated_cost_check
            CHECK (estimated_cost IS NULL OR estimated_cost >= 0)
    )
    """
)

CREATE_RECEPCION_OBSERVACIONES_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS observaciones_recepcion (
        id BIGSERIAL PRIMARY KEY,
        ficha_id BIGINT NOT NULL REFERENCES fichas_recepcion(id) ON DELETE CASCADE,
        mechanic_id BIGINT NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
        observation_text TEXT NOT NULL,
        work_status VARCHAR(30),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT observaciones_recepcion_work_status_check
            CHECK (work_status IS NULL OR work_status IN ('pendiente', 'en_proceso', 'pausado', 'completado'))
    )
    """
)

INSERT_RECEPCION_CLIENTE_SQL = text(
    """
    INSERT INTO clientes_recepcion (
        full_name,
        identity_card,
        phone,
        email,
        address,
        mobile_client_id
    )
    VALUES (
        :full_name,
        :identity_card,
        :phone,
        :email,
        :address,
        :mobile_client_id
    )
    RETURNING
        id,
        full_name,
        identity_card,
        phone,
        email,
        address,
        mobile_client_id,
        created_at,
        updated_at
    """
)

UPDATE_RECEPCION_CLIENTE_SQL = text(
    """
    UPDATE clientes_recepcion
    SET
        full_name = :full_name,
        identity_card = :identity_card,
        phone = :phone,
        email = :email,
        address = :address,
        mobile_client_id = :mobile_client_id,
        updated_at = NOW()
    WHERE id = :id
    RETURNING
        id,
        full_name,
        identity_card,
        phone,
        email,
        address,
        mobile_client_id,
        created_at,
        updated_at
    """
)

GET_RECEPCION_CLIENTE_BY_MOBILE_CLIENT_ID_SQL = text(
    """
    SELECT
        id,
        full_name,
        identity_card,
        phone,
        email,
        address,
        mobile_client_id,
        created_at,
        updated_at
    FROM clientes_recepcion
    WHERE mobile_client_id = :mobile_client_id
    ORDER BY updated_at DESC, id DESC
    LIMIT 1
    """
)

GET_RECEPCION_CLIENTE_BY_IDENTITY_CARD_SQL = text(
    """
    SELECT
        id,
        full_name,
        identity_card,
        phone,
        email,
        address,
        mobile_client_id,
        created_at,
        updated_at
    FROM clientes_recepcion
    WHERE identity_card = :identity_card
    LIMIT 1
    """
)

INSERT_RECEPCION_VEHICULO_SQL = text(
    """
    INSERT INTO vehiculos_recepcion (
        cliente_id,
        plate,
        brand,
        model,
        year,
        color,
        vin,
        engine_number
    )
    VALUES (
        :cliente_id,
        :plate,
        :brand,
        :model,
        :year,
        :color,
        :vin,
        :engine_number
    )
    RETURNING
        id,
        cliente_id,
        plate,
        brand,
        model,
        year,
        color,
        vin,
        engine_number,
        created_at,
        updated_at
    """
)

UPDATE_RECEPCION_VEHICULO_SQL = text(
    """
    UPDATE vehiculos_recepcion
    SET
        plate = :plate,
        brand = :brand,
        model = :model,
        year = :year,
        color = :color,
        vin = :vin,
        engine_number = :engine_number,
        updated_at = NOW()
    WHERE id = :id
    RETURNING
        id,
        cliente_id,
        plate,
        brand,
        model,
        year,
        color,
        vin,
        engine_number,
        created_at,
        updated_at
    """
)

GET_RECEPCION_VEHICULO_BY_PLATE_SQL = text(
    """
    SELECT
        id,
        cliente_id,
        plate,
        brand,
        model,
        year,
        color,
        vin,
        engine_number,
        created_at,
        updated_at
    FROM vehiculos_recepcion
    WHERE plate = :plate
    LIMIT 1
    """
)

INSERT_RECEPCION_FICHA_SQL = text(
    """
    INSERT INTO fichas_recepcion (
        codigo_ficha,
        cliente_id,
        vehiculo_id,
        emergencia_id,
        status,
        fecha_recepcion,
        kilometraje,
        nivel_combustible,
        recepcionado_por_user_id,
        recepcionado_por_role,
        assigned_mechanic_id,
        observaciones_generales
    )
    VALUES (
        :codigo_ficha,
        :cliente_id,
        :vehiculo_id,
        :emergencia_id,
        :status,
        COALESCE(:fecha_recepcion, NOW()),
        :kilometraje,
        :nivel_combustible,
        :recepcionado_por_user_id,
        :recepcionado_por_role,
        :assigned_mechanic_id,
        :observaciones_generales
    )
    RETURNING
        id,
        codigo_ficha,
        cliente_id,
        vehiculo_id,
        emergencia_id,
        status,
        fecha_recepcion,
        kilometraje,
        nivel_combustible,
        recepcionado_por_user_id,
        recepcionado_por_role,
        assigned_mechanic_id,
        observaciones_generales,
        created_at,
        updated_at
    """
)

UPDATE_RECEPCION_FICHA_SQL = text(
    """
    UPDATE fichas_recepcion
    SET
        codigo_ficha = :codigo_ficha,
        emergencia_id = :emergencia_id,
        status = :status,
        fecha_recepcion = COALESCE(:fecha_recepcion, fecha_recepcion),
        kilometraje = :kilometraje,
        nivel_combustible = :nivel_combustible,
        assigned_mechanic_id = :assigned_mechanic_id,
        observaciones_generales = :observaciones_generales,
        updated_at = NOW()
    WHERE id = :id
    RETURNING
        id,
        codigo_ficha,
        cliente_id,
        vehiculo_id,
        emergencia_id,
        status,
        fecha_recepcion,
        kilometraje,
        nivel_combustible,
        recepcionado_por_user_id,
        recepcionado_por_role,
        assigned_mechanic_id,
        observaciones_generales,
        created_at,
        updated_at
    """
)

INSERT_RECEPCION_ACCESORIO_SQL = text(
    """
    INSERT INTO accesorios_recepcion (
        ficha_id,
        name,
        quantity,
        notes
    )
    VALUES (
        :ficha_id,
        :name,
        :quantity,
        :notes
    )
    RETURNING id, ficha_id, name, quantity, notes
    """
)

DELETE_RECEPCION_ACCESORIOS_SQL = text("DELETE FROM accesorios_recepcion WHERE ficha_id = :ficha_id")

LIST_RECEPCION_ACCESORIOS_SQL = text(
    """
    SELECT id, ficha_id, name, quantity, notes
    FROM accesorios_recepcion
    WHERE ficha_id = :ficha_id
    ORDER BY id ASC
    """
)

INSERT_RECEPCION_PROBLEMA_SQL = text(
    """
    INSERT INTO problemas_recepcion (
        ficha_id,
        description,
        priority,
        reported_by
    )
    VALUES (
        :ficha_id,
        :description,
        :priority,
        :reported_by
    )
    RETURNING id, ficha_id, description, priority, reported_by, created_at
    """
)

DELETE_RECEPCION_PROBLEMAS_SQL = text("DELETE FROM problemas_recepcion WHERE ficha_id = :ficha_id")

LIST_RECEPCION_PROBLEMAS_SQL = text(
    """
    SELECT id, ficha_id, description, priority, reported_by, created_at
    FROM problemas_recepcion
    WHERE ficha_id = :ficha_id
    ORDER BY id ASC
    """
)

INSERT_RECEPCION_DIAGNOSTICO_SQL = text(
    """
    INSERT INTO diagnosticos_recepcion (
        ficha_id,
        mechanic_id,
        diagnostic_text,
        estimated_work,
        estimated_cost
    )
    VALUES (
        :ficha_id,
        :mechanic_id,
        :diagnostic_text,
        :estimated_work,
        :estimated_cost
    )
    RETURNING
        id,
        ficha_id,
        mechanic_id,
        diagnostic_text,
        estimated_work,
        estimated_cost,
        created_at,
        updated_at
    """
)

LIST_RECEPCION_DIAGNOSTICOS_SQL = text(
    """
    SELECT
        dr.id,
        dr.ficha_id,
        dr.mechanic_id,
        dr.diagnostic_text,
        dr.estimated_work,
        dr.estimated_cost,
        dr.created_at,
        dr.updated_at,
        c.full_name AS mechanic_name
    FROM diagnosticos_recepcion dr
    LEFT JOIN clientes c ON c.id = dr.mechanic_id
    WHERE dr.ficha_id = :ficha_id
    ORDER BY dr.created_at DESC, dr.id DESC
    """
)

INSERT_RECEPCION_OBSERVACION_SQL = text(
    """
    INSERT INTO observaciones_recepcion (
        ficha_id,
        mechanic_id,
        observation_text,
        work_status
    )
    VALUES (
        :ficha_id,
        :mechanic_id,
        :observation_text,
        :work_status
    )
    RETURNING
        id,
        ficha_id,
        mechanic_id,
        observation_text,
        work_status,
        created_at
    """
)

LIST_RECEPCION_OBSERVACIONES_SQL = text(
    """
    SELECT
        orr.id,
        orr.ficha_id,
        orr.mechanic_id,
        orr.observation_text,
        orr.work_status,
        orr.created_at,
        c.full_name AS mechanic_name
    FROM observaciones_recepcion orr
    LEFT JOIN clientes c ON c.id = orr.mechanic_id
    WHERE orr.ficha_id = :ficha_id
    ORDER BY orr.created_at DESC, orr.id DESC
    """
)

LIST_RECEPCION_RECORDS_SQL = text(
    """
    SELECT
        fr.id,
        fr.codigo_ficha,
        fr.emergencia_id,
        fr.status,
        fr.fecha_recepcion,
        fr.kilometraje,
        fr.nivel_combustible,
        fr.assigned_mechanic_id,
        cr.id AS reception_client_id,
        cr.full_name AS client_full_name,
        cr.identity_card AS client_identity_card,
        cr.phone AS client_phone,
        cr.email AS client_email,
        cr.mobile_client_id,
        vr.id AS vehicle_id,
        vr.plate,
        vr.brand,
        vr.model,
        vr.year,
        vr.color,
        mech.full_name AS assigned_mechanic_name,
        fr.updated_at
    FROM fichas_recepcion fr
    JOIN clientes_recepcion cr ON cr.id = fr.cliente_id
    JOIN vehiculos_recepcion vr ON vr.id = fr.vehiculo_id
    LEFT JOIN clientes mech ON mech.id = fr.assigned_mechanic_id
    WHERE (
        CAST(:status AS VARCHAR(30)) IS NULL
        OR fr.status = CAST(:status AS VARCHAR(30))
    )
      AND (
        CAST(:plate AS VARCHAR(40)) IS NULL
        OR vr.plate ILIKE '%' || CAST(:plate AS VARCHAR(40)) || '%'
    )
      AND (
        CAST(:codigo_ficha AS VARCHAR(40)) IS NULL
        OR fr.codigo_ficha ILIKE '%' || CAST(:codigo_ficha AS VARCHAR(40)) || '%'
    )
      AND (
        CAST(:identity_card AS VARCHAR(40)) IS NULL
        OR cr.identity_card ILIKE '%' || CAST(:identity_card AS VARCHAR(40)) || '%'
    )
      AND (
        CAST(:assigned_mechanic_id AS BIGINT) IS NULL
        OR fr.assigned_mechanic_id = CAST(:assigned_mechanic_id AS BIGINT)
    )
      AND (
        CAST(:visible_mechanic_id AS BIGINT) IS NULL
        OR fr.assigned_mechanic_id IS NULL
        OR fr.assigned_mechanic_id = CAST(:visible_mechanic_id AS BIGINT)
    )
    ORDER BY fr.created_at DESC, fr.id DESC
    LIMIT :limit OFFSET :offset
    """
)

COUNT_RECEPCION_RECORDS_SQL = text(
    """
    SELECT COUNT(*) AS total
    FROM fichas_recepcion fr
    JOIN clientes_recepcion cr ON cr.id = fr.cliente_id
    JOIN vehiculos_recepcion vr ON vr.id = fr.vehiculo_id
    WHERE (
        CAST(:status AS VARCHAR(30)) IS NULL
        OR fr.status = CAST(:status AS VARCHAR(30))
    )
      AND (
        CAST(:plate AS VARCHAR(40)) IS NULL
        OR vr.plate ILIKE '%' || CAST(:plate AS VARCHAR(40)) || '%'
    )
      AND (
        CAST(:codigo_ficha AS VARCHAR(40)) IS NULL
        OR fr.codigo_ficha ILIKE '%' || CAST(:codigo_ficha AS VARCHAR(40)) || '%'
    )
      AND (
        CAST(:identity_card AS VARCHAR(40)) IS NULL
        OR cr.identity_card ILIKE '%' || CAST(:identity_card AS VARCHAR(40)) || '%'
    )
      AND (
        CAST(:assigned_mechanic_id AS BIGINT) IS NULL
        OR fr.assigned_mechanic_id = CAST(:assigned_mechanic_id AS BIGINT)
    )
      AND (
        CAST(:visible_mechanic_id AS BIGINT) IS NULL
        OR fr.assigned_mechanic_id IS NULL
        OR fr.assigned_mechanic_id = CAST(:visible_mechanic_id AS BIGINT)
    )
    """
)

GET_RECEPCION_RECORD_SQL = text(
    """
    SELECT
        fr.id,
        fr.codigo_ficha,
        fr.emergencia_id,
        fr.status,
        fr.fecha_recepcion,
        fr.kilometraje,
        fr.nivel_combustible,
        fr.recepcionado_por_user_id,
        fr.recepcionado_por_role,
        fr.assigned_mechanic_id,
        fr.observaciones_generales,
        fr.created_at,
        fr.updated_at,
        cr.id AS reception_client_id,
        cr.full_name AS client_full_name,
        cr.identity_card AS client_identity_card,
        cr.phone AS client_phone,
        cr.email AS client_email,
        cr.address AS client_address,
        cr.mobile_client_id,
        vr.id AS vehicle_id,
        vr.plate,
        vr.brand,
        vr.model,
        vr.year,
        vr.color,
        vr.vin,
        vr.engine_number,
        mech.full_name AS assigned_mechanic_name
    FROM fichas_recepcion fr
    JOIN clientes_recepcion cr ON cr.id = fr.cliente_id
    JOIN vehiculos_recepcion vr ON vr.id = fr.vehiculo_id
    LEFT JOIN clientes mech ON mech.id = fr.assigned_mechanic_id
    WHERE fr.id = :id
    """
)

GET_RECEPCION_RECORD_BY_EMERGENCY_SQL = text(
    """
    SELECT id
    FROM fichas_recepcion
    WHERE emergencia_id = :emergency_id
    ORDER BY created_at DESC, id DESC
    LIMIT 1
    """
)

GET_ACTIVE_RECEPCION_BY_EMERGENCY_SQL = text(
    """
    SELECT id
    FROM fichas_recepcion
    WHERE emergencia_id = :emergency_id
      AND status IN ('registrada', 'en_diagnostico', 'en_trabajo', 'finalizada')
    ORDER BY created_at DESC, id DESC
    LIMIT 1
    """
)

GET_RECEPCION_IDS_SQL = text(
    """
    SELECT id, cliente_id, vehiculo_id
    FROM fichas_recepcion
    WHERE id = :id
    """
)

GET_RECEPCION_STATUS_SQL = text(
    """
    SELECT
        fr.id AS ficha_id,
        fr.codigo_ficha,
        fr.status,
        fr.updated_at,
        vr.brand,
        vr.model,
        vr.year,
        vr.plate,
        cr.mobile_client_id,
        latest_diag.diagnostic_text AS last_diagnostic,
        latest_obs.observation_text AS last_observation
    FROM fichas_recepcion fr
    JOIN clientes_recepcion cr ON cr.id = fr.cliente_id
    JOIN vehiculos_recepcion vr ON vr.id = fr.vehiculo_id
    LEFT JOIN LATERAL (
        SELECT diagnostic_text
        FROM diagnosticos_recepcion
        WHERE ficha_id = fr.id
        ORDER BY created_at DESC, id DESC
        LIMIT 1
    ) latest_diag ON TRUE
    LEFT JOIN LATERAL (
        SELECT observation_text
        FROM observaciones_recepcion
        WHERE ficha_id = fr.id
        ORDER BY created_at DESC, id DESC
        LIMIT 1
    ) latest_obs ON TRUE
    WHERE fr.id = :id
    """
)

INSERT_WORKSHOP_SQL = text(
    """
    INSERT INTO registros_taller (
        nombre_taller,
        contact_name,
        phone,
        email,
        zone,
        specialty,
        approval_status,
        password_hash,
        latitude,
        longitude,
        timezone,
        utc_offset_minutes
    )
    VALUES (
        :workshop_name,
        :contact_name,
        :phone,
        :email,
        :zone,
        :specialty,
        :approval_status,
        :password_hash,
        :latitude,
        :longitude,
        :timezone,
        :utc_offset_minutes
    )
    RETURNING
        id,
        nombre_taller AS workshop_name,
        contact_name,
        phone,
        email,
        zone,
        specialty,
        approval_status,
        password_hash,
        latitude,
        longitude,
        timezone,
        utc_offset_minutes,
        created_at
    """
)

LIST_WORKSHOPS_SQL = text(
    """
    SELECT
        id,
        nombre_taller AS workshop_name,
        contact_name,
        phone,
        email,
        zone,
        specialty,
        approval_status,
        password_hash,
        latitude,
        longitude,
        timezone,
        utc_offset_minutes,
        created_at
    FROM registros_taller
    ORDER BY created_at DESC, id DESC
    """
)

UPDATE_WORKSHOP_SQL = text(
    """
    UPDATE registros_taller
    SET
        nombre_taller = :workshop_name,
        contact_name = :contact_name,
        phone = :phone,
        email = :email,
        zone = :zone,
        specialty = :specialty,
        approval_status = COALESCE(:approval_status, approval_status),
        password_hash = COALESCE(:password_hash, password_hash),
        latitude = :latitude,
        longitude = :longitude,
        timezone = :timezone,
        utc_offset_minutes = :utc_offset_minutes
    WHERE id = :id
    RETURNING
        id,
        nombre_taller AS workshop_name,
        contact_name,
        phone,
        email,
        zone,
        specialty,
        approval_status,
        password_hash,
        latitude,
        longitude,
        timezone,
        utc_offset_minutes,
        created_at
    """
)

UPDATE_WORKSHOP_APPROVAL_STATUS_SQL = text(
    """
    UPDATE registros_taller
    SET
        approval_status = :approval_status,
        password_hash = COALESCE(:password_hash, password_hash)
    WHERE id = :id
    RETURNING
        id,
        nombre_taller AS workshop_name,
        contact_name,
        phone,
        email,
        zone,
        specialty,
        approval_status,
        password_hash,
        latitude,
        longitude,
        timezone,
        utc_offset_minutes,
        created_at
    """
)

UPDATE_WORKSHOP_PASSWORD_SQL = text(
    """
    UPDATE registros_taller
    SET
        password_hash = :password_hash
    WHERE id = :id
    RETURNING
        id,
        nombre_taller AS workshop_name,
        contact_name,
        phone,
        email,
        zone,
        specialty,
        approval_status,
        password_hash,
        latitude,
        longitude,
        timezone,
        utc_offset_minutes,
        created_at
    """
)

GET_WORKSHOP_BY_EMAIL_SQL = text(
    """
    SELECT
        id,
        nombre_taller AS workshop_name,
        contact_name,
        phone,
        email,
        zone,
        specialty,
        approval_status,
        password_hash,
        latitude,
        longitude,
        timezone,
        utc_offset_minutes,
        created_at
    FROM registros_taller
    WHERE email = :email
    LIMIT 1
    """
)

GET_WORKSHOP_BY_ID_SQL = text(
    """
    SELECT
        id,
        nombre_taller AS workshop_name,
        contact_name,
        phone,
        email,
        zone,
        specialty,
        approval_status,
        password_hash,
        latitude,
        longitude,
        timezone,
        utc_offset_minutes,
        created_at
    FROM registros_taller
    WHERE id = :id
    LIMIT 1
    """
)

DELETE_WORKSHOP_SQL = text(
    """
    DELETE FROM registros_taller
    WHERE id = :id
    RETURNING id
    """
)

INSERT_SUCURSAL_SQL = text(
    """
    INSERT INTO sucursales (
        nombre,
        direccion,
        zona,
        telefono,
        email,
        latitud,
        longitud,
        horario_atencion,
        responsable,
        estado
    )
    VALUES (
        :nombre,
        :direccion,
        :zona,
        :telefono,
        :email,
        :latitud,
        :longitud,
        :horario_atencion,
        :responsable,
        :estado
    )
    RETURNING
        id,
        nombre,
        direccion,
        zona,
        telefono,
        email,
        latitud,
        longitud,
        horario_atencion,
        responsable,
        estado,
        fecha_registro,
        fecha_modificacion
    """
)

LIST_SUCURSALES_SQL = text(
    """
    SELECT
        s.id,
        s.nombre,
        s.direccion,
        s.zona,
        s.telefono,
        s.email,
        s.latitud,
        s.longitud,
        s.horario_atencion,
        s.responsable,
        s.estado,
        s.fecha_registro,
        s.fecha_modificacion,
        (
            SELECT COUNT(*)::INTEGER FROM mecanicos m
            WHERE m.sucursal_id = s.id
              AND LOWER(TRIM(m.status)) IN ('disponible', 'ocupado')
        ) AS mecanicos_activos_count,
        (
            SELECT COUNT(*)::INTEGER FROM secretarias sec
            WHERE sec.sucursal_id = s.id
              AND LOWER(TRIM(sec.status)) = 'activo'
        ) AS secretarias_activas_count
    FROM sucursales s
    WHERE (
        CAST(:estado AS VARCHAR(20)) IS NULL
        OR s.estado = CAST(:estado AS VARCHAR(20))
    )
    ORDER BY
        CASE WHEN s.estado = 'ACTIVO' THEN 0 ELSE 1 END,
        s.fecha_registro DESC,
        s.id DESC
    """
)

LIST_MOBILE_SUCURSALES_SQL = text(
    """
    SELECT
        s.id,
        s.nombre,
        s.direccion,
        s.zona,
        s.telefono,
        s.email,
        s.latitud,
        s.longitud,
        s.horario_atencion,
        s.responsable,
        s.estado,
        TRUE AS operativa,
        (
            SELECT COUNT(*)::INTEGER FROM mecanicos m
            WHERE m.sucursal_id = s.id
              AND LOWER(TRIM(m.status)) IN ('disponible', 'ocupado')
        ) AS mecanicos_activos_count,
        (
            SELECT COUNT(*)::INTEGER FROM secretarias sec
            WHERE sec.sucursal_id = s.id
              AND LOWER(TRIM(sec.status)) = 'activo'
        ) AS secretarias_activas_count
    FROM sucursales s
    WHERE s.estado = 'ACTIVO'
      AND s.latitud IS NOT NULL
      AND s.longitud IS NOT NULL
      AND EXISTS (
          SELECT 1 FROM mecanicos m
          WHERE m.sucursal_id = s.id
            AND LOWER(TRIM(m.status)) IN ('disponible', 'ocupado')
      )
      AND EXISTS (
          SELECT 1 FROM secretarias sec
          WHERE sec.sucursal_id = s.id
            AND LOWER(TRIM(sec.status)) = 'activo'
      )
    ORDER BY s.nombre ASC, s.id ASC
    """
)

GET_SUCURSAL_BY_ID_SQL = text(
    """
    SELECT
        id,
        nombre,
        direccion,
        zona,
        telefono,
        email,
        latitud,
        longitud,
        horario_atencion,
        responsable,
        estado,
        fecha_registro,
        fecha_modificacion
    FROM sucursales
    WHERE id = :id
    LIMIT 1
    """
)

UPDATE_SUCURSAL_SQL = text(
    """
    UPDATE sucursales
    SET
        nombre = :nombre,
        direccion = :direccion,
        zona = :zona,
        telefono = :telefono,
        email = :email,
        latitud = :latitud,
        longitud = :longitud,
        horario_atencion = :horario_atencion,
        responsable = :responsable,
        estado = :estado,
        fecha_modificacion = NOW()
    WHERE id = :id
    RETURNING
        id,
        nombre,
        direccion,
        zona,
        telefono,
        email,
        latitud,
        longitud,
        horario_atencion,
        responsable,
        estado,
        fecha_registro,
        fecha_modificacion
    """
)

UPDATE_SUCURSAL_ESTADO_SQL = text(
    """
    UPDATE sucursales
    SET
        estado = :estado,
        fecha_modificacion = NOW()
    WHERE id = :id
    RETURNING
        id,
        nombre,
        direccion,
        zona,
        telefono,
        email,
        latitud,
        longitud,
        horario_atencion,
        responsable,
        estado,
        fecha_registro,
        fecha_modificacion
    """
)

CREATE_SECRETARIAS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS secretarias (
        id BIGSERIAL PRIMARY KEY,
        cliente_id BIGINT NOT NULL UNIQUE REFERENCES clientes(id) ON DELETE CASCADE,
        sucursal_id BIGINT NOT NULL REFERENCES sucursales(id) ON DELETE RESTRICT,
        status VARCHAR(30) NOT NULL DEFAULT 'activo',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT secretarias_status_check CHECK (LOWER(TRIM(status)) IN ('activo', 'inactivo'))
    )
    """
)

LIST_SECRETARIAS_SQL = text(
    """
    SELECT
        sec.id,
        sec.cliente_id,
        sec.sucursal_id,
        sec.status,
        sec.created_at,
        sec.updated_at,
        c.full_name,
        c.phone,
        c.email,
        s.nombre AS sucursal_nombre,
        s.zona AS sucursal_zona,
        s.direccion AS sucursal_direccion,
        s.estado AS sucursal_estado
    FROM secretarias sec
    JOIN clientes c ON c.id = sec.cliente_id
    LEFT JOIN sucursales s ON s.id = sec.sucursal_id
    ORDER BY sec.updated_at DESC, sec.id DESC
    """
)

GET_SECRETARIA_BY_ID_SQL = text(
    """
    SELECT
        sec.id,
        sec.cliente_id,
        sec.sucursal_id,
        sec.status,
        sec.created_at,
        sec.updated_at,
        c.full_name,
        c.phone,
        c.email,
        s.nombre AS sucursal_nombre,
        s.zona AS sucursal_zona,
        s.direccion AS sucursal_direccion,
        s.estado AS sucursal_estado
    FROM secretarias sec
    JOIN clientes c ON c.id = sec.cliente_id
    LEFT JOIN sucursales s ON s.id = sec.sucursal_id
    WHERE sec.id = :id
    LIMIT 1
    """
)

GET_SECRETARIA_BY_CLIENTE_ID_SQL = text(
    """
    SELECT
        sec.id,
        sec.cliente_id,
        sec.sucursal_id,
        sec.status,
        sec.created_at,
        sec.updated_at,
        c.full_name,
        c.phone,
        c.email,
        s.nombre AS sucursal_nombre,
        s.zona AS sucursal_zona,
        s.direccion AS sucursal_direccion,
        s.estado AS sucursal_estado
    FROM secretarias sec
    JOIN clientes c ON c.id = sec.cliente_id
    LEFT JOIN sucursales s ON s.id = sec.sucursal_id
    WHERE sec.cliente_id = :cliente_id
    LIMIT 1
    """
)

UPDATE_SECRETARIA_STATUS_SQL = text(
    """
    UPDATE secretarias
    SET status = :status, updated_at = NOW()
    WHERE id = :id
    RETURNING id, cliente_id, sucursal_id, status, created_at, updated_at
    """
)

INSERT_MECANICO_SQL = text(
    """
    WITH inserted AS (
        INSERT INTO mecanicos (
            taller_id,
            sucursal_id,
            full_name,
            phone,
            email,
            specialty,
            status
        )
        VALUES (
            :workshop_id,
            :sucursal_id,
            :full_name,
            :phone,
            :email,
            :specialty,
            :status
        )
        RETURNING
            id,
            taller_id,
            sucursal_id,
            full_name,
            phone,
            email,
            specialty,
            status,
            created_at,
            updated_at
    )
    SELECT
        inserted.id,
        inserted.taller_id AS workshop_id,
        inserted.sucursal_id,
        inserted.full_name,
        inserted.phone,
        inserted.email,
        inserted.specialty,
        inserted.status,
        sucursales.nombre AS sucursal_nombre,
        sucursales.zona AS sucursal_zona,
        sucursales.direccion AS sucursal_direccion,
        inserted.created_at,
        inserted.updated_at
    FROM inserted
    LEFT JOIN sucursales ON sucursales.id = inserted.sucursal_id
    """
)

LIST_MECANICOS_SQL = text(
    """
    SELECT
        mecanicos.id,
        mecanicos.taller_id AS workshop_id,
        mecanicos.sucursal_id,
        mecanicos.full_name,
        mecanicos.phone,
        mecanicos.email,
        mecanicos.specialty,
        mecanicos.status,
        sucursales.nombre AS sucursal_nombre,
        sucursales.zona AS sucursal_zona,
        sucursales.direccion AS sucursal_direccion,
        mecanicos.created_at,
        mecanicos.updated_at
    FROM mecanicos
    LEFT JOIN sucursales ON sucursales.id = mecanicos.sucursal_id
    ORDER BY mecanicos.updated_at DESC, mecanicos.id DESC
    """
)

LIST_MECANICOS_BY_WORKSHOP_SQL = text(
    """
    SELECT
        mecanicos.id,
        mecanicos.taller_id AS workshop_id,
        mecanicos.sucursal_id,
        mecanicos.full_name,
        mecanicos.phone,
        mecanicos.email,
        mecanicos.specialty,
        mecanicos.status,
        sucursales.nombre AS sucursal_nombre,
        sucursales.zona AS sucursal_zona,
        sucursales.direccion AS sucursal_direccion,
        mecanicos.created_at,
        mecanicos.updated_at
    FROM mecanicos
    LEFT JOIN sucursales ON sucursales.id = mecanicos.sucursal_id
    WHERE mecanicos.taller_id = :workshop_id
    ORDER BY mecanicos.updated_at DESC, mecanicos.id DESC
    """
)

GET_MECANICO_SQL = text(
    """
    SELECT
        mecanicos.id,
        mecanicos.taller_id AS workshop_id,
        mecanicos.sucursal_id,
        mecanicos.full_name,
        mecanicos.phone,
        mecanicos.email,
        mecanicos.specialty,
        mecanicos.status,
        sucursales.nombre AS sucursal_nombre,
        sucursales.zona AS sucursal_zona,
        sucursales.direccion AS sucursal_direccion,
        mecanicos.created_at,
        mecanicos.updated_at
    FROM mecanicos
    LEFT JOIN sucursales ON sucursales.id = mecanicos.sucursal_id
    WHERE mecanicos.id = :id
    LIMIT 1
    """
)

GET_MECANICO_BY_WORKSHOP_SQL = text(
    """
    SELECT
        mecanicos.id,
        mecanicos.taller_id AS workshop_id,
        mecanicos.sucursal_id,
        mecanicos.full_name,
        mecanicos.phone,
        mecanicos.email,
        mecanicos.specialty,
        mecanicos.status,
        sucursales.nombre AS sucursal_nombre,
        sucursales.zona AS sucursal_zona,
        sucursales.direccion AS sucursal_direccion,
        mecanicos.created_at,
        mecanicos.updated_at
    FROM mecanicos
    LEFT JOIN sucursales ON sucursales.id = mecanicos.sucursal_id
    WHERE mecanicos.id = :id AND mecanicos.taller_id = :workshop_id
    LIMIT 1
    """
)

UPDATE_MECANICO_SQL = text(
    """
    WITH updated AS (
        UPDATE mecanicos
        SET
            taller_id = COALESCE(:workshop_id, taller_id),
            sucursal_id = :sucursal_id,
            full_name = :full_name,
            phone = :phone,
            email = :email,
            specialty = :specialty,
            status = :status,
            updated_at = NOW()
        WHERE id = :id
        RETURNING
            id,
            taller_id,
            sucursal_id,
            full_name,
            phone,
            email,
            specialty,
            status,
            created_at,
            updated_at
    )
    SELECT
        updated.id,
        updated.taller_id AS workshop_id,
        updated.sucursal_id,
        updated.full_name,
        updated.phone,
        updated.email,
        updated.specialty,
        updated.status,
        sucursales.nombre AS sucursal_nombre,
        sucursales.zona AS sucursal_zona,
        sucursales.direccion AS sucursal_direccion,
        updated.created_at,
        updated.updated_at
    FROM updated
    LEFT JOIN sucursales ON sucursales.id = updated.sucursal_id
    """
)

UPDATE_MECANICO_STATUS_SQL = text(
    """
    UPDATE mecanicos
    SET
        status = :status,
        updated_at = NOW()
    WHERE id = :id
    RETURNING
        id,
        taller_id AS workshop_id,
        full_name,
        phone,
        email,
        specialty,
        status,
        created_at,
        updated_at
    """
)

UPDATE_MECANICO_BY_WORKSHOP_SQL = text(
    """
    WITH updated AS (
        UPDATE mecanicos
        SET
            sucursal_id = :sucursal_id,
            full_name = :full_name,
            phone = :phone,
            email = :email,
            specialty = :specialty,
            status = :status,
            updated_at = NOW()
        WHERE id = :id AND taller_id = :workshop_id
        RETURNING
            id,
            taller_id,
            sucursal_id,
            full_name,
            phone,
            email,
            specialty,
            status,
            created_at,
            updated_at
    )
    SELECT
        updated.id,
        updated.taller_id AS workshop_id,
        updated.sucursal_id,
        updated.full_name,
        updated.phone,
        updated.email,
        updated.specialty,
        updated.status,
        sucursales.nombre AS sucursal_nombre,
        sucursales.zona AS sucursal_zona,
        sucursales.direccion AS sucursal_direccion,
        updated.created_at,
        updated.updated_at
    FROM updated
    LEFT JOIN sucursales ON sucursales.id = updated.sucursal_id
    """
)

COUNT_ACTIVE_SUCURSALES_SQL = text(
    """
    SELECT COUNT(*) AS total
    FROM sucursales
    WHERE estado = 'ACTIVO'
    """
)

DELETE_MECANICO_SQL = text(
    """
    DELETE FROM mecanicos
    WHERE id = :id
    RETURNING id
    """
)

DELETE_MECANICO_BY_WORKSHOP_SQL = text(
    """
    DELETE FROM mecanicos
    WHERE id = :id AND taller_id = :workshop_id
    RETURNING id
    """
)

INSERT_CLIENT_SQL = text(
    """
    INSERT INTO clientes (
        identity_card,
        full_name,
        email,
        phone,
        password_hash,
        role,
        status,
        accepted_terms
    )
    VALUES (
        :identity_card,
        :full_name,
        :email,
        :phone,
        :password_hash,
        :role,
        :status,
        :accepted_terms
    )
    RETURNING
        id,
        identity_card,
        full_name,
        email,
        phone,
        role,
        status,
        accepted_terms,
        created_at,
        updated_at
    """
)

UPDATE_CLIENT_SQL = text(
    """
    UPDATE clientes
    SET
        identity_card = :identity_card,
        full_name = :full_name,
        email = :email,
        phone = :phone,
        password_hash = COALESCE(:password_hash, password_hash),
        role = :role,
        status = :status,
        accepted_terms = :accepted_terms,
        updated_at = NOW()
    WHERE id = :id
    RETURNING
        id,
        identity_card,
        full_name,
        email,
        phone,
        role,
        status,
        accepted_terms,
        created_at,
        updated_at
    """
)

LIST_CLIENTS_SQL = text(
    """
    SELECT
        id,
        identity_card,
        full_name,
        email,
        phone,
        role,
        status,
        accepted_terms,
        created_at,
        updated_at
    FROM clientes
    ORDER BY created_at DESC, id DESC
    """
)

GET_CLIENT_BY_EMAIL_SQL = text(
    """
    SELECT
        id,
        identity_card,
        full_name,
        email,
        phone,
        password_hash,
        role,
        status,
        accepted_terms,
        created_at,
        updated_at
    FROM clientes
    WHERE email = :email
    LIMIT 1
    """
)

GET_CLIENT_BY_ID_SQL = text(
    """
    SELECT
        id,
        identity_card,
        full_name,
        email,
        phone,
        password_hash,
        role,
        status,
        accepted_terms,
        created_at,
        updated_at
    FROM clientes
    WHERE id = :id
    LIMIT 1
    """
)

UPDATE_CLIENT_STATUS_SQL = text(
    """
    UPDATE clientes
    SET
        status = :status,
        updated_at = NOW()
    WHERE id = :id
    RETURNING
        id,
        identity_card,
        full_name,
        email,
        phone,
        role,
        status,
        accepted_terms,
        created_at,
        updated_at
    """
)

UPDATE_CLIENT_PASSWORD_SQL = text(
    """
    UPDATE clientes
    SET
        password_hash = :password_hash,
        updated_at = NOW()
    WHERE id = :id
    RETURNING
        id,
        identity_card,
        full_name,
        email,
        phone,
        role,
        status,
        accepted_terms,
        created_at,
        updated_at
    """
)

DELETE_CLIENT_SQL = text(
    """
    DELETE FROM clientes
    WHERE id = :id
    RETURNING id
    """
)

DELETE_CLIENT_VEHICLES_SQL = text(
    """
    DELETE FROM vehiculos
    WHERE cliente_id = :client_id
    """
)

INSERT_VEHICLE_SQL = text(
    """
    INSERT INTO vehiculos (
        cliente_id,
        brand,
        model,
        year,
        plate,
        color,
        is_primary,
        photo_path,
        photo_url
    )
    VALUES (
        :client_id,
        :brand,
        :model,
        :year,
        :plate,
        :color,
        :is_primary,
        :photo_path,
        :photo_url
    )
    RETURNING
        id,
        cliente_id AS client_id,
        brand,
        model,
        year,
        plate,
        color,
        is_primary,
        photo_path,
        photo_url,
        created_at
    """
)

LIST_VEHICLES_SQL = text(
    """
    SELECT
        id,
        cliente_id AS client_id,
        brand,
        model,
        year,
        plate,
        color,
        is_primary,
        photo_path,
        photo_url,
        created_at
    FROM vehiculos
    WHERE cliente_id = :client_id
    ORDER BY created_at DESC, id DESC
    """
)

GET_VEHICLE_BY_ID_SQL = text(
    """
    SELECT
        id,
        cliente_id AS client_id,
        brand,
        model,
        year,
        plate,
        color,
        is_primary,
        photo_path,
        photo_url,
        created_at
    FROM vehiculos
    WHERE id = :id AND cliente_id = :client_id
    LIMIT 1
    """
)

GET_VEHICLE_BY_ANY_ID_SQL = text(
    """
    SELECT
        id,
        cliente_id AS client_id,
        brand,
        model,
        year,
        plate,
        color,
        is_primary,
        photo_path,
        photo_url,
        created_at
    FROM vehiculos
    WHERE id = :id
    LIMIT 1
    """
)

GET_VEHICLE_BY_CLIENT_AND_PLATE_SQL = text(
    """
    SELECT
        id,
        cliente_id AS client_id,
        brand,
        model,
        year,
        plate,
        color,
        is_primary,
        photo_path,
        photo_url,
        created_at
    FROM vehiculos
    WHERE cliente_id = :client_id AND plate = :plate
    LIMIT 1
    """
)

COUNT_CLIENT_VEHICLES_SQL = text(
    """
    SELECT COUNT(*)::BIGINT AS total
    FROM vehiculos
    WHERE cliente_id = :client_id
    """
)

UPDATE_VEHICLE_SQL = text(
    """
    UPDATE vehiculos
    SET
        cliente_id = :client_id,
        brand = :brand,
        model = :model,
        year = :year,
        plate = :plate,
        color = :color,
        is_primary = :is_primary,
        photo_path = :photo_path,
        photo_url = :photo_url
    WHERE id = :id AND cliente_id = :client_id
    RETURNING
        id,
        cliente_id AS client_id,
        brand,
        model,
        year,
        plate,
        color,
        is_primary,
        photo_path,
        photo_url,
        created_at
    """
)

DELETE_VEHICLE_SQL = text(
    """
    DELETE FROM vehiculos
    WHERE id = :id AND cliente_id = :client_id
    RETURNING id, cliente_id AS client_id, photo_path
    """
)

INSERT_EMERGENCY_REPORT_SQL = text(
    """
    INSERT INTO reportes_emergencia (
        cliente_id,
        vehiculo_id,
        vehiculo_nombre,
        vehiculo_placa,
        problem_type,
        price,
        estado_emergencia,
        problem_type_standardized,
        photo_problem_type_standardized,
        photo_classification_confidence,
        photo_classification_error,
        description,
        latitude,
        longitude,
        address,
        zone,
        taller_cercano_id,
        taller_cercano_nombre,
        taller_cercano_especialidad,
        taller_cercano_zona,
        taller_cercano_distancia_metros,
        audio_duration_seconds,
        audio_transcript,
        audio_transcript_status,
        audio_transcript_error,
        photo_paths,
        photo_urls,
        audio_path,
        audio_url
    )
    VALUES (
        :client_id,
        :vehicle_id,
        :vehicle_name,
        :vehicle_plate,
        :problem_type,
        :price,
        :emergency_status,
        :problem_type_standardized,
        :photo_problem_type_standardized,
        :photo_classification_confidence,
        :photo_classification_error,
        :description,
        :latitude,
        :longitude,
        :address,
        :zone,
        :nearest_workshop_id,
        :nearest_workshop_name,
        :nearest_workshop_specialty,
        :nearest_workshop_zone,
        :nearest_workshop_distance_meters,
        :audio_duration_seconds,
        :audio_transcript,
        :audio_transcript_status,
        :audio_transcript_error,
        :photo_paths,
        :photo_urls,
        :audio_path,
        :audio_url
    )
    RETURNING
        id,
        cliente_id AS client_id,
        vehiculo_id AS vehicle_id,
        vehiculo_nombre AS vehicle_name,
        vehiculo_placa AS vehicle_plate,
        problem_type,
        price,
        estado_emergencia AS emergency_status,
        problem_type_standardized,
        photo_problem_type_standardized,
        photo_classification_confidence,
        photo_classification_error,
        description,
        latitude,
        longitude,
        address,
        zone,
        taller_cercano_id AS nearest_workshop_id,
        taller_cercano_nombre AS nearest_workshop_name,
        taller_cercano_especialidad AS nearest_workshop_specialty,
        taller_cercano_zona AS nearest_workshop_zone,
        taller_cercano_distancia_metros AS nearest_workshop_distance_meters,
        audio_duration_seconds,
        audio_transcript,
        audio_transcript_status,
        audio_transcript_error,
        photo_paths,
        photo_urls,
        audio_path,
        audio_url,
        rejection_reason,
        rejected_at,
        rejected_by_user_id,
        created_at
    """
)

LIST_EMERGENCY_REPORTS_SQL = text(
    """
    SELECT
        er.id,
        er.cliente_id AS client_id,
        er.vehiculo_id AS vehicle_id,
        er.vehiculo_nombre AS vehicle_name,
        er.vehiculo_placa AS vehicle_plate,
        er.problem_type,
        er.price,
        er.estado_emergencia AS emergency_status,
        er.problem_type_standardized,
        er.photo_problem_type_standardized,
        er.photo_classification_confidence,
        er.photo_classification_error,
        er.description,
        er.latitude,
        er.longitude,
        er.address,
        er.zone,
        er.taller_cercano_id AS nearest_workshop_id,
        er.taller_cercano_nombre AS nearest_workshop_name,
        er.taller_cercano_especialidad AS nearest_workshop_specialty,
        er.taller_cercano_zona AS nearest_workshop_zone,
        er.taller_cercano_distancia_metros AS nearest_workshop_distance_meters,
        er.audio_duration_seconds,
        er.audio_transcript,
        er.audio_transcript_status,
        er.audio_transcript_error,
        er.photo_paths,
        er.photo_urls,
        er.audio_path,
        er.audio_url,
        er.rejection_reason,
        er.rejected_at,
        er.rejected_by_user_id,
        er.created_at,
        c.full_name AS client_name,
        ea.id AS assignment_id,
        ea.estado_asignacion AS assignment_status,
        ea.mecanico_id AS assigned_mecanico_id,
        t.full_name AS assigned_mecanico_name,
        t.phone AS assigned_mecanico_phone,
        t.email AS assigned_mecanico_email,
        t.specialty AS assigned_mecanico_specialty
    FROM reportes_emergencia er
    LEFT JOIN clientes c ON c.id = er.cliente_id
    LEFT JOIN asignaciones_emergencia ea ON ea.reporte_emergencia_id = er.id
    LEFT JOIN mecanicos t ON t.id = ea.mecanico_id
    WHERE (
        CAST(:nearest_workshop_id AS BIGINT) IS NULL
        OR er.taller_cercano_id = CAST(:nearest_workshop_id AS BIGINT)
    )
      AND (
        CAST(:secretaria_sucursal_id AS BIGINT) IS NULL
        OR t.sucursal_id = CAST(:secretaria_sucursal_id AS BIGINT)
    )
      AND (
        CAST(:emergency_status AS VARCHAR(30)) IS NULL
        OR er.estado_emergencia = CAST(:emergency_status AS VARCHAR(30))
    )
    ORDER BY er.created_at DESC, er.id DESC
    """
)

GET_MOBILE_EMERGENCY_TRACKING_SQL = text(
    """
    SELECT
        er.id AS emergency_id,
        er.client_id,
        er.emergency_status,
        er.latitude AS destination_latitude,
        er.longitude AS destination_longitude,
        ea.assignment_status,
        ea.technician_id AS mechanic_id,
        t.full_name AS mechanic_name,
        t.phone AS mechanic_phone,
        t.specialty AS mechanic_specialty,
        wr.id AS workshop_id,
        wr.workshop_name,
        wr.latitude AS workshop_latitude,
        wr.longitude AS workshop_longitude
    FROM emergency_reports er
    LEFT JOIN emergency_assignments ea ON ea.emergency_report_id = er.id
    LEFT JOIN technicians t ON t.id = ea.technician_id
    LEFT JOIN workshop_registrations wr
        ON wr.id = COALESCE(ea.workshop_id, er.nearest_workshop_id)
    WHERE er.id = :report_id
      AND er.client_id = :client_id
    """
)

UPDATE_EMERGENCY_STATUS_SQL = text(
    """
    UPDATE reportes_emergencia
    SET
        estado_emergencia = CAST(:emergency_status AS VARCHAR(30)),
        rejection_reason = CASE
            WHEN CAST(:emergency_status AS VARCHAR(30)) = 'activo' THEN NULL
            ELSE rejection_reason
        END,
        rejected_at = CASE
            WHEN CAST(:emergency_status AS VARCHAR(30)) = 'activo' THEN NULL
            ELSE rejected_at
        END,
        rejected_by_user_id = CASE
            WHEN CAST(:emergency_status AS VARCHAR(30)) = 'activo' THEN NULL
            ELSE rejected_by_user_id
        END
    WHERE id = :report_id
      AND (
        CAST(:nearest_workshop_id AS BIGINT) IS NULL
        OR taller_cercano_id = CAST(:nearest_workshop_id AS BIGINT)
    )
    RETURNING
        id,
        cliente_id AS client_id,
        vehiculo_id AS vehicle_id,
        vehiculo_nombre AS vehicle_name,
        vehiculo_placa AS vehicle_plate,
        problem_type,
        price,
        estado_emergencia AS emergency_status,
        problem_type_standardized,
        photo_problem_type_standardized,
        photo_classification_confidence,
        photo_classification_error,
        description,
        latitude,
        longitude,
        address,
        zone,
        taller_cercano_id AS nearest_workshop_id,
        taller_cercano_nombre AS nearest_workshop_name,
        taller_cercano_especialidad AS nearest_workshop_specialty,
        taller_cercano_zona AS nearest_workshop_zone,
        taller_cercano_distancia_metros AS nearest_workshop_distance_meters,
        audio_duration_seconds,
        audio_transcript,
        audio_transcript_status,
        audio_transcript_error,
        photo_paths,
        photo_urls,
        audio_path,
        audio_url,
        rejection_reason,
        rejected_at,
        rejected_by_user_id,
        created_at,
        NULL::BIGINT AS assignment_id,
        NULL::VARCHAR(30) AS assignment_status,
        NULL::BIGINT AS assigned_mecanico_id,
        NULL::VARCHAR(160) AS assigned_mecanico_name,
        NULL::VARCHAR(40) AS assigned_mecanico_phone,
        NULL::VARCHAR(160) AS assigned_mecanico_email,
        NULL::VARCHAR(120) AS assigned_mecanico_specialty
    """
)

GET_EMERGENCY_REPORT_BY_ID_SQL = text(
    """
    SELECT
        er.id,
        er.cliente_id AS client_id,
        er.vehiculo_id AS vehicle_id,
        er.vehiculo_nombre AS vehicle_name,
        er.vehiculo_placa AS vehicle_plate,
        er.problem_type,
        er.price,
        er.estado_emergencia AS emergency_status,
        er.problem_type_standardized,
        er.photo_problem_type_standardized,
        er.photo_classification_confidence,
        er.photo_classification_error,
        er.description,
        er.latitude,
        er.longitude,
        er.address,
        er.zone,
        er.taller_cercano_id AS nearest_workshop_id,
        er.taller_cercano_nombre AS nearest_workshop_name,
        er.taller_cercano_especialidad AS nearest_workshop_specialty,
        er.taller_cercano_zona AS nearest_workshop_zone,
        er.taller_cercano_distancia_metros AS nearest_workshop_distance_meters,
        er.audio_duration_seconds,
        er.audio_transcript,
        er.audio_transcript_status,
        er.audio_transcript_error,
        er.photo_paths,
        er.photo_urls,
        er.audio_path,
        er.audio_url,
        er.rejection_reason,
        er.rejected_at,
        er.rejected_by_user_id,
        er.created_at,
        c.full_name AS client_name,
        ea.id AS assignment_id,
        ea.estado_asignacion AS assignment_status,
        ea.mecanico_id AS assigned_mecanico_id,
        t.full_name AS assigned_mecanico_name,
        t.phone AS assigned_mecanico_phone,
        t.email AS assigned_mecanico_email,
        t.specialty AS assigned_mecanico_specialty
    FROM reportes_emergencia er
    LEFT JOIN clientes c ON c.id = er.cliente_id
    LEFT JOIN asignaciones_emergencia ea ON ea.reporte_emergencia_id = er.id
    LEFT JOIN mecanicos t ON t.id = ea.mecanico_id
    WHERE er.id = :report_id
    LIMIT 1
    """
)

GET_EMERGENCY_REPORT_FOR_ACCEPT_SQL = text(
    """
    SELECT
        id,
        cliente_id AS client_id,
        estado_emergencia AS emergency_status,
        taller_cercano_id AS nearest_workshop_id,
        taller_cercano_nombre AS nearest_workshop_name,
        description,
        problem_type,
        problem_type_standardized,
        vehiculo_nombre AS vehicle_name
    FROM reportes_emergencia
    WHERE id = :report_id
      AND (
        CAST(:nearest_workshop_id AS BIGINT) IS NULL
        OR taller_cercano_id = CAST(:nearest_workshop_id AS BIGINT)
      )
    FOR UPDATE
    """
)

GET_EMERGENCY_REPORT_FOR_ASSIGNMENT_SQL = text(
    """
    SELECT
        er.id,
        er.cliente_id AS client_id,
        (
            SELECT ea.mecanico_id
            FROM asignaciones_emergencia ea
            WHERE ea.reporte_emergencia_id = er.id
            LIMIT 1
        ) AS assigned_mecanico_id
    FROM reportes_emergencia er
    WHERE er.id = :report_id
      AND (
        CAST(:nearest_workshop_id AS BIGINT) IS NULL
        OR er.taller_cercano_id = CAST(:nearest_workshop_id AS BIGINT)
      )
    FOR UPDATE
    """
)

REJECT_EMERGENCY_REPORT_SQL = text(
    """
    UPDATE reportes_emergencia
    SET
        estado_emergencia = 'rechazado',
        rejection_reason = :rejection_reason,
        rejected_at = NOW(),
        rejected_by_user_id = :rejected_by_user_id
    WHERE id = :report_id
    RETURNING
        id,
        cliente_id AS client_id,
        vehiculo_id AS vehicle_id,
        vehiculo_nombre AS vehicle_name,
        vehiculo_placa AS vehicle_plate,
        problem_type,
        price,
        estado_emergencia AS emergency_status,
        problem_type_standardized,
        photo_problem_type_standardized,
        photo_classification_confidence,
        photo_classification_error,
        description,
        latitude,
        longitude,
        address,
        zone,
        taller_cercano_id AS nearest_workshop_id,
        taller_cercano_nombre AS nearest_workshop_name,
        taller_cercano_especialidad AS nearest_workshop_specialty,
        taller_cercano_zona AS nearest_workshop_zone,
        taller_cercano_distancia_metros AS nearest_workshop_distance_meters,
        audio_duration_seconds,
        audio_transcript,
        audio_transcript_status,
        audio_transcript_error,
        photo_paths,
        photo_urls,
        audio_path,
        audio_url,
        rejection_reason,
        rejected_at,
        rejected_by_user_id,
        created_at
    """
)

INSERT_CLIENT_NOTIFICATION_SQL = text(
    """
    INSERT INTO notificaciones_cliente (
        cliente_id,
        emergencia_id,
        tipo,
        titulo,
        mensaje,
        metadata,
        leida
    )
    VALUES (
        :cliente_id,
        :emergencia_id,
        :tipo,
        :titulo,
        :mensaje,
        CAST(:metadata AS JSONB),
        FALSE
    )
    RETURNING
        id,
        cliente_id,
        emergencia_id,
        tipo,
        titulo,
        mensaje,
        metadata,
        leida,
        created_at,
        read_at
    """
)

LIST_CLIENT_NOTIFICATIONS_SQL = text(
    """
    SELECT
        id,
        cliente_id,
        emergencia_id,
        tipo,
        titulo,
        mensaje,
        metadata,
        leida,
        created_at,
        read_at
    FROM notificaciones_cliente
    WHERE cliente_id = :cliente_id
    ORDER BY created_at DESC, id DESC
    """
)

MARK_CLIENT_NOTIFICATION_READ_SQL = text(
    """
    UPDATE notificaciones_cliente
    SET
        leida = TRUE,
        read_at = COALESCE(read_at, NOW())
    WHERE id = :notification_id
      AND cliente_id = :cliente_id
    RETURNING
        id,
        cliente_id,
        emergencia_id,
        tipo,
        titulo,
        mensaje,
        metadata,
        leida,
        created_at,
        read_at
    """
)

COUNT_UNREAD_CLIENT_NOTIFICATIONS_SQL = text(
    """
    SELECT COUNT(*)::INTEGER AS unread_count
    FROM notificaciones_cliente
    WHERE cliente_id = :cliente_id
      AND leida = FALSE
    """
)

ASSIGN_EMERGENCY_MECANICO_SQL = text(
    """
    INSERT INTO asignaciones_emergencia (
        reporte_emergencia_id,
        taller_id,
        mecanico_id,
        estado_asignacion
    )
    VALUES (
        :report_id,
        :workshop_id,
        :mecanico_id,
        'asignado'
    )
    ON CONFLICT (reporte_emergencia_id)
    DO UPDATE SET
        taller_id = EXCLUDED.taller_id,
        mecanico_id = EXCLUDED.mecanico_id,
        estado_asignacion = 'asignado',
        updated_at = NOW()
    RETURNING
        id,
        reporte_emergencia_id AS emergency_report_id,
        taller_id AS workshop_id,
        mecanico_id,
        estado_asignacion AS assignment_status,
        created_at,
        updated_at
    """
)

GET_EMERGENCY_TRACKING_CONTEXT_SQL = text(
    """
    SELECT
        er.id AS emergencia_id,
        er.cliente_id AS client_id,
        er.estado_emergencia AS emergency_status,
        er.latitude AS destination_latitude,
        er.longitude AS destination_longitude,
        er.address,
        er.zone,
        ea.id AS assignment_id,
        ea.estado_asignacion AS assignment_status,
        ea.mecanico_id AS assigned_mecanico_id,
        m.full_name AS assigned_mecanico_name,
        m.phone AS assigned_mecanico_phone,
        m.email AS assigned_mecanico_email,
        m.specialty AS assigned_mecanico_specialty,
        m.sucursal_id,
        m.taller_id AS workshop_id,
        s.nombre AS sucursal_nombre,
        s.latitud AS origin_latitude,
        s.longitud AS origin_longitude
    FROM reportes_emergencia er
    LEFT JOIN asignaciones_emergencia ea ON ea.reporte_emergencia_id = er.id
    LEFT JOIN mecanicos m ON m.id = ea.mecanico_id
    LEFT JOIN sucursales s ON s.id = m.sucursal_id
    WHERE er.id = :emergency_id
    LIMIT 1
    """
)

LIST_EMERGENCY_TRACKING_EVENTS_SQL = text(
    """
    SELECT
        id,
        emergencia_id,
        mecanico_id,
        latitud,
        longitud,
        heading,
        speed,
        event_type,
        created_at
    FROM seguimiento_emergencia_tracking
    WHERE emergencia_id = :emergency_id
    ORDER BY created_at ASC, id ASC
    """
)

INSERT_EMERGENCY_TRACKING_EVENT_SQL = text(
    """
    INSERT INTO seguimiento_emergencia_tracking (
        emergencia_id,
        mecanico_id,
        latitud,
        longitud,
        heading,
        speed,
        event_type
    )
    VALUES (
        :emergency_id,
        :mecanico_id,
        :latitud,
        :longitud,
        :heading,
        :speed,
        :event_type
    )
    RETURNING
        id,
        emergencia_id,
        mecanico_id,
        latitud,
        longitud,
        heading,
        speed,
        event_type,
        created_at
    """
)

DELETE_EMERGENCY_REPORT_SQL = text(
    """
    DELETE FROM reportes_emergencia
    WHERE id = :report_id
      AND (
        CAST(:nearest_workshop_id AS BIGINT) IS NULL
        OR taller_cercano_id = CAST(:nearest_workshop_id AS BIGINT)
    )
    RETURNING id, photo_paths, photo_urls, audio_path, audio_url
    """
)

BACKFILL_EMERGENCY_PRICES_SQL = text(
    """
    UPDATE reportes_emergencia
    SET price = CASE
        WHEN COALESCE(problem_type_standardized, problem_type) = 'Batería' THEN 50
        WHEN COALESCE(problem_type_standardized, problem_type) = 'Neumático' THEN 50
        WHEN COALESCE(problem_type_standardized, problem_type) = 'Combustible' THEN 60
        WHEN COALESCE(problem_type_standardized, problem_type) = 'Motor' THEN 100
        WHEN COALESCE(problem_type_standardized, problem_type) = 'Sistema eléctrico' THEN 90
        WHEN COALESCE(problem_type_standardized, problem_type) = 'Accidente' THEN 150
        WHEN COALESCE(problem_type_standardized, problem_type) = 'Cerrajería / llaves' THEN 80
        ELSE price
    END
    WHERE price IS NULL
      AND COALESCE(problem_type_standardized, problem_type) IN (
        'Batería',
        'Neumático',
        'Combustible',
        'Motor',
        'Sistema eléctrico',
        'Accidente',
        'Cerrajería / llaves'
      )
    """
)

UPSERT_DEVICE_FCM_TOKEN_SQL = text(
    """
    INSERT INTO tokens_fcm_dispositivo (
        user_id,
        fcm_token,
        platform,
        is_active
    )
    VALUES (
        :user_id,
        :fcm_token,
        :platform,
        TRUE
    )
    ON CONFLICT (fcm_token)
    DO UPDATE SET
        user_id = EXCLUDED.user_id,
        platform = EXCLUDED.platform,
        is_active = TRUE,
        updated_at = NOW()
    RETURNING
        id,
        user_id,
        fcm_token,
        platform,
        is_active,
        created_at,
        updated_at
    """
)

LIST_ACTIVE_DEVICE_FCM_TOKENS_SQL = text(
    """
    SELECT
        id,
        user_id,
        fcm_token,
        platform,
        is_active,
        created_at,
        updated_at
    FROM tokens_fcm_dispositivo
    WHERE user_id = :user_id
      AND is_active = TRUE
    ORDER BY updated_at DESC, id DESC
    """
)

CREATE_TOKENS_FCM_TALLER_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS tokens_fcm_taller (
        id BIGSERIAL PRIMARY KEY,
        workshop_id BIGINT NOT NULL REFERENCES registros_taller(id) ON DELETE CASCADE,
        fcm_token TEXT NOT NULL UNIQUE,
        platform VARCHAR(40) NOT NULL DEFAULT 'android',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

UPSERT_WORKSHOP_FCM_TOKEN_SQL = text(
    """
    INSERT INTO tokens_fcm_taller (workshop_id, fcm_token, platform, is_active)
    VALUES (:workshop_id, :fcm_token, :platform, TRUE)
    ON CONFLICT (fcm_token)
    DO UPDATE SET
        workshop_id = EXCLUDED.workshop_id,
        platform = EXCLUDED.platform,
        is_active = TRUE,
        updated_at = NOW()
    RETURNING id, workshop_id, fcm_token, platform, is_active, created_at, updated_at
    """
)

LIST_ACTIVE_WORKSHOP_FCM_TOKENS_SQL = text(
    """
    SELECT id, workshop_id, fcm_token, platform, is_active, created_at, updated_at
    FROM tokens_fcm_taller
    WHERE workshop_id = :workshop_id AND is_active = TRUE
    ORDER BY updated_at DESC, id DESC
    """
)

DEACTIVATE_WORKSHOP_FCM_TOKEN_SQL = text(
    """
    UPDATE tokens_fcm_taller
    SET is_active = FALSE, updated_at = NOW()
    WHERE fcm_token = :fcm_token AND workshop_id = :workshop_id
    RETURNING id
    """
)

DEACTIVATE_CLIENT_FCM_TOKEN_SQL = text(
    """
    UPDATE tokens_fcm_dispositivo
    SET is_active = FALSE, updated_at = NOW()
    WHERE fcm_token = :fcm_token AND user_id = :user_id
    RETURNING id
    """
)

INSERT_PASSWORD_RESET_TOKEN_SQL = text(
    """
    INSERT INTO tokens_recuperacion_password (
        account_type,
        account_id,
        token_hash,
        expires_at,
        used_at,
        created_at
    )
    VALUES (
        :account_type,
        :account_id,
        :token_hash,
        :expires_at,
        :used_at,
        :created_at
    )
    RETURNING
        id,
        account_type,
        account_id,
        token_hash,
        expires_at,
        used_at,
        created_at
    """
)

GET_PASSWORD_RESET_TOKEN_BY_HASH_SQL = text(
    """
    SELECT
        id,
        account_type,
        account_id,
        token_hash,
        expires_at,
        used_at,
        created_at
    FROM tokens_recuperacion_password
    WHERE token_hash = :token_hash
    ORDER BY id DESC
    LIMIT 1
    """
)

MARK_PASSWORD_RESET_TOKEN_USED_SQL = text(
    """
    UPDATE tokens_recuperacion_password
    SET used_at = :used_at
    WHERE id = :id
      AND used_at IS NULL
    RETURNING
        id,
        account_type,
        account_id,
        token_hash,
        expires_at,
        used_at,
        created_at
    """
)


def check_database_connection() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def _hash_seed_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${digest.hex()}"


def _seed_operational_user(
    connection,
    *,
    identity_card: str,
    full_name: str,
    email: str,
    phone: str,
    password: str,
    role: str,
) -> None:
    existing = connection.execute(
        text("SELECT id FROM clientes WHERE email = :email OR identity_card = :identity_card"),
        {"email": email, "identity_card": identity_card},
    ).mappings().one_or_none()

    if existing:
        connection.execute(
            text(
                """
                UPDATE clientes
                SET
                    full_name = :full_name,
                    phone = :phone,
                    role = :role,
                    status = 'active',
                    accepted_terms = TRUE,
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {
                "id": existing["id"],
                "full_name": full_name,
                "phone": phone,
                "role": role,
            },
        )
        return

    connection.execute(
        text(
            """
            INSERT INTO clientes (
                identity_card,
                full_name,
                email,
                phone,
                password_hash,
                role,
                status,
                accepted_terms
            )
            VALUES (
                :identity_card,
                :full_name,
                :email,
                :phone,
                :password_hash,
                :role,
                'active',
                TRUE
            )
            """
        ),
        {
            "identity_card": identity_card,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "password_hash": _hash_seed_password(password),
            "role": role,
        },
    )


def init_database() -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'workshop_registrations' AND table_type = 'BASE TABLE'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'registros_taller'
                    ) THEN
                        ALTER TABLE workshop_registrations RENAME TO registros_taller;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'clients' AND table_type = 'BASE TABLE'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'clientes'
                    ) THEN
                        ALTER TABLE clients RENAME TO clientes;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'vehicles' AND table_type = 'BASE TABLE'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'vehiculos'
                    ) THEN
                        ALTER TABLE vehicles RENAME TO vehiculos;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'emergency_reports' AND table_type = 'BASE TABLE'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'reportes_emergencia'
                    ) THEN
                        ALTER TABLE emergency_reports RENAME TO reportes_emergencia;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'emergency_assignments' AND table_type = 'BASE TABLE'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'asignaciones_emergencia'
                    ) THEN
                        ALTER TABLE emergency_assignments RENAME TO asignaciones_emergencia;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'device_fcm_tokens' AND table_type = 'BASE TABLE'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'tokens_fcm_dispositivo'
                    ) THEN
                        ALTER TABLE device_fcm_tokens RENAME TO tokens_fcm_dispositivo;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'password_reset_tokens' AND table_type = 'BASE TABLE'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'tokens_recuperacion_password'
                    ) THEN
                        ALTER TABLE password_reset_tokens RENAME TO tokens_recuperacion_password;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(CREATE_SUCURSALES_TABLE_SQL)
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS sucursales_nombre_direccion_activa_key
                ON sucursales (LOWER(nombre), LOWER(direccion))
                WHERE estado = 'ACTIVO'
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'clients_id_seq')
                       AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'clientes_id_seq') THEN
                        ALTER SEQUENCE clients_id_seq RENAME TO clientes_id_seq;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'vehicles_id_seq')
                       AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'vehiculos_id_seq') THEN
                        ALTER SEQUENCE vehicles_id_seq RENAME TO vehiculos_id_seq;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'workshop_registrations_id_seq')
                       AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'registros_taller_id_seq') THEN
                        ALTER SEQUENCE workshop_registrations_id_seq RENAME TO registros_taller_id_seq;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'emergency_reports_id_seq')
                       AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'reportes_emergencia_id_seq') THEN
                        ALTER SEQUENCE emergency_reports_id_seq RENAME TO reportes_emergencia_id_seq;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'emergency_assignments_id_seq')
                       AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'asignaciones_emergencia_id_seq') THEN
                        ALTER SEQUENCE emergency_assignments_id_seq RENAME TO asignaciones_emergencia_id_seq;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'device_fcm_tokens_id_seq')
                       AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'tokens_fcm_dispositivo_id_seq') THEN
                        ALTER SEQUENCE device_fcm_tokens_id_seq RENAME TO tokens_fcm_dispositivo_id_seq;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'password_reset_tokens_id_seq')
                       AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'tokens_recuperacion_password_id_seq') THEN
                        ALTER SEQUENCE password_reset_tokens_id_seq RENAME TO tokens_recuperacion_password_id_seq;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name = 'technicians'
                          AND table_type = 'BASE TABLE'
                    ) AND NOT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name = 'mecanicos'
                    ) THEN
                        ALTER TABLE technicians RENAME TO mecanicos;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'clients_pkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'clientes_pkey') THEN
                        ALTER TABLE clientes RENAME CONSTRAINT clients_pkey TO clientes_pkey;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'clients_email_key')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'clientes_email_key') THEN
                        ALTER TABLE clientes RENAME CONSTRAINT clients_email_key TO clientes_email_key;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'clients_identity_card_key')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'clientes_identity_card_key') THEN
                        ALTER TABLE clientes RENAME CONSTRAINT clients_identity_card_key TO clientes_identity_card_key;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'vehicles_pkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'vehiculos_pkey') THEN
                        ALTER TABLE vehiculos RENAME CONSTRAINT vehicles_pkey TO vehiculos_pkey;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'vehicles_plate_key')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'vehiculos_plate_key') THEN
                        ALTER TABLE vehiculos RENAME CONSTRAINT vehicles_plate_key TO vehiculos_plate_key;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'vehicles_client_id_fkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'vehiculos_cliente_id_fkey') THEN
                        ALTER TABLE vehiculos RENAME CONSTRAINT vehicles_client_id_fkey TO vehiculos_cliente_id_fkey;
                    ELSIF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'vehicles_client_id_fkey')
                      AND EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'vehiculos_cliente_id_fkey') THEN
                        ALTER TABLE vehiculos DROP CONSTRAINT vehicles_client_id_fkey;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'workshop_registrations_pkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'registros_taller_pkey') THEN
                        ALTER TABLE registros_taller RENAME CONSTRAINT workshop_registrations_pkey TO registros_taller_pkey;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'emergency_reports_pkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'reportes_emergencia_pkey') THEN
                        ALTER TABLE reportes_emergencia RENAME CONSTRAINT emergency_reports_pkey TO reportes_emergencia_pkey;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'emergency_reports_client_id_fkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'reportes_emergencia_cliente_id_fkey') THEN
                        ALTER TABLE reportes_emergencia
                        RENAME CONSTRAINT emergency_reports_client_id_fkey TO reportes_emergencia_cliente_id_fkey;
                    ELSIF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'emergency_reports_client_id_fkey')
                      AND EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'reportes_emergencia_cliente_id_fkey') THEN
                        ALTER TABLE reportes_emergencia DROP CONSTRAINT emergency_reports_client_id_fkey;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'emergency_reports_vehicle_id_fkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'reportes_emergencia_vehiculo_id_fkey') THEN
                        ALTER TABLE reportes_emergencia
                        RENAME CONSTRAINT emergency_reports_vehicle_id_fkey TO reportes_emergencia_vehiculo_id_fkey;
                    ELSIF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'emergency_reports_vehicle_id_fkey')
                      AND EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'reportes_emergencia_vehiculo_id_fkey') THEN
                        ALTER TABLE reportes_emergencia DROP CONSTRAINT emergency_reports_vehicle_id_fkey;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'emergency_assignments_pkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'asignaciones_emergencia_pkey') THEN
                        ALTER TABLE asignaciones_emergencia
                        RENAME CONSTRAINT emergency_assignments_pkey TO asignaciones_emergencia_pkey;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'emergency_assignments_emergency_report_id_key')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'asignaciones_emergencia_reporte_emergencia_id_key') THEN
                        ALTER TABLE asignaciones_emergencia
                        RENAME CONSTRAINT emergency_assignments_emergency_report_id_key TO asignaciones_emergencia_reporte_emergencia_id_key;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'emergency_assignments_emergency_report_id_fkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'asignaciones_emergencia_reporte_emergencia_id_fkey') THEN
                        ALTER TABLE asignaciones_emergencia
                        RENAME CONSTRAINT emergency_assignments_emergency_report_id_fkey TO asignaciones_emergencia_reporte_emergencia_id_fkey;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'emergency_assignments_workshop_id_fkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'asignaciones_emergencia_taller_id_fkey') THEN
                        ALTER TABLE asignaciones_emergencia
                        RENAME CONSTRAINT emergency_assignments_workshop_id_fkey TO asignaciones_emergencia_taller_id_fkey;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'emergency_assignments_mecanico_id_fkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'asignaciones_emergencia_mecanico_id_fkey') THEN
                        ALTER TABLE asignaciones_emergencia
                        RENAME CONSTRAINT emergency_assignments_mecanico_id_fkey TO asignaciones_emergencia_mecanico_id_fkey;
                    ELSIF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'emergency_assignments_mecanico_id_fkey')
                      AND EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'asignaciones_emergencia_mecanico_id_fkey') THEN
                        ALTER TABLE asignaciones_emergencia DROP CONSTRAINT emergency_assignments_mecanico_id_fkey;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'mecanicos_workshop_id_fkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'mecanicos_taller_id_fkey') THEN
                        ALTER TABLE mecanicos RENAME CONSTRAINT mecanicos_workshop_id_fkey TO mecanicos_taller_id_fkey;
                    ELSIF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'mecanicos_workshop_id_fkey')
                      AND EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'mecanicos_taller_id_fkey') THEN
                        ALTER TABLE mecanicos DROP CONSTRAINT mecanicos_workshop_id_fkey;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'device_fcm_tokens_pkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tokens_fcm_dispositivo_pkey') THEN
                        ALTER TABLE tokens_fcm_dispositivo
                        RENAME CONSTRAINT device_fcm_tokens_pkey TO tokens_fcm_dispositivo_pkey;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'password_reset_tokens_pkey')
                       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tokens_recuperacion_password_pkey') THEN
                        ALTER TABLE tokens_recuperacion_password
                        RENAME CONSTRAINT password_reset_tokens_pkey TO tokens_recuperacion_password_pkey;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'i' AND relname = 'emergency_reports_vehicle_id_idx')
                       AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'i' AND relname = 'reportes_emergencia_vehiculo_id_idx') THEN
                        ALTER INDEX emergency_reports_vehicle_id_idx RENAME TO reportes_emergencia_vehiculo_id_idx;
                    ELSIF EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'i' AND relname = 'emergency_reports_vehicle_id_idx')
                      AND EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'i' AND relname = 'reportes_emergencia_vehiculo_id_idx') THEN
                        DROP INDEX emergency_reports_vehicle_id_idx;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'i' AND relname = 'device_fcm_tokens_fcm_token_key')
                       AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'i' AND relname = 'tokens_fcm_dispositivo_fcm_token_key') THEN
                        ALTER INDEX device_fcm_tokens_fcm_token_key RENAME TO tokens_fcm_dispositivo_fcm_token_key;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'i' AND relname = 'password_reset_tokens_token_hash_key')
                       AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'i' AND relname = 'tokens_recuperacion_password_token_hash_key') THEN
                        ALTER INDEX password_reset_tokens_token_hash_key RENAME TO tokens_recuperacion_password_token_hash_key;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'i' AND relname = 'password_reset_tokens_account_lookup_idx')
                       AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'i' AND relname = 'tokens_recuperacion_password_account_lookup_idx') THEN
                        ALTER INDEX password_reset_tokens_account_lookup_idx RENAME TO tokens_recuperacion_password_account_lookup_idx;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='mecanicos' AND column_name='workshop_id'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='mecanicos' AND column_name='taller_id'
                    ) THEN
                        ALTER TABLE mecanicos RENAME COLUMN workshop_id TO taller_id;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='vehiculos' AND column_name='client_id'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='vehiculos' AND column_name='cliente_id'
                    ) THEN
                        ALTER TABLE vehiculos RENAME COLUMN client_id TO cliente_id;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='client_id'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='cliente_id'
                    ) THEN
                        ALTER TABLE reportes_emergencia RENAME COLUMN client_id TO cliente_id;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='vehicle_id'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='vehiculo_id'
                    ) THEN
                        ALTER TABLE reportes_emergencia RENAME COLUMN vehicle_id TO vehiculo_id;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='vehicle_name'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='vehiculo_nombre'
                    ) THEN
                        ALTER TABLE reportes_emergencia RENAME COLUMN vehicle_name TO vehiculo_nombre;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='vehicle_plate'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='vehiculo_placa'
                    ) THEN
                        ALTER TABLE reportes_emergencia RENAME COLUMN vehicle_plate TO vehiculo_placa;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='emergency_status'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='estado_emergencia'
                    ) THEN
                        ALTER TABLE reportes_emergencia RENAME COLUMN emergency_status TO estado_emergencia;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='nearest_workshop_id'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='taller_cercano_id'
                    ) THEN
                        ALTER TABLE reportes_emergencia RENAME COLUMN nearest_workshop_id TO taller_cercano_id;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='nearest_workshop_name'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='taller_cercano_nombre'
                    ) THEN
                        ALTER TABLE reportes_emergencia RENAME COLUMN nearest_workshop_name TO taller_cercano_nombre;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='nearest_workshop_specialty'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='taller_cercano_especialidad'
                    ) THEN
                        ALTER TABLE reportes_emergencia RENAME COLUMN nearest_workshop_specialty TO taller_cercano_especialidad;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='nearest_workshop_zone'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='taller_cercano_zona'
                    ) THEN
                        ALTER TABLE reportes_emergencia RENAME COLUMN nearest_workshop_zone TO taller_cercano_zona;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='nearest_workshop_distance_meters'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='reportes_emergencia' AND column_name='taller_cercano_distancia_metros'
                    ) THEN
                        ALTER TABLE reportes_emergencia RENAME COLUMN nearest_workshop_distance_meters TO taller_cercano_distancia_metros;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='asignaciones_emergencia' AND column_name='emergency_report_id'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='asignaciones_emergencia' AND column_name='reporte_emergencia_id'
                    ) THEN
                        ALTER TABLE asignaciones_emergencia RENAME COLUMN emergency_report_id TO reporte_emergencia_id;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='asignaciones_emergencia' AND column_name='workshop_id'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='asignaciones_emergencia' AND column_name='taller_id'
                    ) THEN
                        ALTER TABLE asignaciones_emergencia RENAME COLUMN workshop_id TO taller_id;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='asignaciones_emergencia' AND column_name='assignment_status'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='asignaciones_emergencia' AND column_name='estado_asignacion'
                    ) THEN
                        ALTER TABLE asignaciones_emergencia RENAME COLUMN assignment_status TO estado_asignacion;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='registros_taller' AND column_name='workshop_name'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='registros_taller' AND column_name='nombre_taller'
                    ) THEN
                        ALTER TABLE registros_taller RENAME COLUMN workshop_name TO nombre_taller;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(CREATE_REGISTROS_TALLER_TABLE_SQL)
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'technicians_id_seq')
                       AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'mecanicos_id_seq') THEN
                        ALTER SEQUENCE technicians_id_seq RENAME TO mecanicos_id_seq;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'asignaciones_emergencia'
                          AND column_name = 'technician_id'
                    ) AND NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'asignaciones_emergencia'
                          AND column_name = 'mecanico_id'
                    ) THEN
                        ALTER TABLE asignaciones_emergencia RENAME COLUMN technician_id TO mecanico_id;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(CREATE_MECANICOS_TABLE_SQL)
        connection.execute(CREATE_CLIENTES_TABLE_SQL)
        connection.execute(CREATE_VEHICULOS_TABLE_SQL)
        connection.execute(CREATE_REPORTES_EMERGENCIA_TABLE_SQL)
        connection.execute(CREATE_ASIGNACIONES_EMERGENCIA_TABLE_SQL)
        connection.execute(CREATE_EMERGENCY_TRACKING_EVENTS_TABLE_SQL)
        connection.execute(CREATE_TOKENS_FCM_DISPOSITIVO_TABLE_SQL)
        connection.execute(CREATE_NOTIFICACIONES_CLIENTE_TABLE_SQL)
        connection.execute(CREATE_TOKENS_RECUPERACION_PASSWORD_TABLE_SQL)
        connection.execute(CREATE_TOKENS_FCM_TALLER_TABLE_SQL)
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_tokens_fcm_taller_workshop_id
                ON tokens_fcm_taller (workshop_id)
                WHERE is_active = TRUE
                """
            )
        )
        connection.execute(CREATE_RECEPCION_CLIENTES_TABLE_SQL)
        connection.execute(CREATE_RECEPCION_VEHICULOS_TABLE_SQL)
        connection.execute(CREATE_RECEPCION_FICHAS_TABLE_SQL)
        connection.execute(CREATE_RECEPCION_ACCESORIOS_TABLE_SQL)
        connection.execute(CREATE_RECEPCION_PROBLEMAS_TABLE_SQL)
        connection.execute(CREATE_RECEPCION_DIAGNOSTICOS_TABLE_SQL)
        connection.execute(CREATE_RECEPCION_OBSERVACIONES_TABLE_SQL)
        connection.execute(text("ALTER TABLE fichas_recepcion ADD COLUMN IF NOT EXISTS emergencia_id BIGINT"))
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'fichas_recepcion_emergencia_id_fkey'
                    ) AND NOT EXISTS (
                        SELECT 1
                        FROM fichas_recepcion fr
                        LEFT JOIN reportes_emergencia re ON re.id = fr.emergencia_id
                        WHERE fr.emergencia_id IS NOT NULL
                          AND re.id IS NULL
                    ) THEN
                        ALTER TABLE fichas_recepcion
                        ADD CONSTRAINT fichas_recepcion_emergencia_id_fkey
                        FOREIGN KEY (emergencia_id)
                        REFERENCES reportes_emergencia(id)
                        ON DELETE SET NULL;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(text("ALTER TABLE mecanicos ADD COLUMN IF NOT EXISTS taller_id BIGINT"))
        connection.execute(text("ALTER TABLE mecanicos ADD COLUMN IF NOT EXISTS sucursal_id BIGINT"))
        connection.execute(text("ALTER TABLE mecanicos ADD COLUMN IF NOT EXISTS email VARCHAR(160)"))
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM pg_attrdef d
                        JOIN pg_class c ON c.oid = d.adrelid
                        JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = d.adnum
                        WHERE c.relname = 'mecanicos'
                          AND a.attname = 'id'
                          AND pg_get_expr(d.adbin, d.adrelid) LIKE '%technicians_id_seq%'
                    ) THEN
                        ALTER TABLE mecanicos ALTER COLUMN id SET DEFAULT nextval('mecanicos_id_seq'::regclass);
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'mecanicos_sucursal_id_fkey'
                    ) AND NOT EXISTS (
                        SELECT 1
                        FROM mecanicos m
                        LEFT JOIN sucursales s ON s.id = m.sucursal_id
                        WHERE m.sucursal_id IS NOT NULL
                          AND s.id IS NULL
                    ) THEN
                        ALTER TABLE mecanicos
                        ADD CONSTRAINT mecanicos_sucursal_id_fkey
                        FOREIGN KEY (sucursal_id)
                        REFERENCES sucursales(id)
                        ON DELETE SET NULL;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'technicians_pkey'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'mecanicos_pkey'
                    ) THEN
                        ALTER TABLE mecanicos RENAME CONSTRAINT technicians_pkey TO mecanicos_pkey;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'technicians_workshop_id_fkey'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'mecanicos_workshop_id_fkey'
                    ) THEN
                        ALTER TABLE mecanicos RENAME CONSTRAINT technicians_workshop_id_fkey TO mecanicos_workshop_id_fkey;
                    ELSIF EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'technicians_workshop_id_fkey'
                    ) AND EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'mecanicos_workshop_id_fkey'
                    ) THEN
                        ALTER TABLE mecanicos DROP CONSTRAINT technicians_workshop_id_fkey;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'emergency_assignments_technician_id_fkey'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'asignaciones_emergencia_mecanico_id_fkey'
                    ) THEN
                        ALTER TABLE asignaciones_emergencia
                        RENAME CONSTRAINT emergency_assignments_technician_id_fkey TO asignaciones_emergencia_mecanico_id_fkey;
                    ELSIF EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'emergency_assignments_technician_id_fkey'
                    ) AND EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'asignaciones_emergencia_mecanico_id_fkey'
                    ) THEN
                        ALTER TABLE asignaciones_emergencia DROP CONSTRAINT emergency_assignments_technician_id_fkey;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname IN ('mecanicos_workshop_id_fkey', 'technicians_workshop_id_fkey')
                    ) THEN
                        ALTER TABLE mecanicos
                        ADD CONSTRAINT mecanicos_workshop_id_fkey
                        FOREIGN KEY (taller_id)
                        REFERENCES registros_taller(id)
                        ON DELETE CASCADE;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'asignaciones_emergencia'
                          AND column_name = 'mecanico_id'
                    ) AND NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'asignaciones_emergencia_mecanico_id_fkey'
                    ) THEN
                        ALTER TABLE asignaciones_emergencia
                        ADD CONSTRAINT asignaciones_emergencia_mecanico_id_fkey
                        FOREIGN KEY (mecanico_id)
                        REFERENCES mecanicos(id)
                        ON DELETE RESTRICT;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text("ALTER TABLE registros_taller ADD COLUMN IF NOT EXISTS timezone VARCHAR(120)")
        )
        connection.execute(
            text("ALTER TABLE registros_taller ADD COLUMN IF NOT EXISTS utc_offset_minutes INTEGER")
        )
        connection.execute(
            text(
                "ALTER TABLE registros_taller "
                "ADD COLUMN IF NOT EXISTS approval_status VARCHAR(30) NOT NULL DEFAULT 'pendiente'"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE registros_taller "
                "ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"
            )
        )
        connection.execute(
            text(
                "UPDATE registros_taller "
                "SET approval_status = 'pendiente' "
                "WHERE approval_status IS NULL OR approval_status = ''"
            )
        )
        connection.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS role VARCHAR(40) DEFAULT 'client'"))
        connection.execute(
            text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'active'")
        )
        connection.execute(
            text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS accepted_terms BOOLEAN NOT NULL DEFAULT FALSE")
        )
        connection.execute(
            text(
                """
                UPDATE clientes
                SET role = :mecanico_role
                WHERE LOWER(TRIM(role)) IN ('tecnico', 'técnico', 'technician')
                """
            ),
            {"mecanico_role": MECANICO_ROLE},
        )
        _seed_operational_user(
            connection,
            identity_card="9000001",
            full_name="Secretaria Recepcion",
            email="secretaria@acb.com",
            phone="70000001",
            password="secretaria123",
            role=SECRETARIA_ROLE,
        )
        _seed_operational_user(
            connection,
            identity_card="9000002",
            full_name="Mecanico Taller",
            email="mecanico@acb.com",
            phone="70000002",
            password="mecanico123",
            role=MECANICO_ROLE,
        )
        connection.execute(text("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS cliente_id BIGINT"))
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'vehiculos_cliente_id_fkey'
                    ) THEN
                        ALTER TABLE vehiculos
                        ADD CONSTRAINT vehiculos_cliente_id_fkey
                        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE;
                    END IF;
                END$$;
                """
            )
        )
        connection.execute(text("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS photo_path VARCHAR(255)"))
        connection.execute(text("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS photo_url VARCHAR(255)"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS cliente_id BIGINT"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS vehiculo_id BIGINT"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS vehiculo_nombre VARCHAR(160)"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS vehiculo_placa VARCHAR(40)"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS problem_type VARCHAR(120)"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS price INTEGER"))
        connection.execute(
            text(
                """
                ALTER TABLE reportes_emergencia
                ADD COLUMN IF NOT EXISTS estado_emergencia VARCHAR(30) NOT NULL DEFAULT 'pendiente'
                """
            )
        )
        connection.execute(
            text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS problem_type_standardized VARCHAR(120)")
        )
        connection.execute(
            text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS photo_problem_type_standardized VARCHAR(120)")
        )
        connection.execute(
            text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS photo_classification_confidence DOUBLE PRECISION")
        )
        connection.execute(
            text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS photo_classification_error TEXT")
        )
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS description TEXT"))
        connection.execute(text("ALTER TABLE reportes_emergencia ALTER COLUMN description DROP NOT NULL"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS address VARCHAR(255)"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS zone VARCHAR(120)"))
        connection.execute(
            text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS taller_cercano_id BIGINT")
        )
        connection.execute(
            text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS taller_cercano_nombre VARCHAR(160)")
        )
        connection.execute(
            text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS taller_cercano_especialidad VARCHAR(120)")
        )
        connection.execute(
            text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS taller_cercano_zona VARCHAR(120)")
        )
        connection.execute(
            text(
                """
                ALTER TABLE reportes_emergencia
                ADD COLUMN IF NOT EXISTS taller_cercano_distancia_metros DOUBLE PRECISION
                """
            )
        )
        connection.execute(
            text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS audio_duration_seconds DOUBLE PRECISION")
        )
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS audio_transcript TEXT"))
        connection.execute(
            text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS audio_transcript_status VARCHAR(30)")
        )
        connection.execute(
            text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS audio_transcript_error TEXT")
        )
        connection.execute(
            text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS photo_paths TEXT NOT NULL DEFAULT '[]'")
        )
        connection.execute(
            text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS photo_urls TEXT NOT NULL DEFAULT '[]'")
        )
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS audio_path VARCHAR(255)"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS audio_url VARCHAR(255)"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS rejection_reason TEXT"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE reportes_emergencia ADD COLUMN IF NOT EXISTS rejected_by_user_id BIGINT"))
        connection.execute(BACKFILL_EMERGENCY_PRICES_SQL)
        connection.execute(CREATE_ASIGNACIONES_EMERGENCIA_TABLE_SQL)
        connection.execute(CREATE_EMERGENCY_TRACKING_EVENTS_TABLE_SQL)
        connection.execute(CREATE_TOKENS_FCM_DISPOSITIVO_TABLE_SQL)
        connection.execute(CREATE_NOTIFICACIONES_CLIENTE_TABLE_SQL)
        connection.execute(text("ALTER TABLE tokens_fcm_dispositivo ADD COLUMN IF NOT EXISTS user_id BIGINT"))
        connection.execute(text("ALTER TABLE tokens_fcm_dispositivo ADD COLUMN IF NOT EXISTS fcm_token TEXT"))
        connection.execute(text("ALTER TABLE tokens_fcm_dispositivo ADD COLUMN IF NOT EXISTS platform VARCHAR(40)"))
        connection.execute(
            text("ALTER TABLE tokens_fcm_dispositivo ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE")
        )
        connection.execute(
            text("ALTER TABLE tokens_fcm_dispositivo ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
        )
        connection.execute(
            text("ALTER TABLE tokens_fcm_dispositivo ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
        )
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS tokens_fcm_dispositivo_fcm_token_key
                ON tokens_fcm_dispositivo (fcm_token)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_notificaciones_cliente_cliente_id_created_at
                ON notificaciones_cliente (cliente_id, created_at DESC)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_notificaciones_cliente_leida
                ON notificaciones_cliente (leida)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_notificaciones_cliente_emergencia_id
                ON notificaciones_cliente (emergencia_id)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_tracking_emergencia_created_at
                ON seguimiento_emergencia_tracking (emergencia_id, created_at DESC)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_tracking_mecanico_created_at
                ON seguimiento_emergencia_tracking (mecanico_id, created_at DESC)
                """
            )
        )
        connection.execute(text("ALTER TABLE tokens_recuperacion_password ADD COLUMN IF NOT EXISTS account_type VARCHAR(40)"))
        connection.execute(text("ALTER TABLE tokens_recuperacion_password ADD COLUMN IF NOT EXISTS account_id BIGINT"))
        connection.execute(text("ALTER TABLE tokens_recuperacion_password ADD COLUMN IF NOT EXISTS token_hash VARCHAR(64)"))
        connection.execute(
            text("ALTER TABLE tokens_recuperacion_password ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ")
        )
        connection.execute(text("ALTER TABLE tokens_recuperacion_password ADD COLUMN IF NOT EXISTS used_at TIMESTAMPTZ"))
        connection.execute(
            text(
                "ALTER TABLE tokens_recuperacion_password "
                "ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            )
        )
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS tokens_recuperacion_password_token_hash_key
                ON tokens_recuperacion_password (token_hash)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS tokens_recuperacion_password_account_lookup_idx
                ON tokens_recuperacion_password (account_type, account_id, used_at)
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE reportes_emergencia re
                SET vehiculo_id = v.id
                FROM vehiculos v
                WHERE re.vehiculo_id IS NULL
                  AND re.cliente_id IS NOT NULL
                  AND v.cliente_id = re.cliente_id
                  AND UPPER(COALESCE(re.vehiculo_placa, '')) = UPPER(v.plate)
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'reportes_emergencia_vehiculo_id_fkey'
                    ) THEN
                        ALTER TABLE reportes_emergencia
                        ADD CONSTRAINT reportes_emergencia_vehiculo_id_fkey
                        FOREIGN KEY (vehiculo_id)
                        REFERENCES vehiculos(id)
                        ON DELETE SET NULL;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS reportes_emergencia_vehiculo_id_idx
                ON reportes_emergencia (vehiculo_id)
                """
            )
        )
        connection.execute(text("ALTER TABLE fichas_recepcion ALTER COLUMN recepcionado_por_user_id DROP NOT NULL"))
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_mecanicos_sucursal_id
                ON mecanicos (sucursal_id)
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'reportes_emergencia_cliente_id_fkey'
                    ) THEN
                        ALTER TABLE reportes_emergencia
                        ADD CONSTRAINT reportes_emergencia_cliente_id_fkey
                        FOREIGN KEY (cliente_id)
                        REFERENCES clientes(id)
                        ON DELETE SET NULL;
                    END IF;
                END $$;
                """
            )
        )
        connection.execute(CREATE_SECRETARIAS_TABLE_SQL)
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_secretarias_sucursal_id
                ON secretarias (sucursal_id)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_secretarias_status
                ON secretarias (status)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE OR REPLACE VIEW clients AS
                SELECT * FROM clientes;
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE OR REPLACE VIEW vehicles AS
                SELECT
                    id,
                    cliente_id AS client_id,
                    brand,
                    model,
                    year,
                    plate,
                    color,
                    is_primary,
                    photo_path,
                    photo_url,
                    created_at
                FROM vehiculos;
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE OR REPLACE VIEW workshop_registrations AS
                SELECT
                    id,
                    nombre_taller AS workshop_name,
                    contact_name,
                    phone,
                    email,
                    zone,
                    specialty,
                    approval_status,
                    password_hash,
                    latitude,
                    longitude,
                    timezone,
                    utc_offset_minutes,
                    created_at
                FROM registros_taller;
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE OR REPLACE VIEW emergency_reports AS
                SELECT
                    id,
                    cliente_id AS client_id,
                    vehiculo_id AS vehicle_id,
                    vehiculo_nombre AS vehicle_name,
                    vehiculo_placa AS vehicle_plate,
                    problem_type,
                    price,
                    estado_emergencia AS emergency_status,
                    problem_type_standardized,
                    photo_problem_type_standardized,
                    photo_classification_confidence,
                    photo_classification_error,
                    description,
                    latitude,
                    longitude,
                    address,
                    zone,
                    taller_cercano_id AS nearest_workshop_id,
                    taller_cercano_nombre AS nearest_workshop_name,
                    taller_cercano_especialidad AS nearest_workshop_specialty,
                    taller_cercano_zona AS nearest_workshop_zone,
                    taller_cercano_distancia_metros AS nearest_workshop_distance_meters,
                    audio_duration_seconds,
                    audio_transcript,
                    audio_transcript_status,
                    audio_transcript_error,
                    photo_paths,
                    photo_urls,
                    audio_path,
                    audio_url,
                    created_at
                FROM reportes_emergencia;
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE OR REPLACE VIEW emergency_assignments AS
                SELECT
                    id,
                    reporte_emergencia_id AS emergency_report_id,
                    taller_id AS workshop_id,
                    mecanico_id,
                    estado_asignacion AS assignment_status,
                    created_at,
                    updated_at
                FROM asignaciones_emergencia;
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE OR REPLACE VIEW device_fcm_tokens AS
                SELECT * FROM tokens_fcm_dispositivo;
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE OR REPLACE VIEW password_reset_tokens AS
                SELECT * FROM tokens_recuperacion_password;
                """
            )
        )
        connection.execute(
            text("ALTER TABLE asignaciones_emergencia ALTER COLUMN taller_id DROP NOT NULL")
        )


def create_workshop_registration(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        result = connection.execute(INSERT_WORKSHOP_SQL, payload)
        row = result.mappings().one()
    return dict(row)


def list_workshop_registrations() -> list[dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(LIST_WORKSHOPS_SQL)
        rows = result.mappings().all()
    return [dict(row) for row in rows]


def update_workshop_registration(workshop_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(UPDATE_WORKSHOP_SQL, {"id": workshop_id, **payload})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def update_workshop_approval_status(workshop_id: int, approval_status: str) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(
            UPDATE_WORKSHOP_APPROVAL_STATUS_SQL,
            {
                "id": workshop_id,
                "approval_status": approval_status,
                "password_hash": None,
            },
        )
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def get_workshop_by_email(email: str) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(GET_WORKSHOP_BY_EMAIL_SQL, {"email": email})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def get_workshop_by_id(workshop_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(GET_WORKSHOP_BY_ID_SQL, {"id": workshop_id})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def update_workshop_approval_status_with_password(
    workshop_id: int,
    approval_status: str,
    password_hash: str | None,
) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(
            UPDATE_WORKSHOP_APPROVAL_STATUS_SQL,
            {
                "id": workshop_id,
                "approval_status": approval_status,
                "password_hash": password_hash,
            },
        )
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def update_workshop_password(workshop_id: int, password_hash: str) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(
            UPDATE_WORKSHOP_PASSWORD_SQL,
            {
                "id": workshop_id,
                "password_hash": password_hash,
            },
        )
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def delete_workshop_registration(workshop_id: int) -> bool:
    with engine.begin() as connection:
        result = connection.execute(DELETE_WORKSHOP_SQL, {"id": workshop_id})
        row = result.mappings().one_or_none()
    return row is not None


def create_sucursal(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        result = connection.execute(INSERT_SUCURSAL_SQL, payload)
        row = result.mappings().one()
    return dict(row)


def list_sucursales(estado: str | None = None) -> list[dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(LIST_SUCURSALES_SQL, {"estado": estado})
        rows = result.mappings().all()

    result_list = []
    for row in rows:
        d = dict(row)
        mecanicos_count = int(d.get("mecanicos_activos_count") or 0)
        secretarias_count = int(d.get("secretarias_activas_count") or 0)
        lat = d.get("latitud")
        lng = d.get("longitud")
        es_activo = str(d.get("estado", "")) == "ACTIVO"

        if not es_activo:
            d["operativa"] = False
            d["motivo_no_operativa"] = "Sucursal inactiva"
        elif lat is None or lng is None:
            d["operativa"] = False
            d["motivo_no_operativa"] = "Sin coordenadas"
        elif mecanicos_count == 0:
            d["operativa"] = False
            d["motivo_no_operativa"] = "Sin mecánico activo"
        elif secretarias_count == 0:
            d["operativa"] = False
            d["motivo_no_operativa"] = "Sin secretaria activa"
        else:
            d["operativa"] = True
            d["motivo_no_operativa"] = None

        result_list.append(d)

    return result_list


def count_active_sucursales() -> int:
    with engine.connect() as connection:
        result = connection.execute(COUNT_ACTIVE_SUCURSALES_SQL)
        row = result.mappings().one()
    return int(row["total"])


def list_sucursales_for_mobile() -> list[dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(LIST_MOBILE_SUCURSALES_SQL)
        rows = result.mappings().all()
    return [dict(row) for row in rows]


def get_sucursal_by_id(sucursal_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(GET_SUCURSAL_BY_ID_SQL, {"id": sucursal_id})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def update_sucursal(sucursal_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(UPDATE_SUCURSAL_SQL, {"id": sucursal_id, **payload})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def update_sucursal_estado(sucursal_id: int, estado: str) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(UPDATE_SUCURSAL_ESTADO_SQL, {"id": sucursal_id, "estado": estado})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def delete_sucursal(sucursal_id: int) -> bool:
    updated = update_sucursal_estado(sucursal_id, "INACTIVO")
    return updated is not None


def list_secretarias() -> list[dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(LIST_SECRETARIAS_SQL)
        rows = result.mappings().all()
    return [dict(row) for row in rows]


def get_secretaria_by_id(secretaria_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(GET_SECRETARIA_BY_ID_SQL, {"id": secretaria_id})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def get_secretaria_by_cliente_id(cliente_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(GET_SECRETARIA_BY_CLIENTE_ID_SQL, {"cliente_id": cliente_id})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def create_secretaria(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        # 1. Crear registro en clientes
        cliente_result = connection.execute(
            text(
                """
                INSERT INTO clientes (
                    identity_card, full_name, email, phone,
                    password_hash, role, status, accepted_terms
                )
                VALUES (
                    :identity_card, :full_name, :email, :phone,
                    :password_hash, 'secretaria', 'active', TRUE
                )
                RETURNING id, full_name, email, phone
                """
            ),
            {
                "identity_card": payload["identity_card"],
                "full_name": payload["full_name"],
                "email": payload["email"],
                "phone": payload.get("phone") or "",
                "password_hash": payload["password_hash"],
            },
        )
        cliente_row = cliente_result.mappings().one()
        cliente_id = int(cliente_row["id"])

        # 2. Crear registro en secretarias
        sec_result = connection.execute(
            text(
                """
                INSERT INTO secretarias (cliente_id, sucursal_id, status)
                VALUES (:cliente_id, :sucursal_id, 'activo')
                RETURNING id, cliente_id, sucursal_id, status, created_at, updated_at
                """
            ),
            {"cliente_id": cliente_id, "sucursal_id": payload["sucursal_id"]},
        )
        sec_row = sec_result.mappings().one()

        # 3. Obtener datos completos con JOIN
        full_result = connection.execute(
            GET_SECRETARIA_BY_ID_SQL,
            {"id": int(sec_row["id"])},
        )
        full_row = full_result.mappings().one()
    return dict(full_row)


def update_secretaria(secretaria_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        # Obtener cliente_id
        sec = connection.execute(
            text("SELECT cliente_id FROM secretarias WHERE id = :id"),
            {"id": secretaria_id},
        ).mappings().one_or_none()

        if not sec:
            return None

        cliente_id = int(sec["cliente_id"])

        # Actualizar clientes
        connection.execute(
            text(
                """
                UPDATE clientes
                SET
                    full_name = :full_name,
                    phone = :phone,
                    password_hash = COALESCE(:password_hash, password_hash),
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {
                "full_name": payload["full_name"],
                "phone": payload.get("phone") or "",
                "password_hash": payload.get("password_hash"),
                "id": cliente_id,
            },
        )

        # Actualizar secretarias
        connection.execute(
            text(
                """
                UPDATE secretarias
                SET sucursal_id = :sucursal_id, updated_at = NOW()
                WHERE id = :id
                """
            ),
            {"sucursal_id": payload["sucursal_id"], "id": secretaria_id},
        )

        # Obtener datos completos
        full_result = connection.execute(GET_SECRETARIA_BY_ID_SQL, {"id": secretaria_id})
        full_row = full_result.mappings().one_or_none()
    return dict(full_row) if full_row else None


def update_secretaria_status(secretaria_id: int, status: str) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(
            UPDATE_SECRETARIA_STATUS_SQL,
            {"id": secretaria_id, "status": status},
        )
        row = result.mappings().one_or_none()
        if not row:
            return None
        full_result = connection.execute(GET_SECRETARIA_BY_ID_SQL, {"id": secretaria_id})
        full_row = full_result.mappings().one_or_none()
    return dict(full_row) if full_row else None


def delete_secretaria(secretaria_id: int) -> dict[str, object] | None:
    return update_secretaria_status(secretaria_id, "inactivo")


def create_mecanico(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        result = connection.execute(INSERT_MECANICO_SQL, payload)
        row = result.mappings().one()
    return dict(row)


def list_mecanicos() -> list[dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(LIST_MECANICOS_SQL)
        rows = result.mappings().all()
    return [dict(row) for row in rows]


def list_mecanicos_by_workshop(workshop_id: int) -> list[dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(LIST_MECANICOS_BY_WORKSHOP_SQL, {"workshop_id": workshop_id})
        rows = result.mappings().all()
    return [dict(row) for row in rows]


def get_mecanico_by_workshop(mecanico_id: int, workshop_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(
            GET_MECANICO_BY_WORKSHOP_SQL,
            {"id": mecanico_id, "workshop_id": workshop_id},
        )
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def get_mecanico_by_id(mecanico_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(GET_MECANICO_SQL, {"id": mecanico_id})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def update_mecanico(mecanico_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(UPDATE_MECANICO_SQL, {"id": mecanico_id, **payload})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def update_mecanico_status(mecanico_id: int, status: str) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(
            UPDATE_MECANICO_STATUS_SQL,
            {"id": mecanico_id, "status": status},
        )
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def update_mecanico_for_workshop(
    mecanico_id: int,
    workshop_id: int,
    payload: Mapping[str, object],
) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(
            UPDATE_MECANICO_BY_WORKSHOP_SQL,
            {"id": mecanico_id, "workshop_id": workshop_id, **payload},
        )
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def delete_mecanico(mecanico_id: int) -> bool:
    with engine.begin() as connection:
        result = connection.execute(DELETE_MECANICO_SQL, {"id": mecanico_id})
        row = result.mappings().one_or_none()
    return row is not None


def delete_mecanico_for_workshop(mecanico_id: int, workshop_id: int) -> bool:
    with engine.begin() as connection:
        result = connection.execute(
            DELETE_MECANICO_BY_WORKSHOP_SQL,
            {"id": mecanico_id, "workshop_id": workshop_id},
        )
        row = result.mappings().one_or_none()
    return row is not None


def create_client(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        result = connection.execute(INSERT_CLIENT_SQL, payload)
        row = result.mappings().one()
    return dict(row)


def list_clients() -> list[dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(LIST_CLIENTS_SQL)
        rows = result.mappings().all()
    return [dict(row) for row in rows]


def get_client_by_email(email: str) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(GET_CLIENT_BY_EMAIL_SQL, {"email": email})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def get_client_by_id(client_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(GET_CLIENT_BY_ID_SQL, {"id": client_id})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def update_client_status(client_id: int, status: str) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(UPDATE_CLIENT_STATUS_SQL, {"id": client_id, "status": status})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def update_client(client_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(UPDATE_CLIENT_SQL, {"id": client_id, **payload})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def update_client_password(client_id: int, password_hash: str) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(
            UPDATE_CLIENT_PASSWORD_SQL,
            {"id": client_id, "password_hash": password_hash},
        )
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def delete_client(client_id: int) -> bool:
    with engine.begin() as connection:
        connection.execute(DELETE_CLIENT_VEHICLES_SQL, {"client_id": client_id})
        result = connection.execute(DELETE_CLIENT_SQL, {"id": client_id})
        row = result.mappings().one_or_none()
    return row is not None


def create_vehicle(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        result = connection.execute(INSERT_VEHICLE_SQL, payload)
        row = result.mappings().one()
    return dict(row)


def list_vehicles(client_id: int) -> list[dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(LIST_VEHICLES_SQL, {"client_id": client_id})
        rows = result.mappings().all()
    return [dict(row) for row in rows]


def get_vehicle_by_id(vehicle_id: int, client_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(GET_VEHICLE_BY_ID_SQL, {"id": vehicle_id, "client_id": client_id})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def get_vehicle_by_any_id(vehicle_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(GET_VEHICLE_BY_ANY_ID_SQL, {"id": vehicle_id})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def get_vehicle_by_client_and_plate(client_id: int, plate: str) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(
            GET_VEHICLE_BY_CLIENT_AND_PLATE_SQL,
            {"client_id": client_id, "plate": plate},
        )
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def count_client_vehicles(client_id: int) -> int:
    with engine.connect() as connection:
        result = connection.execute(COUNT_CLIENT_VEHICLES_SQL, {"client_id": client_id})
        row = result.mappings().one()
    return int(row["total"])


def update_vehicle(vehicle_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(UPDATE_VEHICLE_SQL, {"id": vehicle_id, **payload})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def delete_vehicle(vehicle_id: int, client_id: int) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(DELETE_VEHICLE_SQL, {"id": vehicle_id, "client_id": client_id})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def create_emergency_report(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        result = connection.execute(INSERT_EMERGENCY_REPORT_SQL, payload)
        row = result.mappings().one()
    return dict(row)


def list_emergency_reports(
    *,
    nearest_workshop_id: int | None = None,
    secretaria_sucursal_id: int | None = None,
    emergency_status: str | None = None,
) -> list[dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(
            LIST_EMERGENCY_REPORTS_SQL,
            {
                "nearest_workshop_id": nearest_workshop_id,
                "secretaria_sucursal_id": secretaria_sucursal_id,
                "emergency_status": emergency_status,
            },
        )
        rows = result.mappings().all()
    return [dict(row) for row in rows]


def get_mobile_emergency_tracking(
    report_id: int,
    client_id: int,
) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(
            GET_MOBILE_EMERGENCY_TRACKING_SQL,
            {"report_id": report_id, "client_id": client_id},
        )
        row = result.mappings().one_or_none()
    return dict(row) if row is not None else None


def update_emergency_status(
    report_id: int,
    emergency_status: str,
    *,
    nearest_workshop_id: int | None = None,
) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(
            UPDATE_EMERGENCY_STATUS_SQL,
            {
                "report_id": report_id,
                "emergency_status": emergency_status,
                "nearest_workshop_id": nearest_workshop_id,
            },
        )
        row = result.mappings().one_or_none()

    return dict(row) if row is not None else None


def accept_emergency_report(
    report_id: int,
    *,
    nearest_workshop_id: int | None,
    notification_payload: Mapping[str, object] | None = None,
) -> tuple[dict[str, object] | None, dict[str, object] | None, bool]:
    serialized_notification_payload = None
    if notification_payload is not None:
        serialized_notification_payload = dict(notification_payload)
        metadata = serialized_notification_payload.get("metadata")
        if metadata is not None and not isinstance(metadata, str):
            serialized_notification_payload["metadata"] = json.dumps(metadata, ensure_ascii=True)

    with engine.begin() as connection:
        current_row = connection.execute(
            GET_EMERGENCY_REPORT_FOR_ACCEPT_SQL,
            {
                "report_id": report_id,
                "nearest_workshop_id": nearest_workshop_id,
            },
        ).mappings().one_or_none()

        if current_row is None:
            return None, None, False

        was_already_active = current_row.get("emergency_status") == "activo"

        if was_already_active:
            report_row = connection.execute(
                GET_EMERGENCY_REPORT_BY_ID_SQL,
                {"report_id": report_id},
            ).mappings().one()
            return dict(report_row), None, False

        if (
            serialized_notification_payload is not None
            and serialized_notification_payload.get("cliente_id") is None
            and current_row.get("client_id") is not None
        ):
            serialized_notification_payload["cliente_id"] = int(current_row["client_id"])

        updated_row = connection.execute(
            UPDATE_EMERGENCY_STATUS_SQL,
            {
                "report_id": report_id,
                "emergency_status": "activo",
                "nearest_workshop_id": nearest_workshop_id,
            },
        ).mappings().one_or_none()

        if updated_row is None:
            return None, None, False

        notification_row = None
        if (
            serialized_notification_payload is not None
            and serialized_notification_payload.get("cliente_id") is not None
        ):
            notification_result = connection.execute(
                INSERT_CLIENT_NOTIFICATION_SQL,
                serialized_notification_payload,
            )
            notification_row = notification_result.mappings().one()

    return dict(updated_row), dict(notification_row) if notification_row is not None else None, True


def get_emergency_report_by_id(report_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(GET_EMERGENCY_REPORT_BY_ID_SQL, {"report_id": report_id})
        row = result.mappings().one_or_none()
    return dict(row) if row is not None else None


def get_emergency_tracking_context(emergency_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(
            GET_EMERGENCY_TRACKING_CONTEXT_SQL,
            {"emergency_id": emergency_id},
        )
        row = result.mappings().one_or_none()
    return dict(row) if row is not None else None


def list_emergency_tracking_events(emergency_id: int) -> list[dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(
            LIST_EMERGENCY_TRACKING_EVENTS_SQL,
            {"emergency_id": emergency_id},
        )
        rows = result.mappings().all()
    return [dict(row) for row in rows]


def create_emergency_tracking_event(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        result = connection.execute(INSERT_EMERGENCY_TRACKING_EVENT_SQL, payload)
        row = result.mappings().one()
    return dict(row)


def create_client_notification(payload: Mapping[str, object]) -> dict[str, object]:
    serialized_payload = dict(payload)
    metadata = serialized_payload.get("metadata")
    if metadata is not None and not isinstance(metadata, str):
        serialized_payload["metadata"] = json.dumps(metadata, ensure_ascii=True)

    with engine.begin() as connection:
        result = connection.execute(INSERT_CLIENT_NOTIFICATION_SQL, serialized_payload)
        row = result.mappings().one()
    return dict(row)


def reject_emergency_report(
    report_id: int,
    *,
    rejection_reason: str,
    rejected_by_user_id: int | None,
    notification_payload: Mapping[str, object] | None = None,
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    serialized_notification_payload = None
    if notification_payload is not None:
        serialized_notification_payload = dict(notification_payload)
        metadata = serialized_notification_payload.get("metadata")
        if metadata is not None and not isinstance(metadata, str):
            serialized_notification_payload["metadata"] = json.dumps(metadata, ensure_ascii=True)

    with engine.begin() as connection:
        result = connection.execute(
            REJECT_EMERGENCY_REPORT_SQL,
            {
                "report_id": report_id,
                "rejection_reason": rejection_reason,
                "rejected_by_user_id": rejected_by_user_id,
            },
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None, None

        notification_row = None
        if serialized_notification_payload is not None:
            notification_result = connection.execute(INSERT_CLIENT_NOTIFICATION_SQL, serialized_notification_payload)
            notification_row = notification_result.mappings().one()

    return dict(row), dict(notification_row) if notification_row is not None else None


def assign_emergency_mecanico(
    report_id: int,
    workshop_id: int,
    mecanico_id: int,
) -> dict[str, object]:
    with engine.begin() as connection:
        result = connection.execute(
            ASSIGN_EMERGENCY_MECANICO_SQL,
            {
                "report_id": report_id,
                "workshop_id": workshop_id,
                "mecanico_id": mecanico_id,
            },
        )
        row = result.mappings().one()
        connection.execute(
            UPDATE_MECANICO_STATUS_SQL,
            {"id": mecanico_id, "status": "ocupado"},
        )

    return dict(row)


def assign_emergency_mecanico_with_notification(
    report_id: int,
    workshop_id: int | None,
    mecanico_id: int,
    *,
    report_scope_workshop_id: int | None = None,
    notification_payload: Mapping[str, object] | None = None,
) -> tuple[dict[str, object] | None, dict[str, object] | None, bool]:
    serialized_notification_payload = None
    if notification_payload is not None:
        serialized_notification_payload = dict(notification_payload)
        metadata = serialized_notification_payload.get("metadata")
        if metadata is not None and not isinstance(metadata, str):
            serialized_notification_payload["metadata"] = json.dumps(metadata, ensure_ascii=True)

    with engine.begin() as connection:
        current_row = connection.execute(
            GET_EMERGENCY_REPORT_FOR_ASSIGNMENT_SQL,
            {
                "report_id": report_id,
                "nearest_workshop_id": report_scope_workshop_id,
            },
        ).mappings().one_or_none()

        if current_row is None:
            return None, None, False

        current_assigned_mecanico_id = current_row.get("assigned_mecanico_id")
        changed_assignment = int(current_assigned_mecanico_id or 0) != mecanico_id

        assignment_result = connection.execute(
            ASSIGN_EMERGENCY_MECANICO_SQL,
            {
                "report_id": report_id,
                "workshop_id": workshop_id,
                "mecanico_id": mecanico_id,
            },
        )
        assignment_row = assignment_result.mappings().one()
        connection.execute(
            UPDATE_MECANICO_STATUS_SQL,
            {"id": mecanico_id, "status": "ocupado"},
        )

        notification_row = None
        if (
            changed_assignment
            and serialized_notification_payload is not None
            and serialized_notification_payload.get("cliente_id") is None
            and current_row.get("client_id") is not None
        ):
            serialized_notification_payload["cliente_id"] = int(current_row["client_id"])

        if (
            changed_assignment
            and serialized_notification_payload is not None
            and serialized_notification_payload.get("cliente_id") is not None
        ):
            notification_result = connection.execute(
                INSERT_CLIENT_NOTIFICATION_SQL,
                serialized_notification_payload,
            )
            notification_row = notification_result.mappings().one()

    return (
        dict(assignment_row),
        dict(notification_row) if notification_row is not None else None,
        changed_assignment,
    )


def create_technician(payload: Mapping[str, object]) -> dict[str, object]:
    return create_mecanico(payload)


def list_technicians() -> list[dict[str, object]]:
    return list_mecanicos()


def list_technicians_by_workshop(workshop_id: int) -> list[dict[str, object]]:
    return list_mecanicos_by_workshop(workshop_id)


def get_technician_by_workshop(technician_id: int, workshop_id: int) -> dict[str, object] | None:
    return get_mecanico_by_workshop(technician_id, workshop_id)


def update_technician(technician_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    return update_mecanico(technician_id, payload)


def update_technician_status(technician_id: int, status: str) -> dict[str, object] | None:
    return update_mecanico_status(technician_id, status)


def update_technician_for_workshop(
    technician_id: int,
    workshop_id: int,
    payload: Mapping[str, object],
) -> dict[str, object] | None:
    return update_mecanico_for_workshop(technician_id, workshop_id, payload)


def delete_technician(technician_id: int) -> bool:
    return delete_mecanico(technician_id)


def delete_technician_for_workshop(technician_id: int, workshop_id: int) -> bool:
    return delete_mecanico_for_workshop(technician_id, workshop_id)


def assign_emergency_technician(
    report_id: int,
    workshop_id: int,
    technician_id: int,
) -> dict[str, object]:
    return assign_emergency_mecanico(report_id, workshop_id, technician_id)


def delete_emergency_report(
    report_id: int,
    *,
    nearest_workshop_id: int | None = None,
) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(
            DELETE_EMERGENCY_REPORT_SQL,
            {
                "report_id": report_id,
                "nearest_workshop_id": nearest_workshop_id,
            },
        )
        row = result.mappings().one_or_none()

    return dict(row) if row is not None else None


def upsert_device_fcm_token(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        result = connection.execute(UPSERT_DEVICE_FCM_TOKEN_SQL, payload)
        row = result.mappings().one()
    return dict(row)


def list_active_device_fcm_tokens(user_id: int) -> list[dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(LIST_ACTIVE_DEVICE_FCM_TOKENS_SQL, {"user_id": user_id})
        rows = result.mappings().all()
    return [dict(row) for row in rows]


def list_client_notifications(cliente_id: int) -> list[dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(LIST_CLIENT_NOTIFICATIONS_SQL, {"cliente_id": cliente_id})
        rows = result.mappings().all()
    return [dict(row) for row in rows]


def mark_client_notification_read(notification_id: int, cliente_id: int) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(
            MARK_CLIENT_NOTIFICATION_READ_SQL,
            {"notification_id": notification_id, "cliente_id": cliente_id},
        )
        row = result.mappings().one_or_none()
    return dict(row) if row is not None else None


def count_unread_client_notifications(cliente_id: int) -> int:
    with engine.connect() as connection:
        result = connection.execute(COUNT_UNREAD_CLIENT_NOTIFICATIONS_SQL, {"cliente_id": cliente_id})
        row = result.mappings().one()
    return int(row["unread_count"])


def deactivate_client_fcm_token(user_id: int, fcm_token: str) -> bool:
    with engine.begin() as connection:
        result = connection.execute(
            DEACTIVATE_CLIENT_FCM_TOKEN_SQL,
            {"user_id": user_id, "fcm_token": fcm_token},
        )
        row = result.mappings().one_or_none()
    return row is not None


def upsert_workshop_fcm_token(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        result = connection.execute(UPSERT_WORKSHOP_FCM_TOKEN_SQL, payload)
        row = result.mappings().one()
    return dict(row)


def list_active_workshop_fcm_tokens(workshop_id: int) -> list[dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(
            LIST_ACTIVE_WORKSHOP_FCM_TOKENS_SQL,
            {"workshop_id": workshop_id},
        )
        rows = result.mappings().all()
    return [dict(row) for row in rows]


def deactivate_workshop_fcm_token(workshop_id: int, fcm_token: str) -> bool:
    with engine.begin() as connection:
        result = connection.execute(
            DEACTIVATE_WORKSHOP_FCM_TOKEN_SQL,
            {"workshop_id": workshop_id, "fcm_token": fcm_token},
        )
        row = result.mappings().one_or_none()
    return row is not None


def create_password_reset_token_record(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        result = connection.execute(INSERT_PASSWORD_RESET_TOKEN_SQL, payload)
        row = result.mappings().one()
    return dict(row)


def get_password_reset_token_by_hash(token_hash: str) -> dict[str, object] | None:
    with engine.connect() as connection:
        result = connection.execute(GET_PASSWORD_RESET_TOKEN_BY_HASH_SQL, {"token_hash": token_hash})
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def mark_password_reset_token_used_record(token_id: int, used_at: object) -> dict[str, object] | None:
    with engine.begin() as connection:
        result = connection.execute(
            MARK_PASSWORD_RESET_TOKEN_USED_SQL,
            {"id": token_id, "used_at": used_at},
        )
        row = result.mappings().one_or_none()
    return dict(row) if row else None


def _normalize_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    return [dict(row) for row in rows]


def _upsert_recepcion_client(connection, payload: Mapping[str, object]) -> dict[str, object]:
    existing = None
    mobile_client_id = payload.get("mobile_client_id")
    if mobile_client_id is not None:
        existing = connection.execute(
            GET_RECEPCION_CLIENTE_BY_MOBILE_CLIENT_ID_SQL,
            {"mobile_client_id": mobile_client_id},
        ).mappings().one_or_none()

    if existing is None:
        existing = connection.execute(
            GET_RECEPCION_CLIENTE_BY_IDENTITY_CARD_SQL,
            {"identity_card": payload["identity_card"]},
        ).mappings().one_or_none()

    if existing is None:
        return connection.execute(INSERT_RECEPCION_CLIENTE_SQL, payload).mappings().one()

    return connection.execute(
        UPDATE_RECEPCION_CLIENTE_SQL,
        {"id": existing["id"], **payload},
    ).mappings().one()


def _upsert_recepcion_vehicle(
    connection,
    *,
    cliente_id: int,
    payload: Mapping[str, object],
) -> dict[str, object]:
    existing = connection.execute(
        GET_RECEPCION_VEHICULO_BY_PLATE_SQL,
        {"plate": payload["plate"]},
    ).mappings().one_or_none()

    if existing is None:
        return connection.execute(
            INSERT_RECEPCION_VEHICULO_SQL,
            {"cliente_id": cliente_id, **payload},
        ).mappings().one()

    if int(existing["cliente_id"]) != int(cliente_id):
        raise IntegrityError("vehiculos_recepcion", params=None, orig=None)

    return connection.execute(
        UPDATE_RECEPCION_VEHICULO_SQL,
        {"id": existing["id"], **payload},
    ).mappings().one()


def _list_recepcion_accessories(connection, ficha_id: int) -> list[dict[str, object]]:
    rows = connection.execute(LIST_RECEPCION_ACCESORIOS_SQL, {"ficha_id": ficha_id}).mappings().all()
    return _normalize_rows(rows)


def _list_recepcion_problems(connection, ficha_id: int) -> list[dict[str, object]]:
    rows = connection.execute(LIST_RECEPCION_PROBLEMAS_SQL, {"ficha_id": ficha_id}).mappings().all()
    return _normalize_rows(rows)


def _list_recepcion_diagnostics(connection, ficha_id: int) -> list[dict[str, object]]:
    rows = connection.execute(LIST_RECEPCION_DIAGNOSTICOS_SQL, {"ficha_id": ficha_id}).mappings().all()
    return _normalize_rows(rows)


def _list_recepcion_observations(connection, ficha_id: int) -> list[dict[str, object]]:
    rows = connection.execute(LIST_RECEPCION_OBSERVACIONES_SQL, {"ficha_id": ficha_id}).mappings().all()
    return _normalize_rows(rows)


def _get_recepcion_detail(connection, recepcion_id: int) -> dict[str, object] | None:
    row = connection.execute(GET_RECEPCION_RECORD_SQL, {"id": recepcion_id}).mappings().one_or_none()
    if row is None:
        return None

    detail = dict(row)
    ficha_id = int(detail["id"])
    detail["accesorios"] = _list_recepcion_accessories(connection, ficha_id)
    detail["problemas"] = _list_recepcion_problems(connection, ficha_id)
    detail["diagnosticos"] = _list_recepcion_diagnostics(connection, ficha_id)
    detail["observaciones"] = _list_recepcion_observations(connection, ficha_id)
    return detail


def create_recepcion_record(
    *,
    cliente_payload: Mapping[str, object],
    vehiculo_payload: Mapping[str, object],
    ficha_payload: Mapping[str, object],
    accessories: Sequence[Mapping[str, object]],
    problems: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    with engine.begin() as connection:
        cliente_row = _upsert_recepcion_client(connection, cliente_payload)
        vehiculo_row = _upsert_recepcion_vehicle(
            connection,
            cliente_id=int(cliente_row["id"]),
            payload=vehiculo_payload,
        )
        ficha_row = connection.execute(
            INSERT_RECEPCION_FICHA_SQL,
            {
                **ficha_payload,
                "cliente_id": cliente_row["id"],
                "vehiculo_id": vehiculo_row["id"],
            },
        ).mappings().one()

        ficha_id = int(ficha_row["id"])

        if accessories:
            connection.execute(
                INSERT_RECEPCION_ACCESORIO_SQL,
                [{"ficha_id": ficha_id, **item} for item in accessories],
            )

        if problems:
            connection.execute(
                INSERT_RECEPCION_PROBLEMA_SQL,
                [{"ficha_id": ficha_id, **item} for item in problems],
            )

        detail = _get_recepcion_detail(connection, ficha_id)

    return detail if detail is not None else {}


def list_recepcion_records(
    *,
    status: str | None = None,
    plate: str | None = None,
    codigo_ficha: str | None = None,
    identity_card: str | None = None,
    assigned_mechanic_id: int | None = None,
    visible_mechanic_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict[str, object]], int]:
    params = {
        "status": status,
        "plate": plate,
        "codigo_ficha": codigo_ficha,
        "identity_card": identity_card,
        "assigned_mechanic_id": assigned_mechanic_id,
        "visible_mechanic_id": visible_mechanic_id,
        "limit": limit,
        "offset": offset,
    }
    with engine.connect() as connection:
        rows = connection.execute(LIST_RECEPCION_RECORDS_SQL, params).mappings().all()
        count_row = connection.execute(COUNT_RECEPCION_RECORDS_SQL, params).mappings().one()
    return _normalize_rows(rows), int(count_row["total"])


def get_recepcion_record_by_id(recepcion_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _get_recepcion_detail(connection, recepcion_id)


def get_recepcion_record_by_emergency_id(emergency_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        row = connection.execute(
            GET_RECEPCION_RECORD_BY_EMERGENCY_SQL,
            {"emergency_id": emergency_id},
        ).mappings().one_or_none()
        if row is None:
            return None
        return _get_recepcion_detail(connection, int(row["id"]))


def get_active_recepcion_by_emergency_id(emergency_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        row = connection.execute(
            GET_ACTIVE_RECEPCION_BY_EMERGENCY_SQL,
            {"emergency_id": emergency_id},
        ).mappings().one_or_none()
        if row is None:
            return None
        return _get_recepcion_detail(connection, int(row["id"]))


def update_recepcion_record(
    recepcion_id: int,
    *,
    cliente_payload: Mapping[str, object],
    vehiculo_payload: Mapping[str, object],
    ficha_payload: Mapping[str, object],
    accessories: Sequence[Mapping[str, object]],
    problems: Sequence[Mapping[str, object]],
) -> dict[str, object] | None:
    with engine.begin() as connection:
        ids_row = connection.execute(GET_RECEPCION_IDS_SQL, {"id": recepcion_id}).mappings().one_or_none()
        if ids_row is None:
            return None

        connection.execute(
            UPDATE_RECEPCION_CLIENTE_SQL,
            {"id": ids_row["cliente_id"], **cliente_payload},
        ).mappings().one()
        connection.execute(
            UPDATE_RECEPCION_VEHICULO_SQL,
            {"id": ids_row["vehiculo_id"], **vehiculo_payload},
        ).mappings().one()
        connection.execute(
            UPDATE_RECEPCION_FICHA_SQL,
            {"id": recepcion_id, **ficha_payload},
        ).mappings().one()

        connection.execute(DELETE_RECEPCION_ACCESORIOS_SQL, {"ficha_id": recepcion_id})
        connection.execute(DELETE_RECEPCION_PROBLEMAS_SQL, {"ficha_id": recepcion_id})

        if accessories:
            connection.execute(
                INSERT_RECEPCION_ACCESORIO_SQL,
                [{"ficha_id": recepcion_id, **item} for item in accessories],
            )

        if problems:
            connection.execute(
                INSERT_RECEPCION_PROBLEMA_SQL,
                [{"ficha_id": recepcion_id, **item} for item in problems],
            )

        return _get_recepcion_detail(connection, recepcion_id)


def create_recepcion_diagnostic(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        row = connection.execute(INSERT_RECEPCION_DIAGNOSTICO_SQL, payload).mappings().one()
    return dict(row)


def create_recepcion_observation(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        row = connection.execute(INSERT_RECEPCION_OBSERVACION_SQL, payload).mappings().one()
    return dict(row)


def get_recepcion_status_by_id(recepcion_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        row = connection.execute(GET_RECEPCION_STATUS_SQL, {"id": recepcion_id}).mappings().one_or_none()
    return dict(row) if row is not None else None
