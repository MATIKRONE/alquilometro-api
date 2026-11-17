from decimal import Decimal

from sqlalchemy import Engine, inspect
from sqlalchemy.orm import Session

from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.models.propiedad import Propiedad
from alquilometro_api.models.publicacion import Publicacion
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.schemas.publicacion import PublicacionRespuesta


def test_crear_tablas_incluye_los_modelos_base(engine: Engine) -> None:
    tablas = inspect(engine).get_table_names()

    assert 'usuarios' in tablas
    assert 'propiedades' in tablas
    assert 'publicaciones' in tablas


def test_publicacion_se_relaciona_con_usuario_y_propiedad(
    sesion: Session,
) -> None:
    usuario = Usuario(
        nombre='Ana Pérez',
        email='ana@example.com',
        password_hash='hash-de-pueba',
    )
    propiedad = Propiedad(
        direccion='Avenida Rivadavia 5500',
        zona='Caballito',
        tipo='departamento',
        ambientes=2,
    )
    publicacion = Publicacion(
        publicador=usuario,
        propiedad=propiedad,
        precio_alquiler_monto=Decimal('650000.00'),
        precio_alquiler_moneda='ARS',
    )

    sesion.add_all([usuario, propiedad, publicacion])
    sesion.commit()

    assert publicacion.id is not None
    assert publicacion.publicador is usuario
    assert publicacion.propiedad is propiedad
    assert publicacion in usuario.publicaciones
    assert publicacion in propiedad.publicaciones


def test_publicacion_calcula_el_costo_real_mensual() -> None:
    publicacion = Publicacion(
        propiedad_id=1,
        publicador_id=1,
        precio_alquiler_monto=Decimal('650000'),
        precio_alquiler_moneda='ARS',
        expensas_mensuales_monto=Decimal('85000'),
        expensas_mensuales_moneda='ARS',
        abl_monto=None,
        abl_moneda=None,
        seguro_caucion_monto=Decimal('180000'),
        seguro_caucion_moneda='ARS',
        duracion_contrato_meses=24,
    )

    desglose = publicacion.calcular_costo_real()

    assert desglose.total == Dinero(Decimal('742500'), Moneda.ARS)
    assert desglose.faltantes == ['abl']

    desglose = publicacion.calcular_costo_real()

    assert desglose.total == Dinero(Decimal('742500'), Moneda.ARS)
    assert desglose.faltantes == ['abl']


def test_publicacion_se_convierte_a_respuesta_api() -> None:
    propiedad = Propiedad(
        direccion='Avenida Rivadavia 5500',
        zona='Caballito',
        tipo='departamento',
        ambientes=2,
    )
    publicacion = Publicacion(
        id=1,
        propiedad_id=1,
        publicador_id=1,
        propiedad=propiedad,
        precio_alquiler_monto=Decimal('650000'),
        precio_alquiler_moneda='ARS',
        expensas_mensuales_monto=Decimal('85000'),
        expensas_mensuales_moneda='ARS',
        abl_monto=Decimal('12000'),
        abl_moneda='ARS',
        seguro_caucion_monto=Decimal('30000'),
        seguro_caucion_moneda='ARS',
        deposito_monto=Decimal('650000'),
        deposito_moneda='ARS',
        duracion_contrato_meses=24,
        tipo_garantia_aceptada='Seguro de caución',
        tipo_ajuste='INDICE',
        serie_codigo='ICL',
        patrocinada=False,
        fuente='Carga manual',
    )

    respuesta = PublicacionRespuesta.model_validate(publicacion)

    assert respuesta.id == 1
    assert respuesta.propiedad.zona == 'Caballito'
    assert respuesta.precio_alquiler.monto == Decimal('650000')
    assert respuesta.expensas_mensuales is not None
    assert respuesta.expensas_mensuales.monto == Decimal('85000')
    assert respuesta.abl_mensual is not None
    assert respuesta.abl_mensual.monto == Decimal('12000')
    assert respuesta.seguro_caucion is not None
    assert respuesta.deposito is not None
