from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class DineroEntrada(BaseModel):
    monto: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    moneda: Literal['ARS', 'USD'] = 'ARS'


class PropiedadCrear(BaseModel):
    direccion: str = Field(min_length=5, max_length=200)
    zona: str = Field(min_length=2, max_length=100)
    tipo: Literal['departamento', 'casa', 'ph']
    ambientes: int = Field(ge=1, le=10)
    metros_cuadrados: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=8,
        decimal_places=2,
    )
    permite_mascotas: bool | None = None


class PublicacionCrear(BaseModel):
    propiedad: PropiedadCrear
    precio_alquiler: DineroEntrada
    expensas_mensuales: DineroEntrada | None = None
    abl_mensual: DineroEntrada | None = None
    costo_caucion_total: DineroEntrada | None = None
    duracion_contrato_meses: int | None = Field(default=None, ge=1, le=36)
    tipo_garantia_aceptada: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )


class PublicacionRespuesta(PublicacionCrear):
    id: int
