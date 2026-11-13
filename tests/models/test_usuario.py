from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import ValidacionError
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.domain.rol import Rol
from alquilometro_api.models.usuario import Usuario


def nuevo_usuario(email: str = 'ana@example.com', **extra: object) -> Usuario:
    return Usuario(
        nombre='Ana Pérez',
        email=email,
        password_hash='hash-de-prueba',  # noqa: S106
        **extra,
    )


def test_roles_available() -> None:
    assert {rol.value for rol in Rol} == {
        'BUSCADOR',
        'INMOBILIARIA',
        'ADMIN',
    }


def test_new_user_defaults_to_buscador_without_income(sesion: Session) -> None:
    usuario = nuevo_usuario()
    sesion.add(usuario)
    sesion.commit()
    sesion.refresh(usuario)

    assert usuario.rol is Rol.BUSCADOR
    assert usuario.ingreso_referencia is None


@pytest.mark.parametrize('rol', list(Rol))
def test_every_role_is_persisted_and_read_back(
    sesion: Session, rol: Rol
) -> None:
    sesion.add(nuevo_usuario(rol=rol))
    sesion.commit()
    sesion.expire_all()

    assert sesion.query(Usuario).one().rol is rol


def test_income_roundtrips_as_dinero(sesion: Session) -> None:
    usuario = nuevo_usuario(
        ingreso_referencia=Dinero(Decimal('1200000.50'), Moneda.ARS)
    )
    sesion.add(usuario)
    sesion.commit()
    sesion.expire_all()

    assert usuario.ingreso_referencia == Dinero(
        Decimal('1200000.50'), Moneda.ARS
    )


def test_income_in_usd_keeps_its_currency(sesion: Session) -> None:
    usuario = nuevo_usuario()
    usuario.ingreso_referencia = Dinero(Decimal(2500), Moneda.USD)
    sesion.add(usuario)
    sesion.commit()
    sesion.expire_all()

    assert usuario.ingreso_referencia_moneda == 'USD'
    assert usuario.ingreso_referencia.moneda is Moneda.USD  # type: ignore[union-attr]


def test_income_can_be_cleared() -> None:
    usuario = nuevo_usuario(
        ingreso_referencia=Dinero(Decimal(1000), Moneda.ARS)
    )

    usuario.ingreso_referencia = None

    assert usuario.ingreso_referencia is None
    assert usuario.ingreso_referencia_monto is None
    assert usuario.ingreso_referencia_moneda is None


@pytest.mark.parametrize('monto', [0, -1])
def test_income_must_be_positive(monto: int) -> None:
    usuario = nuevo_usuario()

    with pytest.raises(ValidacionError):
        usuario.ingreso_referencia = Dinero(Decimal(monto), Moneda.ARS)


def test_email_must_be_unique(sesion: Session) -> None:
    sesion.add(nuevo_usuario())
    sesion.commit()
    sesion.add(nuevo_usuario())

    with pytest.raises(IntegrityError):
        sesion.commit()


def test_password_hash_is_required(sesion: Session) -> None:
    sesion.add(Usuario(nombre='Sin clave', email='x@example.com'))

    with pytest.raises(IntegrityError):
        sesion.commit()


def test_income_amount_without_currency_is_rejected_by_the_database(
    sesion: Session,
) -> None:
    sesion.add(nuevo_usuario(ingreso_referencia_monto=Decimal(1000)))

    with pytest.raises(IntegrityError):
        sesion.commit()
