"""Datos de ejemplo para la demo: una serie ICL y, opcional, un admin.

Uso:  poetry run python -m alquilometro_api.semilla

Los valores son DE EJEMPLO, no la serie oficial del BCRA: crecen un 2,5%
por mes desde enero de 2025 para que los ajustes den números redondos de
seguir. Para crear un administrador, definir ADMIN_EMAIL y ADMIN_PASSWORD
en el entorno o en el .env antes de correr el script.
"""

import os
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import alquilometro_api.models  # noqa: F401
from alquilometro_api.core.database import crear_tablas, get_engine
from alquilometro_api.core.seguridad import hashear_password
from alquilometro_api.domain.ajuste import sumar_meses
from alquilometro_api.domain.rol import Rol
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.services.indices import RepositorioIndicesDB

INICIO_SERIE = date(2025, 1, 1)
MESES_DE_SERIE = 24
VALOR_INICIAL = Decimal(100)
VARIACION_MENSUAL = Decimal('1.025')


def cargar_icl_de_ejemplo(sesion: Session) -> int:
    """Carga 24 meses de ICL de ejemplo y devuelve cuántos valores cargó."""
    indices = RepositorioIndicesDB(sesion)
    for mes in range(MESES_DE_SERIE):
        valor = (VALOR_INICIAL * VARIACION_MENSUAL**mes).quantize(
            Decimal('0.01')
        )
        indices.cargar('ICL', sumar_meses(INICIO_SERIE, mes), valor)
    return MESES_DE_SERIE


def crear_admin(sesion: Session, email: str, password: str) -> Usuario:
    """Crea el administrador si no existe (el registro no permite ese rol)."""
    existente = sesion.scalars(
        select(Usuario).where(Usuario.email == email)
    ).first()
    if existente is not None:
        return existente
    admin = Usuario(
        nombre='Administrador',
        email=email,
        password_hash=hashear_password(password),
        rol=Rol.ADMIN,
    )
    sesion.add(admin)
    sesion.commit()
    return admin


def main() -> None:
    crear_tablas()
    with Session(get_engine()) as sesion:
        cantidad = cargar_icl_de_ejemplo(sesion)
        print(f'ICL de ejemplo: {cantidad} valores cargados.')
        email = os.environ.get('ADMIN_EMAIL')
        password = os.environ.get('ADMIN_PASSWORD')
        if email and password:
            crear_admin(sesion, email, password)
            print(f'Administrador listo: {email}')


if __name__ == '__main__':
    main()
