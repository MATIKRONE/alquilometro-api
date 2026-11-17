from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from alquilometro_api.domain.analisis_economico import AnalisisEconomico
from alquilometro_api.domain.errores import (
    PermisoInsuficiente,
    RecursoNoEncontrado,
    ValidacionError,
)
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.domain.rol import Rol
from alquilometro_api.models.propiedad import Propiedad
from alquilometro_api.models.publicacion import Publicacion
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.schemas.publicacion import (
    DineroEntrada,
    PublicacionCrear,
)


@dataclass
class FiltrosPublicaciones:
    """Criterios opcionales para buscar publicaciones."""

    zona: str | None = None
    ambientes: int | None = None
    permite_mascotas: bool | None = None
    tipo_garantia: str | None = None
    alquiler_min: Decimal | None = None
    alquiler_max: Decimal | None = None
    costo_real_min: Decimal | None = None
    costo_real_max: Decimal | None = None
    moneda: Moneda | None = None
    orden: str | None = None
    descendente: bool = False


class ServicioPublicaciones:
    """Alta y consulta de publicaciones guardadas en la base."""

    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def crear(
        self,
        datos: PublicacionCrear,
        publicador: Usuario,
    ) -> Publicacion:
        if publicador.rol not in {Rol.INMOBILIARIA, Rol.ADMIN}:
            msg = 'Solo una inmobiliaria o un administrador puede publicar.'
            raise PermisoInsuficiente(msg)

        propiedad = Propiedad(**datos.propiedad.model_dump())

        expensas_monto, expensas_moneda = _columnas_dinero(
            datos.expensas_mensuales,
        )
        abl_monto, abl_moneda = _columnas_dinero(datos.abl_mensual)
        seguro_monto, seguro_moneda = _columnas_dinero(
            datos.seguro_caucion,
        )
        deposito_monto, deposito_moneda = _columnas_dinero(datos.deposito)

        publicacion = Publicacion(
            propiedad=propiedad,
            publicador=publicador,
            precio_alquiler_monto=datos.precio_alquiler.monto,
            precio_alquiler_moneda=datos.precio_alquiler.moneda.value,
            expensas_mensuales_monto=expensas_monto,
            expensas_mensuales_moneda=expensas_moneda,
            abl_monto=abl_monto,
            abl_moneda=abl_moneda,
            seguro_caucion_monto=seguro_monto,
            seguro_caucion_moneda=seguro_moneda,
            deposito_monto=deposito_monto,
            deposito_moneda=deposito_moneda,
            duracion_contrato_meses=datos.duracion_contrato_meses,
            tipo_garantia_aceptada=datos.tipo_garantia_aceptada,
            tipo_ajuste=datos.tipo_ajuste,
            tasa_ajuste=datos.tasa_ajuste,
            serie_codigo=datos.serie_codigo,
            patrocinada=datos.patrocinada,
            fuente=datos.fuente,
        )

        self.sesion.add(propiedad)
        self.sesion.add(publicacion)
        self.sesion.commit()
        self.sesion.refresh(publicacion)
        return publicacion

    def listar(
        self,
        filtros: FiltrosPublicaciones | None = None,
    ) -> list[Publicacion]:
        if filtros is None:
            filtros = FiltrosPublicaciones()

        self._validar_filtros(filtros)
        publicaciones = self._consultar_publicaciones(filtros)

        if (
            filtros.costo_real_min is not None
            or filtros.costo_real_max is not None
        ):
            publicaciones = [
                publicacion
                for publicacion in publicaciones
                if _esta_dentro_del_rango_de_costo_real(
                    publicacion,
                    filtros,
                )
            ]

        return self._ordenar_publicaciones(publicaciones, filtros)

    @staticmethod
    def _validar_filtros(
        filtros: FiltrosPublicaciones,
    ) -> None:
        if (
            filtros.alquiler_min is not None
            and filtros.alquiler_max is not None
            and filtros.alquiler_min > filtros.alquiler_max
        ):
            msg = 'El alquiler mínimo no puede ser mayor al máximo.'
            raise ValidacionError(msg)

        if (
            filtros.costo_real_min is not None
            and filtros.costo_real_max is not None
            and filtros.costo_real_min > filtros.costo_real_max
        ):
            msg = 'El costo real mínimo no puede ser mayor al máximo.'
            raise ValidacionError(msg)

        hay_rango_monetario = (
            filtros.alquiler_min is not None
            or filtros.alquiler_max is not None
            or filtros.costo_real_min is not None
            or filtros.costo_real_max is not None
        )

        if hay_rango_monetario and filtros.moneda is None:
            msg = 'Indicá una moneda para filtrar por rangos monetarios.'
            raise ValidacionError(msg)

        if filtros.orden is not None and filtros.moneda is None:
            msg = 'Indicá una moneda para ordenar por un valor monetario.'
            raise ValidacionError(msg)

    def _consultar_publicaciones(
        self,
        filtros: FiltrosPublicaciones,
    ) -> list[Publicacion]:
        consulta = select(Publicacion).join(Publicacion.propiedad)

        if filtros.zona is not None:
            consulta = consulta.where(Propiedad.zona == filtros.zona)

        if filtros.ambientes is not None:
            consulta = consulta.where(
                Propiedad.ambientes == filtros.ambientes,
            )

        if filtros.permite_mascotas is not None:
            consulta = consulta.where(
                Propiedad.permite_mascotas.is_(filtros.permite_mascotas),
            )

        if filtros.tipo_garantia is not None:
            consulta = consulta.where(
                Publicacion.tipo_garantia_aceptada == filtros.tipo_garantia,
            )

        if filtros.moneda is not None:
            consulta = consulta.where(
                Publicacion.precio_alquiler_moneda == filtros.moneda.value,
            )

        if filtros.alquiler_min is not None:
            consulta = consulta.where(
                Publicacion.precio_alquiler_monto >= filtros.alquiler_min,
            )

        if filtros.alquiler_max is not None:
            consulta = consulta.where(
                Publicacion.precio_alquiler_monto <= filtros.alquiler_max,
            )

        if filtros.orden == 'alquiler':
            orden_alquiler = Publicacion.precio_alquiler_monto

            if filtros.descendente:
                orden_alquiler = orden_alquiler.desc()

            consulta = consulta.order_by(
                orden_alquiler,
                Publicacion.id,
            )
        else:
            consulta = consulta.order_by(Publicacion.id)

        return list(self.sesion.scalars(consulta))

    @staticmethod
    def _ordenar_publicaciones(
        publicaciones: list[Publicacion],
        filtros: FiltrosPublicaciones,
    ) -> list[Publicacion]:
        if filtros.orden == 'costo_real':
            return sorted(
                publicaciones,
                key=_monto_costo_real,
                reverse=filtros.descendente,
            )

        if filtros.orden == 'precio_m2':
            return _ordenar_por_precio_m2(
                publicaciones,
                filtros.descendente,
            )

        return publicaciones

    def obtener(self, publicacion_id: int) -> Publicacion:
        publicacion = self.sesion.get(Publicacion, publicacion_id)
        if publicacion is None:
            msg = 'No encontramos esa publicación.'
            raise RecursoNoEncontrado(msg)
        return publicacion

    def analizar_para_usuario(
        self,
        publicacion_id: int,
        usuario: Usuario,
    ) -> AnalisisEconomico:
        if usuario.ingreso_referencia is None:
            msg = 'Primero cargá tu ingreso de referencia.'
            raise ValidacionError(msg)

        publicacion = self.obtener(publicacion_id)
        return AnalisisEconomico(
            costo_real=publicacion.calcular_costo_real(),
            ingreso_referencia=usuario.ingreso_referencia,
        )


