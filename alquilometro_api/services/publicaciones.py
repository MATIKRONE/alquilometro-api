from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from alquilometro_api.domain.analisis_economico import AnalisisEconomico
from alquilometro_api.domain.errores import (
    PermisoInsuficiente,
    RecursoNoEncontrado,
    ValidacionError,
)
from alquilometro_api.domain.rol import Rol
from alquilometro_api.models.propiedad import Propiedad
from alquilometro_api.models.publicacion import Publicacion
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.schemas.publicacion import (
    DineroEntrada,
    PublicacionCrear,
)


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

    def listar(self) -> list[Publicacion]:
        consulta = select(Publicacion).order_by(Publicacion.id)
        return list(self.sesion.scalars(consulta))

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
