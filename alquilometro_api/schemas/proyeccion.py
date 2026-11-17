from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from alquilometro_api.domain.ajuste import TipoAjuste
from alquilometro_api.domain.proyeccion import OrigenEscenario
from alquilometro_api.schemas.contrato import DineroRespuesta


class EscenarioRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tasa_mensual_porcentual: Decimal
    origen: OrigenEscenario


class MesProyectadoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mes: int
    ajustes_aplicados: int
    alquiler: DineroRespuesta
    costo_mensual: DineroRespuesta
    porcentaje_ingreso: Decimal | None
    formula: str


class ProyeccionRespuesta(BaseModel):
    """Proyección a 12 y 24 meses, con la serie y el escenario usados."""

    model_config = ConfigDict(from_attributes=True)

    publicacion_id: int
    tipo_ajuste: TipoAjuste
    meses_periodicidad: int
    serie: str | None
    fecha_referencia: date | None
    escenario: EscenarioRespuesta | None
    meses: list[MesProyectadoRespuesta]
    faltantes: list[str]
