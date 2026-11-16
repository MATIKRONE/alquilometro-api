from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import (
    ConflictoDominio,
    RecursoNoEncontrado,
    ValidacionError,
)
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.domain.verificacion import ResultadoVerificacion
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.services.contratos import (
    DatosContrato,
    EstadoAjuste,
    ServicioContratos,
)
from alquilometro_api.services.indices import RepositorioIndicesDB

INICIO = date(2026, 1, 1)
AJUSTES_EN_UN_ANIO = 3


def pesos(monto: str) -> Dinero:
    return Dinero(Decimal(monto), Moneda.ARS)


def crear_usuario(sesion: Session, email: str) -> Usuario:
    usuario = Usuario(
        nombre='Inquilina',
        email=email,
        password_hash='hash-de-prueba',  # noqa: S106
    )
    sesion.add(usuario)
    sesion.commit()
    return usuario


@pytest.fixture
def inquilina(sesion: Session) -> Usuario:
    return crear_usuario(sesion, 'ines@example.com')


@pytest.fixture
def servicio(sesion: Session) -> ServicioContratos:
    """ICL cargado en la base para enero, abril y julio (no octubre)."""
    indices = RepositorioIndicesDB(sesion)
    indices.cargar('ICL', date(2026, 1, 1), Decimal(100))
    indices.cargar('ICL', date(2026, 4, 1), Decimal(130))
    indices.cargar('ICL', date(2026, 7, 1), Decimal(169))
    return ServicioContratos(sesion)


def datos_icl(**cambios: object) -> DatosContrato:
    datos = {
        'fecha_inicio': INICIO,
        'duracion_meses': 12,
        'monto_base': pesos('500000'),
        'tipo_ajuste': 'INDICE',
        'meses_periodicidad': 3,
        'serie_codigo': 'ICL',
    }
    datos.update(cambios)
    return DatosContrato(**datos)  # type: ignore[arg-type]


def test_registra_un_contrato(
    servicio: ServicioContratos, inquilina: Usuario
) -> None:
    contrato = servicio.registrar(inquilina, datos_icl())

    assert contrato.id is not None
    assert contrato.monto_base == pesos('500000')
    assert contrato.fecha_fin == date(2027, 1, 1)
    assert servicio.listar(inquilina) == [contrato]


def test_rechaza_ajuste_fijo_sin_tasa(
    servicio: ServicioContratos, inquilina: Usuario
) -> None:
    with pytest.raises(ValidacionError):
        servicio.registrar(inquilina, datos_icl(tipo_ajuste='FIJO'))


def test_rechaza_periodicidad_mayor_a_la_duracion(
    servicio: ServicioContratos, inquilina: Usuario
) -> None:
    with pytest.raises(ValidacionError):
        servicio.registrar(inquilina, datos_icl(meses_periodicidad=12))


def test_un_contrato_ajeno_no_se_encuentra(
    sesion: Session, servicio: ServicioContratos, inquilina: Usuario
) -> None:
    contrato = servicio.registrar(inquilina, datos_icl())
    otro = crear_usuario(sesion, 'otro@example.com')

    with pytest.raises(RecursoNoEncontrado):
        servicio.obtener(contrato.id, otro)


def test_calendario_marca_pendiente_el_indice_no_publicado(
    servicio: ServicioContratos, inquilina: Usuario
) -> None:
    contrato = servicio.registrar(inquilina, datos_icl())

    calendario = servicio.calendario(contrato)

    assert len(calendario) == AJUSTES_EN_UN_ANIO
    assert [a.estado for a in calendario] == [
        EstadoAjuste.CALCULADO,
        EstadoAjuste.CALCULADO,
        EstadoAjuste.PENDIENTE,
    ]
    segundo = calendario[1].resultado
    assert segundo is not None
    assert segundo.monto_ajustado == pesos('845000')


def test_una_fecha_a_mitad_de_periodo_usa_el_ultimo_ajuste(
    servicio: ServicioContratos, inquilina: Usuario
) -> None:
    contrato = servicio.registrar(inquilina, datos_icl())

    resultado = servicio.calcular_ajuste(contrato, date(2026, 8, 15))

    assert resultado.monto_ajustado == pesos('845000')


def test_verificar_detecta_encadenamiento_y_lo_guarda(
    sesion: Session, servicio: ServicioContratos, inquilina: Usuario
) -> None:
    contrato = servicio.registrar(inquilina, datos_icl())

    registro = servicio.verificar(contrato, date(2026, 7, 1), pesos('1098500'))

    assert registro.resultado_verificacion is ResultadoVerificacion.ENCADENADO
    assert registro.monto_esperado == Decimal('845000.00')
    sesion.refresh(contrato)
    assert contrato.verificaciones == [registro]


def test_no_hay_ajustes_despues_del_final(
    servicio: ServicioContratos, inquilina: Usuario
) -> None:
    contrato = servicio.registrar(inquilina, datos_icl())

    with pytest.raises(ConflictoDominio):
        servicio.calcular_ajuste(contrato, date(2027, 3, 1))
