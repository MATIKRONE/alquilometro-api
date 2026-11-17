from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from alquilometro_api.domain.ajuste import (
    RepositorioIndices,
    ResultadoAjuste,
    meses_entre,
    sumar_meses,
)
from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import (
    ConflictoDominio,
    IndiceNoDisponible,
    RecursoNoEncontrado,
    ValidacionError,
)
from alquilometro_api.domain.verificacion import (
    Verificacion,
    verificar_ajuste,
)
from alquilometro_api.models.contrato import (
    ContratoAlquiler,
    VerificacionAjuste,
)
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.services.indices import RepositorioIndicesDB


class EstadoAjuste(StrEnum):
    CALCULADO = 'CALCULADO'
    PENDIENTE = 'PENDIENTE'


@dataclass(frozen=True, slots=True)
class DatosContrato:
    """Lo necesario para registrar un contrato firmado."""

    fecha_inicio: date
    duracion_meses: int
    monto_base: Dinero
    tipo_ajuste: str
    meses_periodicidad: int
    tasa_ajuste: Decimal | None = None
    serie_codigo: str | None = None
    publicacion_id: int | None = None


@dataclass(frozen=True, slots=True)
class AjusteProgramado:
    """Una fecha del calendario de ajustes y su monto, si ya se conoce."""

    numero: int
    fecha: date
    estado: EstadoAjuste
    resultado: ResultadoAjuste | None = None


class ServicioContratos:
    """Registro de contratos, calendario de ajustes y verificaciones."""

    def __init__(
        self,
        sesion: Session,
        repositorio: RepositorioIndices | None = None,
    ) -> None:
        self.sesion = sesion
        self.repositorio = repositorio or RepositorioIndicesDB(sesion)

    def registrar(
        self, inquilino: Usuario, datos: DatosContrato
    ) -> ContratoAlquiler:
        _validar(datos)
        contrato = ContratoAlquiler(
            inquilino_id=inquilino.id,
            publicacion_id=datos.publicacion_id,
            fecha_inicio=datos.fecha_inicio,
            duracion_meses=datos.duracion_meses,
            monto_base_monto=datos.monto_base.redondear().monto,
            monto_base_moneda=datos.monto_base.moneda.value,
            tipo_ajuste=datos.tipo_ajuste.strip().upper(),
            tasa_ajuste=datos.tasa_ajuste,
            serie_codigo=datos.serie_codigo,
            meses_periodicidad=datos.meses_periodicidad,
        )
        # La fábrica valida el mecanismo antes de guardar nada.
        contrato.mecanismo(self.repositorio)
        self.sesion.add(contrato)
        self.sesion.commit()
        return contrato

    def listar(self, inquilino: Usuario) -> list[ContratoAlquiler]:
        consulta = select(ContratoAlquiler).where(
            ContratoAlquiler.inquilino_id == inquilino.id
        )
        return list(self.sesion.scalars(consulta))

    def obtener(
        self, contrato_id: int, inquilino: Usuario
    ) -> ContratoAlquiler:
        contrato = self.sesion.get(ContratoAlquiler, contrato_id)
        # 404 y no 403: a nadie se le confirma que un contrato ajeno existe.
        if contrato is None or contrato.inquilino_id != inquilino.id:
            msg = 'No encontramos ese contrato.'
            raise RecursoNoEncontrado(msg)
        return contrato

    def calendario(self, contrato: ContratoAlquiler) -> list[AjusteProgramado]:
        """Todas las fechas de ajuste del contrato, con su monto si se puede.

        Si el índice de un mes todavía no está publicado, el ajuste queda
        pendiente en lugar de inventar un valor.
        """
        mecanismo = contrato.mecanismo(self.repositorio)
        cantidad = (contrato.duracion_meses - 1) // contrato.meses_periodicidad
        programados = []
        for numero in range(1, cantidad + 1):
            fecha = sumar_meses(
                contrato.fecha_inicio, numero * contrato.meses_periodicidad
            )
            try:
                resultado = mecanismo.ajustar(
                    contrato.monto_base,
                    contrato.fecha_inicio,
                    fecha,
                    contrato.meses_periodicidad,
                )
            except IndiceNoDisponible:
                programados.append(
                    AjusteProgramado(numero, fecha, EstadoAjuste.PENDIENTE)
                )
            else:
                programados.append(
                    AjusteProgramado(
                        numero, fecha, EstadoAjuste.CALCULADO, resultado
                    )
                )
        return programados

    def calcular_ajuste(
        self, contrato: ContratoAlquiler, fecha: date
    ) -> ResultadoAjuste:
        fecha_ajuste = self._fecha_del_ajuste_vigente(contrato, fecha)
        return contrato.mecanismo(self.repositorio).ajustar(
            contrato.monto_base,
            contrato.fecha_inicio,
            fecha_ajuste,
            contrato.meses_periodicidad,
        )

    def verificar(
        self,
        contrato: ContratoAlquiler,
        fecha: date,
        monto_informado: Dinero,
    ) -> VerificacionAjuste:
        """Compara lo informado con lo que corresponde y lo guarda."""
        fecha_ajuste = self._fecha_del_ajuste_vigente(contrato, fecha)
        verificacion: Verificacion = verificar_ajuste(
            contrato.mecanismo(self.repositorio),
            contrato.monto_base,
            contrato.fecha_inicio,
            fecha_ajuste,
            contrato.meses_periodicidad,
            monto_informado,
        )
        registro = VerificacionAjuste(
            contrato_id=contrato.id,
            fecha_ajuste=fecha_ajuste,
            moneda=verificacion.monto_esperado.moneda.value,
            monto_informado=verificacion.monto_informado.monto,
            monto_esperado=verificacion.monto_esperado.monto,
            resultado=verificacion.resultado.value,
            formula=verificacion.detalle.formula,
            explicacion=verificacion.explicacion,
        )
        self.sesion.add(registro)
        self.sesion.commit()
        return registro

    @staticmethod
    def _fecha_del_ajuste_vigente(
        contrato: ContratoAlquiler, fecha: date
    ) -> date:
        """Lleva cualquier fecha a la del último ajuste que ya corresponde.

        El índice se toma del mes en que vence el período, no del día en
        que el inquilino consulta.
        """
        if fecha >= contrato.fecha_fin:
            msg = 'El contrato ya terminó: no hay ajustes después del final.'
            raise ConflictoDominio(msg)
        if fecha < contrato.fecha_inicio:
            msg = 'La fecha es anterior al inicio del contrato.'
            raise ValidacionError(msg)
        periodos = (
            meses_entre(contrato.fecha_inicio, fecha)
            // contrato.meses_periodicidad
        )
        return sumar_meses(
            contrato.fecha_inicio, periodos * contrato.meses_periodicidad
        )


def _validar(datos: DatosContrato) -> None:
    if datos.duracion_meses <= 0:
        msg = 'La duración del contrato debe ser de al menos un mes.'
        raise ValidacionError(msg)
    if not 0 < datos.meses_periodicidad < datos.duracion_meses:
        msg = 'La periodicidad tiene que ser menor que la duración.'
        raise ValidacionError(msg)
    if datos.monto_base.monto <= 0:
        msg = 'El monto base del contrato debe ser mayor a cero.'
        raise ValidacionError(msg)
