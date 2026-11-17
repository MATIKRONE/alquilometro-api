from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import ValidacionError
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.services.usuarios import ServicioUsuarios


@pytest.fixture
def usuario(sesion: Session) -> Usuario:
    usuario = Usuario(
        nombre='Ana',
        email='ana@example.com',
        password_hash='hash',  # noqa: S106
    )
    sesion.add(usuario)
    sesion.commit()
    return usuario


def test_income_is_saved_and_survives_a_reload(
    sesion: Session, usuario: Usuario
) -> None:
    ingreso = Dinero(Decimal('1500000.50'), Moneda.ARS)

    ServicioUsuarios(sesion).actualizar_ingreso_referencia(usuario, ingreso)
    sesion.expire_all()

    assert usuario.ingreso_referencia == ingreso


def test_income_can_be_replaced_and_cleared(
    sesion: Session, usuario: Usuario
) -> None:
    servicio = ServicioUsuarios(sesion)
    servicio.actualizar_ingreso_referencia(
        usuario, Dinero(Decimal(1000), Moneda.ARS)
    )
    servicio.actualizar_ingreso_referencia(
        usuario, Dinero(Decimal(2000), Moneda.USD)
    )
    assert usuario.ingreso_referencia == Dinero(Decimal(2000), Moneda.USD)

    servicio.actualizar_ingreso_referencia(usuario, None)
    sesion.expire_all()

    assert usuario.ingreso_referencia is None


def test_non_positive_income_is_rejected_and_nothing_changes(
    sesion: Session, usuario: Usuario
) -> None:
    servicio = ServicioUsuarios(sesion)
    servicio.actualizar_ingreso_referencia(
        usuario, Dinero(Decimal(1000), Moneda.ARS)
    )

    with pytest.raises(ValidacionError):
        servicio.actualizar_ingreso_referencia(
            usuario, Dinero(Decimal(0), Moneda.ARS)
        )

    assert usuario.ingreso_referencia == Dinero(Decimal(1000), Moneda.ARS)
