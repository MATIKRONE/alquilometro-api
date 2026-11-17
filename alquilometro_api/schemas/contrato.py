from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from alquilometro_api.domain.ajuste import TipoAjuste
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.domain.verificacion import ResultadoVerificacion
from alquilometro_api.schemas.publicacion import DineroEntrada
from alquilometro_api.services.contratos import DatosContrato, EstadoAjuste


class DineroRespuesta(BaseModel):
    """Un importe en una respuesta: puede ser negativo (una diferencia)."""

    model_config = ConfigDict(from_attributes=True)

    monto: Decimal
    moneda: Moneda


class ContratoCrear(BaseModel):
    """Datos que recibe POST /contratos."""

    model_config = ConfigDict(extra='forbid')

    fecha_inicio: date
    duracion_meses: int = Field(ge=1, le=120)
    monto_base: DineroEntrada
    tipo_ajuste: TipoAjuste
    meses_periodicidad: int = Field(ge=1, le=60)
    tasa_ajuste: Decimal | None = Field(
        default=None,
        ge=0,
        description='Puntos porcentuales por período (15.5 = 15,5%).',
    )
    serie_codigo: str | None = Field(
        default=None,
        min_length=2,
        max_length=20,
        description='Serie del índice, por ejemplo ICL.',
    )
    publicacion_id: int | None = None

    def a_datos(self) -> DatosContrato:
        return DatosContrato(
            fecha_inicio=self.fecha_inicio,
            duracion_meses=self.duracion_meses,
            monto_base=self.monto_base.a_dominio(),
            tipo_ajuste=self.tipo_ajuste.value,
            meses_periodicidad=self.meses_periodicidad,
            tasa_ajuste=self.tasa_ajuste,
            serie_codigo=self.serie_codigo,
            publicacion_id=self.publicacion_id,
        )


class ContratoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_inicio: date
    fecha_fin: date
    duracion_meses: int
    monto_base: DineroRespuesta
    tipo_ajuste: TipoAjuste
    meses_periodicidad: int
    tasa_ajuste: Decimal | None
    serie_codigo: str | None
    publicacion_id: int | None


class AjusteRespuesta(BaseModel):
    """Un ajuste calculado, con la fórmula que lo explica."""

    model_config = ConfigDict(from_attributes=True)

    monto_base: DineroRespuesta
    monto_ajustado: DineroRespuesta
    coeficiente: Decimal
    periodos: int
    formula: str


class AjusteProgramadoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    numero: int
    fecha: date
    estado: EstadoAjuste
    resultado: AjusteRespuesta | None


class VerificacionCrear(BaseModel):
    """Datos que recibe POST /contratos/{id}/verificaciones."""

    model_config = ConfigDict(extra='forbid')

    fecha_ajuste: date
    monto_informado: DineroEntrada


class VerificacionRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_ajuste: date
    resultado: ResultadoVerificacion
    informado: DineroRespuesta
    esperado: DineroRespuesta
    diferencia: DineroRespuesta
    diferencia_porcentual: Decimal
    formula: str
    explicacion: str
    creada_en: datetime | None
