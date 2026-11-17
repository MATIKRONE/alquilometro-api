from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import (
    PermisoInsuficiente,
    RecursoNoEncontrado,
)
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.domain.rol import Rol
from alquilometro_api.models.propiedad import Propiedad
from alquilometro_api.models.publicacion import Publicacion
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.schemas.publicacion import (
    DineroEntrada,
    PropiedadCrear,
    PublicacionCrear,
)
from alquilometro_api.services.publicaciones import ServicioPublicaciones


def usuario(sesion: Session, email: str, rol: Rol) -> Usuario:
    nuevo = Usuario(
        nombre='Prueba',
        email=email,
        password_hash='hash',  # noqa: S106
        rol=rol,
    )
    sesion.add(nuevo)
    sesion.commit()
    return nuevo


def datos(zona: str = 'Caballito', **extra: object) -> PublicacionCrear:
    return PublicacionCrear(
        propiedad=PropiedadCrear(
            direccion='Avenida Rivadavia 5500',
            zona=zona,
            tipo='departamento',
            ambientes=2,
        ),
        precio_alquiler=DineroEntrada(monto=Decimal(650000)),
        expensas_mensuales=DineroEntrada(monto=Decimal(85000)),
        **extra,
    )


@pytest.fixture
def servicio(sesion: Session) -> ServicioPublicaciones:
    return ServicioPublicaciones(sesion)


@pytest.fixture
def duena(sesion: Session) -> Usuario:
    return usuario(sesion, 'duena@example.com', Rol.INMOBILIARIA)


@pytest.fixture
def aviso(servicio: ServicioPublicaciones, duena: Usuario) -> Publicacion:
    return servicio.crear(datos(), duena)


def test_owner_can_replace_every_field(
    servicio: ServicioPublicaciones, duena: Usuario, aviso: Publicacion
) -> None:
    propiedad_id = aviso.propiedad_id

    nuevo = datos(zona='Palermo')
    nuevo.precio_alquiler = DineroEntrada(
        monto=Decimal(700000), moneda=Moneda.ARS
    )
    nuevo.expensas_mensuales = None
    actualizado = servicio.actualizar(aviso.id, nuevo, duena)

    assert actualizado.id == aviso.id
    assert actualizado.propiedad_id == propiedad_id
    assert actualizado.propiedad.zona == 'Palermo'
    assert actualizado.precio_alquiler == Dinero(Decimal(700000), Moneda.ARS)
    assert actualizado.expensas_mensuales is None


def test_update_stores_the_new_entry_cost_concepts(
    servicio: ServicioPublicaciones, duena: Usuario, aviso: Publicacion
) -> None:
    nuevo = datos(
        comision=DineroEntrada(monto=Decimal(650000)),
        otros_gastos_entrada=DineroEntrada(monto=Decimal(40000)),
    )

    actualizado = servicio.actualizar(aviso.id, nuevo, duena)

    assert actualizado.comision == Dinero(Decimal(650000), Moneda.ARS)
    assert actualizado.otros_gastos_entrada == Dinero(
        Decimal(40000), Moneda.ARS
    )


def test_another_inmobiliaria_cannot_update_or_delete(
    servicio: ServicioPublicaciones, sesion: Session, aviso: Publicacion
) -> None:
    ajena = usuario(sesion, 'ajena@example.com', Rol.INMOBILIARIA)

    with pytest.raises(PermisoInsuficiente):
        servicio.actualizar(aviso.id, datos(zona='Hackeada'), ajena)
    with pytest.raises(PermisoInsuficiente):
        servicio.eliminar(aviso.id, ajena)

    assert sesion.get(Publicacion, aviso.id).propiedad.zona == 'Caballito'  # type: ignore[union-attr]


def test_buscador_cannot_update_or_delete(
    servicio: ServicioPublicaciones, sesion: Session, aviso: Publicacion
) -> None:
    buscador = usuario(sesion, 'busca@example.com', Rol.BUSCADOR)

    with pytest.raises(PermisoInsuficiente):
        servicio.actualizar(aviso.id, datos(), buscador)
    with pytest.raises(PermisoInsuficiente):
        servicio.eliminar(aviso.id, buscador)


def test_admin_can_manage_any_listing(
    servicio: ServicioPublicaciones, sesion: Session, aviso: Publicacion
) -> None:
    admin = usuario(sesion, 'admin@example.com', Rol.ADMIN)

    servicio.actualizar(aviso.id, datos(zona='Belgrano'), admin)
    assert aviso.propiedad.zona == 'Belgrano'

    servicio.eliminar(aviso.id, admin)
    assert sesion.get(Publicacion, aviso.id) is None


def test_delete_also_removes_the_orphan_property(
    servicio: ServicioPublicaciones,
    sesion: Session,
    duena: Usuario,
    aviso: Publicacion,
) -> None:
    servicio.eliminar(aviso.id, duena)

    assert sesion.scalar(select(func.count()).select_from(Propiedad)) == 0


def test_delete_keeps_a_property_that_has_other_listings(
    servicio: ServicioPublicaciones,
    sesion: Session,
    duena: Usuario,
    aviso: Publicacion,
) -> None:
    segundo = Publicacion(
        propiedad=aviso.propiedad,
        publicador=duena,
        precio_alquiler_monto=Decimal(1),
        precio_alquiler_moneda='ARS',
    )
    sesion.add(segundo)
    sesion.commit()

    servicio.eliminar(aviso.id, duena)

    assert sesion.scalar(select(func.count()).select_from(Propiedad)) == 1
    assert sesion.get(Publicacion, segundo.id) is not None


def test_missing_listing_is_not_found(
    servicio: ServicioPublicaciones, duena: Usuario
) -> None:
    with pytest.raises(RecursoNoEncontrado):
        servicio.actualizar(999, datos(), duena)
    with pytest.raises(RecursoNoEncontrado):
        servicio.eliminar(999, duena)


def test_entry_cost_separates_concepts_and_lists_missing_ones(
    servicio: ServicioPublicaciones, duena: Usuario
) -> None:
    aviso = servicio.crear(
        datos(
            deposito=DineroEntrada(monto=Decimal(650000)),
            seguro_caucion=DineroEntrada(monto=Decimal(180000)),
        ),
        duena,
    )

    entrada = aviso.calcular_costo_entrada()

    assert entrada.total == Dinero(Decimal(1480000), Moneda.ARS)
    assert entrada.faltantes == ['comision']
