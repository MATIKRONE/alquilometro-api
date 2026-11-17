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
from alquilometro_api.services.publicaciones import (
    FiltrosPublicaciones,
    ServicioPublicaciones,
)


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


def datos_publicacion(
    zona: str = 'Caballito',
    ambientes: int = 2,
    precio_alquiler: Decimal = Decimal('650000'),
    moneda: Moneda = Moneda.ARS,
    metros_cuadrados: Decimal | None = Decimal('45'),
) -> PublicacionCrear:
    return PublicacionCrear(
        propiedad=PropiedadCrear(
            direccion='Avenida Rivadavia 5500',
            zona=zona,
            tipo='departamento',
            ambientes=ambientes,
            metros_cuadrados=metros_cuadrados,
        ),
        precio_alquiler=DineroEntrada(
            monto=precio_alquiler,
            moneda=moneda,
        ),
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


def test_listar_filtra_por_zona(
    sesion: Session,
) -> None:
    inmobiliaria = crear_usuario(
        sesion,
        'inmobiliaria@example.com',
        Rol.INMOBILIARIA,
    )
    servicio = ServicioPublicaciones(sesion)

    caballito = servicio.crear(
        datos_publicacion('Caballito'),
        inmobiliaria,
    )
    servicio.crear(datos_publicacion('Palermo'), inmobiliaria)

    assert servicio.listar(
        FiltrosPublicaciones(zona='Caballito'),
    ) == [caballito]


def test_listar_filtra_por_ambientes(
    sesion: Session,
) -> None:
    inmobiliaria = crear_usuario(
        sesion,
        'inmobiliaria@example.com',
        Rol.INMOBILIARIA,
    )
    servicio = ServicioPublicaciones(sesion)

    dos_ambientes = servicio.crear(
        datos_publicacion(ambientes=2),
        inmobiliaria,
    )
    servicio.crear(datos_publicacion(ambientes=3), inmobiliaria)

    assert servicio.listar(
        FiltrosPublicaciones(ambientes=2),
    ) == [dos_ambientes]


def test_listar_filtra_por_rango_de_alquiler_y_moneda(
    sesion: Session,
) -> None:
    inmobiliaria = crear_usuario(
        sesion,
        'inmobiliaria@example.com',
        Rol.INMOBILIARIA,
    )
    servicio = ServicioPublicaciones(sesion)

    dentro_del_rango = servicio.crear(
        datos_publicacion(precio_alquiler=Decimal('650000')),
        inmobiliaria,
    )
    servicio.crear(
        datos_publicacion(precio_alquiler=Decimal('800000')),
        inmobiliaria,
    )
    servicio.crear(
        datos_publicacion(
            precio_alquiler=Decimal('650'),
            moneda=Moneda.USD,
        ),
        inmobiliaria,
    )

    publicaciones = servicio.listar(
        FiltrosPublicaciones(
            alquiler_min=Decimal('600000'),
            alquiler_max=Decimal('700000'),
            moneda=Moneda.ARS,
        ),
    )

    assert publicaciones == [dentro_del_rango]


def test_listar_rechaza_rango_de_alquiler_invertido(
    sesion: Session,
) -> None:
    servicio = ServicioPublicaciones(sesion)

    filtros = FiltrosPublicaciones(
        alquiler_min=Decimal('800000'),
        alquiler_max=Decimal('600000'),
        moneda=Moneda.ARS,
    )

    with pytest.raises(ValidacionError):
        servicio.listar(filtros)


def test_listar_rechaza_rango_de_alquiler_sin_moneda(
    sesion: Session,
) -> None:
    servicio = ServicioPublicaciones(sesion)

    filtros = FiltrosPublicaciones(
        alquiler_min=Decimal('600000'),
    )

    with pytest.raises(ValidacionError):
        servicio.listar(filtros)


def test_listar_filtra_por_rango_de_costo_real(
    sesion: Session,
) -> None:
    inmobiliaria = crear_usuario(
        sesion,
        'inmobiliaria@example.com',
        Rol.INMOBILIARIA,
    )
    servicio = ServicioPublicaciones(sesion)

    costo_en_rango = servicio.crear(
        datos_publicacion(),
        inmobiliaria,
    )

    datos_con_expensas_altas = datos_publicacion()
    datos_con_expensas_altas.expensas_mensuales = DineroEntrada(
        monto=Decimal('200000'),
    )
    servicio.crear(datos_con_expensas_altas, inmobiliaria)

    publicaciones = servicio.listar(
        FiltrosPublicaciones(
            costo_real_min=Decimal('700000'),
            costo_real_max=Decimal('750000'),
            moneda=Moneda.ARS,
        ),
    )

    assert publicaciones == [costo_en_rango]


def test_listar_rechaza_rango_de_costo_real_invertido(
    sesion: Session,
) -> None:
    servicio = ServicioPublicaciones(sesion)

    filtros = FiltrosPublicaciones(
        costo_real_min=Decimal('800000'),
        costo_real_max=Decimal('700000'),
        moneda=Moneda.ARS,
    )

    with pytest.raises(ValidacionError):
        servicio.listar(filtros)


def test_listar_rechaza_rango_de_costo_real_sin_moneda(
    sesion: Session,
) -> None:
    servicio = ServicioPublicaciones(sesion)

    filtros = FiltrosPublicaciones(
        costo_real_min=Decimal('700000'),
    )

    with pytest.raises(ValidacionError):
        servicio.listar(filtros)


def test_listar_ordena_por_alquiler_descendente(
    sesion: Session,
) -> None:
    inmobiliaria = crear_usuario(
        sesion,
        'inmobiliaria@example.com',
        Rol.INMOBILIARIA,
    )
    servicio = ServicioPublicaciones(sesion)

    alquiler_menor = servicio.crear(
        datos_publicacion(precio_alquiler=Decimal('600000')),
        inmobiliaria,
    )
    alquiler_mayor = servicio.crear(
        datos_publicacion(precio_alquiler=Decimal('800000')),
        inmobiliaria,
    )

    publicaciones = servicio.listar(
        FiltrosPublicaciones(
            moneda=Moneda.ARS,
            orden='alquiler',
            descendente=True,
        ),
    )

    assert publicaciones == [alquiler_mayor, alquiler_menor]


def test_listar_ordena_por_costo_real_descendente(
    sesion: Session,
) -> None:
    inmobiliaria = crear_usuario(
        sesion,
        'inmobiliaria@example.com',
        Rol.INMOBILIARIA,
    )
    servicio = ServicioPublicaciones(sesion)

    costo_menor = servicio.crear(
        datos_publicacion(),
        inmobiliaria,
    )

    datos_con_expensas_altas = datos_publicacion()
    datos_con_expensas_altas.expensas_mensuales = DineroEntrada(
        monto=Decimal('200000'),
    )
    costo_mayor = servicio.crear(
        datos_con_expensas_altas,
        inmobiliaria,
    )

    publicaciones = servicio.listar(
        FiltrosPublicaciones(
            moneda=Moneda.ARS,
            orden='costo_real',
            descendente=True,
        ),
    )

    assert publicaciones == [costo_mayor, costo_menor]


def test_listar_ordena_por_precio_m2_descendente(
    sesion: Session,
) -> None:
    inmobiliaria = crear_usuario(
        sesion,
        'inmobiliaria@example.com',
        Rol.INMOBILIARIA,
    )
    servicio = ServicioPublicaciones(sesion)

    precio_m2_mayor = servicio.crear(
        datos_publicacion(
            precio_alquiler=Decimal('650000'),
            metros_cuadrados=Decimal('30'),
        ),
        inmobiliaria,
    )
    precio_m2_menor = servicio.crear(
        datos_publicacion(
            precio_alquiler=Decimal('800000'),
            metros_cuadrados=Decimal('80'),
        ),
        inmobiliaria,
    )
    sin_metros = servicio.crear(
        datos_publicacion(metros_cuadrados=None),
        inmobiliaria,
    )

    publicaciones = servicio.listar(
        FiltrosPublicaciones(
            moneda=Moneda.ARS,
            orden='precio_m2',
            descendente=True,
        ),
    )

    assert publicaciones == [
        precio_m2_mayor,
        precio_m2_menor,
        sin_metros,
    ]


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
