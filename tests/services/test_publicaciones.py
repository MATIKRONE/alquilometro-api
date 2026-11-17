from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import (
    PermisoInsuficiente,
    RecursoNoEncontrado,
    ValidacionError,
)
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.domain.rol import Rol
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.schemas.publicacion import (
    DineroEntrada,
    PropiedadCrear,
    PublicacionCrear,
)
from alquilometro_api.services.publicaciones import ServicioPublicaciones


def crear_usuario(
    sesion: Session,
    email: str,
    rol: Rol,
) -> Usuario:
    usuario = Usuario(
        nombre='Usuario de prueba',
        email=email,
        password_hash='hash-de-prueba',
        rol=rol,
    )
    sesion.add(usuario)
    sesion.commit()
    return usuario


def datos_publicacion() -> PublicacionCrear:
    return PublicacionCrear(
        propiedad=PropiedadCrear(
            direccion='Avenida Rivadavia 5500',
            zona='Caballito',
            tipo='departamento',
            ambientes=2,
        ),
        precio_alquiler=DineroEntrada(monto=Decimal('650000')),
        expensas_mensuales=DineroEntrada(monto=Decimal('85000')),
        abl_mensual=DineroEntrada(monto=Decimal('0')),
    )


def test_inmobiliaria_puede_crear_una_publicacion(
    sesion: Session,
) -> None:
    inmobiliaria = crear_usuario(
        sesion,
        'inmobiliaria@example.com',
        Rol.INMOBILIARIA,
    )
    servicio = ServicioPublicaciones(sesion)

    publicacion = servicio.crear(datos_publicacion(), inmobiliaria)

    assert publicacion.id is not None
    assert publicacion.publicador is inmobiliaria
    assert publicacion.propiedad.zona == 'Caballito'
    assert publicacion.expensas_mensuales_monto == Decimal('85000')
    assert publicacion.abl_monto == Decimal('0')


def test_buscador_no_puede_crear_publicaciones(
    sesion: Session,
) -> None:
    buscador = crear_usuario(
        sesion,
        'buscador@example.com',
        Rol.BUSCADOR,
    )
    servicio = ServicioPublicaciones(sesion)

    with pytest.raises(PermisoInsuficiente):
        servicio.crear(datos_publicacion(), buscador)


def test_listar_devuelve_las_publicaciones_guardadas(
    sesion: Session,
) -> None:
    inmobiliaria = crear_usuario(
        sesion,
        'inmobiliaria@example.com',
        Rol.INMOBILIARIA,
    )
    servicio = ServicioPublicaciones(sesion)

    primera = servicio.crear(datos_publicacion(), inmobiliaria)
    segunda = servicio.crear(datos_publicacion(), inmobiliaria)

    assert servicio.listar() == [primera, segunda]


def test_obtener_publicacion_inexistente_devuelve_404(
    sesion: Session,
) -> None:
    servicio = ServicioPublicaciones(sesion)

    with pytest.raises(RecursoNoEncontrado):
        servicio.obtener(999)


def test_analizar_calcula_el_porcentaje_sobre_el_ingreso(
    sesion: Session,
) -> None:
    inmobiliaria = crear_usuario(
        sesion,
        'inmobiliaria@example.com',
        Rol.INMOBILIARIA,
    )
    inmobiliaria.ingreso_referencia = Dinero(
        Decimal('1500000'),
        Moneda.ARS,
    )
    sesion.commit()

    servicio = ServicioPublicaciones(sesion)
    publicacion = servicio.crear(datos_publicacion(), inmobiliaria)

    analisis = servicio.analizar_para_usuario(
        publicacion.id,
        inmobiliaria,
    )

    assert analisis.porcentaje_ingreso == Decimal('49.00')


def test_analizar_sin_ingreso_referencia_devuelve_error_claro(
    sesion: Session,
) -> None:
    inmobiliaria = crear_usuario(
        sesion,
        'inmobiliaria@example.com',
        Rol.INMOBILIARIA,
    )
    servicio = ServicioPublicaciones(sesion)
    publicacion = servicio.crear(datos_publicacion(), inmobiliaria)

    with pytest.raises(ValidacionError):
        servicio.analizar_para_usuario(publicacion.id, inmobiliaria)
