import pytest
from sqlalchemy.orm import Session

from alquilometro_api.core.seguridad import verificar_password
from alquilometro_api.core.tokens import crear_token, validar_token
from alquilometro_api.domain.errores import (
    ConflictoDominio,
    NoAutenticado,
    PermisoInsuficiente,
    ValidacionError,
)
from alquilometro_api.domain.rol import Rol
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.services.auth import ServicioAuth

PASSWORD = 'clave-segura-1'  # noqa: S105


@pytest.fixture
def servicio(sesion: Session) -> ServicioAuth:
    return ServicioAuth(sesion)


def registrar_ana(servicio: ServicioAuth) -> Usuario:
    return servicio.registrar('Ana Pérez', 'ana@example.com', PASSWORD)


# --- registrar ------------------------------------------------------------


def test_registrar_persists_a_buscador_with_a_hashed_password(
    servicio: ServicioAuth, sesion: Session
) -> None:
    usuario = registrar_ana(servicio)

    guardado = sesion.get(Usuario, usuario.id)
    assert guardado is not None
    assert guardado.rol is Rol.BUSCADOR
    assert guardado.password_hash != PASSWORD
    assert verificar_password(PASSWORD, guardado.password_hash)


def test_registrar_normalizes_name_and_email(servicio: ServicioAuth) -> None:
    usuario = servicio.registrar('  Ana  ', '  Ana@Example.COM ', PASSWORD)

    assert usuario.nombre == 'Ana'
    assert usuario.email == 'ana@example.com'


def test_registrar_inmobiliaria_is_allowed(servicio: ServicioAuth) -> None:
    usuario = servicio.registrar(
        'Inmo SA', 'inmo@example.com', PASSWORD, Rol.INMOBILIARIA
    )

    assert usuario.rol is Rol.INMOBILIARIA


def test_registrar_cannot_create_admins(servicio: ServicioAuth) -> None:
    with pytest.raises(PermisoInsuficiente):
        servicio.registrar('Root', 'root@example.com', PASSWORD, Rol.ADMIN)


@pytest.mark.parametrize('email', ['ANA@example.com', ' ana@example.com'])
def test_registrar_duplicate_email_is_a_conflict(
    servicio: ServicioAuth, email: str
) -> None:
    registrar_ana(servicio)

    with pytest.raises(ConflictoDominio):
        servicio.registrar('Otra Ana', email, PASSWORD)


@pytest.mark.parametrize(
    ('nombre', 'email', 'password'),
    [
        ('', 'a@example.com', PASSWORD),
        ('   ', 'a@example.com', PASSWORD),
        ('x' * 101, 'a@example.com', PASSWORD),
        ('Ana', 'sin-arroba', PASSWORD),
        ('Ana', 'a@sin-punto', PASSWORD),
        ('Ana', 'dos@@example.com', PASSWORD),
        ('Ana', 'a@example.com', '1234567'),
        ('Ana', 'a@example.com', ''),
    ],
)
def test_registrar_rejects_invalid_data(
    servicio: ServicioAuth, nombre: str, email: str, password: str
) -> None:
    with pytest.raises(ValidacionError):
        servicio.registrar(nombre, email, password)


# --- autenticar -----------------------------------------------------------


def test_autenticar_returns_a_token_for_the_user(
    servicio: ServicioAuth,
) -> None:
    usuario = registrar_ana(servicio)

    token = servicio.autenticar('ana@example.com', PASSWORD)

    assert validar_token(token) == usuario.id


def test_autenticar_ignores_email_case(servicio: ServicioAuth) -> None:
    registrar_ana(servicio)

    assert servicio.autenticar(' ANA@example.com ', PASSWORD)


def test_autenticar_wrong_password_and_unknown_email_look_the_same(
    servicio: ServicioAuth,
) -> None:
    registrar_ana(servicio)

    with pytest.raises(NoAutenticado) as clave_mala:
        servicio.autenticar('ana@example.com', 'otra-clave-12')
    with pytest.raises(NoAutenticado) as email_inexistente:
        servicio.autenticar('nadie@example.com', PASSWORD)

    assert str(clave_mala.value) == str(email_inexistente.value)


# --- usuario_actual -------------------------------------------------------


def test_usuario_actual_returns_the_token_owner(
    servicio: ServicioAuth,
) -> None:
    usuario = registrar_ana(servicio)
    token = servicio.autenticar('ana@example.com', PASSWORD)

    assert servicio.usuario_actual(token).id == usuario.id


def test_usuario_actual_rejects_garbage(servicio: ServicioAuth) -> None:
    with pytest.raises(NoAutenticado):
        servicio.usuario_actual('no-es-un-token')


def test_usuario_actual_rejects_a_token_of_a_deleted_user(
    servicio: ServicioAuth, sesion: Session
) -> None:
    usuario = registrar_ana(servicio)
    token = crear_token(usuario.id)
    sesion.delete(usuario)
    sesion.commit()

    with pytest.raises(NoAutenticado):
        servicio.usuario_actual(token)


def test_registrar_turns_a_database_duplicate_race_into_a_conflict(
    servicio: ServicioAuth, monkeypatch: pytest.MonkeyPatch
) -> None:
    registrar_ana(servicio)
    # Simula que otro request registró el email entre la consulta y el commit.
    monkeypatch.setattr(servicio, '_buscar_por_email', lambda _email: None)

    with pytest.raises(ConflictoDominio):
        servicio.registrar('Ana bis', 'ana@example.com', PASSWORD)
