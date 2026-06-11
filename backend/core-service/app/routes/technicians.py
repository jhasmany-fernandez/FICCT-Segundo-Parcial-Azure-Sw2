from fastapi import APIRouter, HTTPException, Query, status

from app.config import settings
from app.db import (
    create_mecanico,
    delete_mecanico,
    delete_mecanico_for_workshop,
    list_mecanicos,
    list_mecanicos_by_workshop,
    update_mecanico,
    update_mecanico_for_workshop,
)
from app.schemas import MecanicoCreate, MecanicoResponse

#
# Legacy/non-mounted route module retained for compatibility/reference.
# Active mecanico routes live in backend/app/main.py.
#

# ================================================================
# ARCHIVO: technicians.py
# TIPO: Controlador de tecnicos
# ESTE ARCHIVO SI TIENE METODOS
#
# QUE HACE ESTE ARCHIVO:
# Administra el registro, listado, actualizacion y eliminacion de
# tecnicos, ya sea de forma global o por taller.
# Este archivo actua como controlador del modulo de tecnicos y expone
# las rutas necesarias para que otras capas interactuen con ellos.
#
# CONTROLADORES / METODOS QUE TIENE:
# - register_technician:
#   Registra un tecnico nuevo asociado a un taller.
# - get_technicians:
#   Lista tecnicos de forma general o filtrados por taller.
# - edit_technician:
#   Actualiza los datos de un tecnico.
# - remove_technician:
#   Elimina un tecnico.
# Cada metodo representa una operacion puntual sobre tecnicos.
# ================================================================
router = APIRouter(prefix=settings.api_prefix, tags=["mecanicos"])


# -------------------------------------------------------------------
# LOGICA:
# Aqui se administra la relacion entre tecnicos y talleres, definiendo
# a que taller pertenece cada tecnico y como se actualiza.
# "Logica" aqui significa las reglas para resolver a que taller se
# asocia el tecnico y como restringir consultas o cambios.
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# CONEXION CON EL MOVIL:
# Estos endpoints pueden ser consumidos desde una interfaz movil del
# taller para registrar, listar, editar o eliminar tecnicos.
# La frase indica que el origen de la peticion puede ser una pantalla
# del celular desde donde el taller administra su personal tecnico.
# -------------------------------------------------------------------
# ================================================================
# CONTROLADOR: REGISTRO DE TECNICO
# Atiende la creacion de tecnicos asociados a talleres.
# ================================================================
@router.post(
    "/mecanicos",
    response_model=MecanicoResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/technicians",
    response_model=MecanicoResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def register_mecanico(
    payload: MecanicoCreate,
    workshop_id: int | None = Query(default=None, ge=1),
) -> MecanicoResponse:
    # Este endpoint recibe desde la interfaz del taller los datos del tecnico a registrar.
    # LOGICA: se prioriza el workshop_id recibido por query si existe.
    # Esto permite que el contexto del taller prevalezca sobre el payload si ambos llegan.
    # Permite asociar el tecnico al taller enviado en query o al incluido en el cuerpo de la solicitud.
    # ================================================================
    # METODO: RESOLUCION DEL TALLER
    # Decide a que taller se asociara el tecnico.
    # ================================================================
    target_workshop_id = workshop_id or payload.workshop_id
    mecanico_payload = {
        **payload.model_dump(),
        "workshop_id": target_workshop_id,
    }
    created = create_mecanico(mecanico_payload)
    # ================================================================
    # METODO: RESPUESTA DE REGISTRO
    # Devuelve el tecnico creado en formato de salida.
    # ================================================================
    return MecanicoResponse.model_validate(created)


# ================================================================
# CONTROLADOR: LISTADO DE TECNICOS
# Lista tecnicos globalmente o por taller.
# ================================================================
@router.get(
    "/mecanicos",
    response_model=list[MecanicoResponse],
)
@router.get(
    "/technicians",
    response_model=list[MecanicoResponse],
    include_in_schema=False,
)
def get_mecanicos(workshop_id: int | None = Query(default=None, ge=1)) -> list[MecanicoResponse]:
    # LOGICA: la consulta cambia entre listado global o filtrado por taller.
    # El mismo endpoint sirve para dos vistas distintas segun el parametro recibido.
    # Si llega un taller, filtra sus tecnicos; si no, devuelve el listado completo.
    rows = list_mecanicos_by_workshop(workshop_id) if workshop_id else list_mecanicos()
    # ================================================================
    # METODO: RESPUESTA DE LISTADO
    # Transforma cada tecnico al esquema de salida.
    # ================================================================
    return [MecanicoResponse.model_validate(row) for row in rows]


# ================================================================
# CONTROLADOR: EDICION DE TECNICO
# Actualiza un tecnico existente.
# ================================================================
@router.put(
    "/mecanicos/{mecanico_id}",
    response_model=MecanicoResponse,
)
@router.put(
    "/technicians/{mecanico_id}",
    response_model=MecanicoResponse,
    include_in_schema=False,
)
def edit_mecanico(
    mecanico_id: int,
    payload: MecanicoCreate,
    workshop_id: int | None = Query(default=None, ge=1),
) -> MecanicoResponse:
    # LOGICA: si llega workshop_id por query, solo se permite actualizar dentro de ese taller.
    # Esto ayuda a mantener control sobre que registros puede editar cada contexto.
    # ================================================================
    # METODO: PREPARACION DE ACTUALIZACION
    # Arma el payload y elige la estrategia de actualizacion.
    # ================================================================
    mecanico_payload = payload.model_dump()
    mecanico_payload["workshop_id"] = workshop_id or payload.workshop_id
    # Cuando el taller viene por query, la actualizacion queda restringida a registros de ese mismo taller.
    updated = (
        update_mecanico_for_workshop(mecanico_id, workshop_id, mecanico_payload)
        if workshop_id
        else update_mecanico(mecanico_id, mecanico_payload)
    )

    # ================================================================
    # VALIDACION: TECNICO EXISTENTE
    # AQUI SE HACE ESTA VALIDACION DE EXISTENCIA DEL TECNICO Y PERTENENCIA AL TALLER.
    # ================================================================
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tecnico no encontrado")

    # ================================================================
    # METODO: RESPUESTA DE EDICION
    # Devuelve el tecnico actualizado.
    # ================================================================
    return MecanicoResponse.model_validate(updated)


# ================================================================
# CONTROLADOR: ELIMINACION DE TECNICO
# Elimina un tecnico de forma general o por taller.
# ================================================================
@router.delete(
    "/mecanicos/{mecanico_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@router.delete(
    "/technicians/{mecanico_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
def remove_mecanico(mecanico_id: int, workshop_id: int | None = Query(default=None, ge=1)) -> None:
    # LOGICA: el borrado puede ser general o restringido a un taller concreto.
    # De esa manera se reutiliza la ruta en escenarios administrativos o por taller.
    # Reutiliza dos estrategias de borrado: general o validando pertenencia a un taller especifico.
    deleted = (
        delete_mecanico_for_workshop(mecanico_id, workshop_id)
        if workshop_id
        else delete_mecanico(mecanico_id)
    )

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tecnico no encontrado")
