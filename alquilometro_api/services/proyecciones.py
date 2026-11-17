from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from alquilometro_api.domain.ajuste import (
    FabricaMecanismoAjuste,
    TipoAjuste,
    normalizar_serie,
)
from alquilometro_api.domain.errores import (
    IndiceNoDisponible,
    ValidacionError,
)
from alquilometro_api.domain.proyeccion import (
    Escenario,
    MesProyectado,
    escenario_desde_historia,
    escenario_indicado,
    indices_proyectados,
    proyectar,
)
from alquilometro_api.models.publicacion import Publicacion
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.services.indices import RepositorioIndicesDB


@dataclass(frozen=True, slots=True)
class Proyeccion:
    """Proyección de una publicación, con los supuestos que usó."""

    publicacion_id: int
    tipo_ajuste: TipoAjuste
    meses_periodicidad: int
    serie: str | None
    fecha_referencia: date | None
    escenario: Escenario | None
    meses: list[MesProyectado]
    faltantes: list[str]


class ServicioProyecciones:
    """Proyección a 12 y 24 meses del costo de una publicación (RQ3)."""

    def __init__(self, sesion: Session) -> None:
        self.indices = RepositorioIndicesDB(sesion)

    def proyectar(
        self,
        publicacion: Publicacion,
        usuario: Usuario,
        *,
        meses_periodicidad: int,
        tasa_mensual: Decimal | None = None,
    ) -> Proyeccion:
        if publicacion.tipo_ajuste is None:
            msg = (
                'La publicación no informa cómo se ajusta el alquiler: '
                'no se puede proyectar sin inventar datos.'
            )
            raise ValidacionError(msg)

        desglose = publicacion.calcular_costo_real()
        otros_costos = desglose.total.restar(desglose.alquiler)
        tipo = TipoAjuste(publicacion.tipo_ajuste)

        if tipo is TipoAjuste.FIJO:
            mecanismo = FabricaMecanismoAjuste.crear(
                tipo, tasa_porcentual=publicacion.tasa_ajuste
            )
            fecha_inicio = date.today().replace(day=1)
            serie = referencia = escenario = None
        else:
            serie = normalizar_serie(publicacion.serie_codigo or '')
            valores = self.indices.listar(serie)
            if not valores:
                msg = f'No hay valores cargados de {serie} para proyectar.'
                raise IndiceNoDisponible(msg)
            ultimo = valores[-1]
            escenario = (
                escenario_desde_historia(v.valor for v in valores)
                if tasa_mensual is None
                else escenario_indicado(tasa_mensual)
            )
            referencia = fecha_inicio = ultimo.fecha
            mecanismo = FabricaMecanismoAjuste.crear(
                tipo,
                serie=serie,
                repositorio=indices_proyectados(
                    serie, ultimo.fecha, ultimo.valor, escenario
                ),
            )

        return Proyeccion(
            publicacion_id=publicacion.id,
            tipo_ajuste=tipo,
            meses_periodicidad=meses_periodicidad,
            serie=serie,
            fecha_referencia=referencia,
            escenario=escenario,
            meses=proyectar(
                mecanismo,
                desglose.alquiler,
                otros_costos,
                fecha_inicio,
                meses_periodicidad,
                usuario.ingreso_referencia,
            ),
            faltantes=desglose.faltantes,
        )
