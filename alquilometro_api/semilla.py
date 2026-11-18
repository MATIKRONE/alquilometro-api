"""Datos de ejemplo para la demo: series ICL e IPC, 20 avisos y un admin.

Uso:  poetry run python -m alquilometro_api.semilla
      poetry run python -m alquilometro_api.semilla --csv ICL icl.csv

La segunda forma carga una serie oficial desde un CSV `fecha,valor`.

El ICL es DE EJEMPLO (crece un 2,5% por mes desde enero de 2025). El IPC
usa las variaciones mensuales del INDEC (nivel general) transcriptas a mano:
verificarlas contra la fuente oficial antes de presentarlas como reales, o
reemplazar ambas series con `--csv`. Los avisos de ejemplo pertenecen a un
usuario ADMIN "sistema" sin contraseña utilizable, así que solo los
administradores pueden modificarlos. Para crear un administrador, definir
ADMIN_EMAIL y ADMIN_PASSWORD en el entorno o en el .env antes de correr
el script.
"""

import argparse
import csv
import os
import secrets
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

import alquilometro_api.models  # noqa: F401
from alquilometro_api.core.database import crear_tablas, get_engine
from alquilometro_api.core.seguridad import hashear_password
from alquilometro_api.datos_ejemplo import AVISOS_DE_EJEMPLO, CALLES
from alquilometro_api.domain.ajuste import sumar_meses
from alquilometro_api.domain.errores import ValidacionError
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.domain.rol import Rol
from alquilometro_api.models.publicacion import Publicacion
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.schemas.publicacion import (
    DineroEntrada,
    PropiedadCrear,
    PublicacionCrear,
)
from alquilometro_api.services.indices import RepositorioIndicesDB
from alquilometro_api.services.publicaciones import ServicioPublicaciones

INICIO_SERIE = date(2025, 1, 1)
MESES_DE_SERIE = 24
VALOR_INICIAL = Decimal(100)
VARIACION_MENSUAL = Decimal('1.025')

# IPC nivel general nacional (INDEC), variación mensual en %, desde
# enero de 2024. Base: diciembre de 2023 = 100.
INICIO_IPC = date(2024, 1, 1)
IPC_VARIACIONES = tuple(
    Decimal(v)
    for v in (
        '20.6 13.2 11.0 8.8 4.2 4.6 4.0 4.2 3.5 2.7 2.4 2.7 '
        '2.2 2.4 3.7 2.8 1.5 1.6 1.9 1.9 2.1 2.3'
    ).split()
)

EMAIL_SISTEMA = 'sistema@alquilometro.local'
FUENTE_SEMILLA = 'semilla'


def cargar_icl_de_ejemplo(sesion: Session) -> int:
    """Carga 24 meses de ICL de ejemplo y devuelve cuántos valores cargó."""
    indices = RepositorioIndicesDB(sesion)
    for mes in range(MESES_DE_SERIE):
        valor = (VALOR_INICIAL * VARIACION_MENSUAL**mes).quantize(
            Decimal('0.01')
        )
        indices.cargar('ICL', sumar_meses(INICIO_SERIE, mes), valor)
    return MESES_DE_SERIE


def cargar_ipc_de_ejemplo(sesion: Session) -> int:
    """Carga el IPC como nivel (base dic-2023 = 100) desde las variaciones."""
    indices = RepositorioIndicesDB(sesion)
    nivel = VALOR_INICIAL
    for mes, variacion in enumerate(IPC_VARIACIONES):
        nivel = (nivel * (1 + variacion / 100)).quantize(Decimal('0.01'))
        indices.cargar('IPC', sumar_meses(INICIO_IPC, mes), nivel)
    return len(IPC_VARIACIONES)


def cargar_serie_desde_csv(sesion: Session, serie: str, contenido: str) -> int:
    """Carga filas `fecha,valor` (fecha ISO; el encabezado es opcional)."""
    indices = RepositorioIndicesDB(sesion)
    cargados = 0
    for numero, fila in enumerate(csv.reader(contenido.splitlines()), 1):
        if not fila or not any(campo.strip() for campo in fila):
            continue
        try:
            momento = date.fromisoformat(fila[0].strip())
            valor = Decimal(fila[1].strip())
        except (ValueError, IndexError, InvalidOperation):
            if numero == 1:  # encabezado
                continue
            msg = f'Línea {numero} inválida: se espera fecha ISO,valor.'
            raise ValidacionError(msg) from None
        indices.cargar(serie, momento, valor)
        cargados += 1
    return cargados


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


