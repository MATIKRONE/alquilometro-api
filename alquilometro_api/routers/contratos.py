"""RQ5: seguimiento del contrato y verificación de cada ajuste."""

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from alquilometro_api.core.database import get_session
from alquilometro_api.core.dependencias import usuario_actual
from alquilometro_api.domain.ajuste import ResultadoAjuste
from alquilometro_api.models.contrato import (
    ContratoAlquiler,
    VerificacionAjuste,
)
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.schemas.contrato import (
    AjusteProgramadoRespuesta,
    AjusteRespuesta,
    ContratoCrear,
    ContratoRespuesta,
    VerificacionCrear,
    VerificacionRespuesta,
)
from alquilometro_api.services.contratos import (
    AjusteProgramado,
    ServicioContratos,
)

router = APIRouter(prefix='/contratos', tags=['contratos'])


@router.post(
    '',
    response_model=ContratoRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def registrar_contrato(
    datos: ContratoCrear,
    sesion: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
) -> ContratoAlquiler:
    """Registra el contrato firmado del usuario logueado."""
    return ServicioContratos(sesion).registrar(usuario, datos.a_datos())


@router.get('', response_model=list[ContratoRespuesta])
def listar_contratos(
    sesion: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
) -> list[ContratoAlquiler]:
    return ServicioContratos(sesion).listar(usuario)


@router.get('/{contrato_id}', response_model=ContratoRespuesta)
def ver_contrato(
    contrato_id: int,
    sesion: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
) -> ContratoAlquiler:
    return ServicioContratos(sesion).obtener(contrato_id, usuario)


@router.get(
    '/{contrato_id}/calendario',
    response_model=list[AjusteProgramadoRespuesta],
)
def ver_calendario(
    contrato_id: int,
    sesion: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
) -> list[AjusteProgramado]:
    """Todas las fechas de ajuste; PENDIENTE si el índice no salió."""
    servicio = ServicioContratos(sesion)
    return servicio.calendario(servicio.obtener(contrato_id, usuario))


@router.get('/{contrato_id}/ajuste', response_model=AjusteRespuesta)
def calcular_ajuste(
    contrato_id: int,
    fecha: date = Query(description='Fecha a consultar (AAAA-MM-DD).'),
    sesion: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
) -> ResultadoAjuste:
    """Cuánto corresponde pagar en una fecha, con la fórmula aplicada."""
    servicio = ServicioContratos(sesion)
    contrato = servicio.obtener(contrato_id, usuario)
    return servicio.calcular_ajuste(contrato, fecha)


@router.post(
    '/{contrato_id}/verificaciones',
    response_model=VerificacionRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def verificar_ajuste(
    contrato_id: int,
    datos: VerificacionCrear,
    sesion: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
) -> VerificacionAjuste:
    """Compara el monto que informó la inmobiliaria con el correcto."""
    servicio = ServicioContratos(sesion)
    contrato = servicio.obtener(contrato_id, usuario)
    return servicio.verificar(
        contrato, datos.fecha_ajuste, datos.monto_informado.a_dominio()
    )


@router.get(
    '/{contrato_id}/verificaciones',
    response_model=list[VerificacionRespuesta],
)
def ver_historial(
    contrato_id: int,
    sesion: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
) -> list[VerificacionAjuste]:
    """Historial cronológico de verificaciones del contrato."""
    contrato = ServicioContratos(sesion).obtener(contrato_id, usuario)
    return contrato.verificaciones