def _columnas_dinero(
    dinero: DineroEntrada | None,
) -> tuple[Decimal | None, str | None]:
    """Convierte un importe opcional a las dos columnas de la base."""
    if dinero is None:
        return None, None

    return dinero.monto, dinero.moneda.value


def _esta_dentro_del_rango_de_costo_real(
    publicacion: Publicacion,
    filtros: FiltrosPublicaciones,
) -> bool:
    costo_real = publicacion.calcular_costo_real().total

    if costo_real.moneda is not filtros.moneda:
        return False

    if (
        filtros.costo_real_min is not None
        and costo_real.monto < filtros.costo_real_min
    ):
        return False

    if (
        filtros.costo_real_max is not None
        and costo_real.monto > filtros.costo_real_max
    ):
        return False

    return True


def _monto_costo_real(
    publicacion: Publicacion,
) -> Decimal:
    return publicacion.calcular_costo_real().total.monto


def _ordenar_por_precio_m2(
    publicaciones: list[Publicacion],
    descendente: bool,
) -> list[Publicacion]:
    con_metros = [
        publicacion
        for publicacion in publicaciones
        if publicacion.propiedad.metros_cuadrados is not None
    ]
    sin_metros = [
        publicacion
        for publicacion in publicaciones
        if publicacion.propiedad.metros_cuadrados is None
    ]

    con_metros.sort(
        key=lambda publicacion: _precio_por_m2(publicacion) or Decimal(0),
        reverse=descendente,
    )

    return con_metros + sin_metros


def _precio_por_m2(
    publicacion: Publicacion,
) -> Decimal | None:
    metros_cuadrados = publicacion.propiedad.metros_cuadrados

    if metros_cuadrados is None:
        return None

    return publicacion.precio_alquiler.monto / metros_cuadrados