def crear_usuario_sistema(sesion: Session) -> Usuario:
    """Dueño de los avisos de ejemplo; su contraseña no se puede usar."""
    return crear_admin(sesion, EMAIL_SISTEMA, secrets.token_urlsafe(32))


def _ajuste(texto: str | None) -> dict[str, object]:
    if texto is None:
        return {}
    if texto.startswith('FIJO'):
        return {'tipo_ajuste': 'FIJO', 'tasa_ajuste': Decimal(texto[5:])}
    return {'tipo_ajuste': 'INDICE', 'serie_codigo': texto}


def _dinero(monto: int | None, moneda: Moneda) -> DineroEntrada | None:
    if monto is None:
        return None
    return DineroEntrada(monto=Decimal(monto), moneda=moneda)


def _aviso(numero: int, fila: tuple[object, ...]) -> PublicacionCrear:
    zona, tipo, ambientes, m2, alquiler, extra = fila
    o = dict(extra)  # type: ignore[arg-type]
    moneda = o.get('moneda', Moneda.ARS)
    return PublicacionCrear(
        propiedad=PropiedadCrear(
            direccion=f'{CALLES[numero % len(CALLES)]} {100 + numero * 137}',
            zona=zona,
            tipo=tipo,
            ambientes=ambientes,
            metros_cuadrados=None if m2 is None else Decimal(m2),
            permite_mascotas=o.get('mascotas'),
        ),
        precio_alquiler=_dinero(alquiler, moneda),
        expensas_mensuales=_dinero(o.get('expensas'), moneda),
        abl_mensual=_dinero(o.get('abl'), moneda),
        seguro_caucion=_dinero(o.get('seguro'), moneda),
        deposito=_dinero(o.get('deposito'), moneda),
        comision=_dinero(o.get('comision'), moneda),
        otros_gastos_entrada=_dinero(o.get('otros'), moneda),
        duracion_contrato_meses=o.get('dur'),
        tipo_garantia_aceptada=o.get('garantia'),
        patrocinada=o.get('patrocinada', False),
        fuente=FUENTE_SEMILLA,
        **_ajuste(o.get('ajuste')),
    )


def cargar_publicaciones_de_ejemplo(sesion: Session) -> int:
    """Crea 20 avisos variados (idempotente); devuelve cuántos creó."""
    ya_cargados = sesion.scalars(
        select(Publicacion).where(Publicacion.fuente == FUENTE_SEMILLA)
    ).first()
    if ya_cargados is not None:
        return 0
    sistema = crear_usuario_sistema(sesion)
    servicio = ServicioPublicaciones(sesion)
    for numero, fila in enumerate(AVISOS_DE_EJEMPLO):
        servicio.crear(_aviso(numero, fila), sistema)
    return len(AVISOS_DE_EJEMPLO)


def main(argumentos: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Datos de ejemplo.')
    parser.add_argument(
        '--csv',
        nargs=2,
        metavar=('SERIE', 'ARCHIVO'),
        help='carga una serie oficial desde un CSV fecha,valor',
    )
    args = parser.parse_args(argumentos)
    crear_tablas()
    with Session(get_engine()) as sesion:
        if args.csv:
            serie, ruta = args.csv
            with open(ruta, encoding='utf-8') as archivo:
                cantidad = cargar_serie_desde_csv(
                    sesion, serie, archivo.read()
                )
            print(f'{serie}: {cantidad} valores cargados.')
            return
        print(f'ICL de ejemplo: {cargar_icl_de_ejemplo(sesion)} valores.')
        print(f'IPC (INDEC): {cargar_ipc_de_ejemplo(sesion)} valores.')
        print(f'Avisos de ejemplo: {cargar_publicaciones_de_ejemplo(sesion)}.')
        email = os.environ.get('ADMIN_EMAIL')
        password = os.environ.get('ADMIN_PASSWORD')
        if email and password:
            crear_admin(sesion, email, password)
            print(f'Administrador listo: {email}')


if __name__ == '__main__':
    main()
