from decimal import Decimal

from sqlalchemy import Engine, inspect
from sqlalchemy.orm import Session

from alquilometro_api.models.propiedad import Propiedad
from alquilometro_api.models.publicacion import Publicacion
from alquilometro_api.models.usuario import Usuario


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
