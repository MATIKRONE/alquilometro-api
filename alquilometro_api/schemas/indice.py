from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ValorIndiceCrear(BaseModel):
    """Valor mensual de una serie: cualquier fecha cae al 1 de su mes."""

    model_config = ConfigDict(extra='forbid')

    fecha: date
    valor: Decimal = Field(gt=0, max_digits=18, decimal_places=6)


class ValorIndiceRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    serie: str
    fecha: date
    valor: Decimal
