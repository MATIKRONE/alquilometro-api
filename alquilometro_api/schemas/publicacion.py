from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.moneda import Moneda


class DineroEntrada(BaseModel):
    monto: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    moneda: Moneda = Moneda.ARS

    def a_dominio(self) -> Dinero:
        return Dinero(self.monto, self.moneda)


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
    model_config = ConfigDict(extra='forbid')

    propiedad: PropiedadCrear
    precio_alquiler: DineroEntrada
    expensas_mensuales: DineroEntrada | None = None
    abl_mensual: DineroEntrada | None = None
    seguro_caucion: DineroEntrada | None = None
    duracion_contrato_meses: int | None = Field(default=None, ge=1, le=36)
    tipo_garantia_aceptada: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )
    deposito: DineroEntrada | None = None
    # TODO: cambiar cuando se cree enum INDICE!!!
    tipo_ajuste: Literal['FIJO', 'INDICE'] | None = None
    tasa_ajuste: Decimal | None = Field(
        default=None,
        ge=0,
        description='Porcentaje de ajuste expresado en puntos '
        'porcentuales (ej: 15.5 para 15.5%)',
    )
    serie_codigo: str | None = None
    patrocinada: bool = False
    fuente: str | None = None

    # Validaciones
    @field_validator('precio_alquiler')
    @classmethod
    def validar_alquiler_gt_cero(cls, valor: DineroEntrada) -> DineroEntrada:
        if valor.monto == 0:
            raise ValueError('El precio del alquiler no puede ser cero.')
        return valor

    @model_validator(mode='after')
    def validar_coherencia_ajuste(self) -> 'PublicacionCrear':
        if self.tipo_ajuste == 'FIJO' and self.tasa_ajuste is None:
            raise ValueError(
                'Si el tipo de ajuste es FIJO, especificar tasa_ajuste'
            )
        if self.tipo_ajuste == 'INDICE' and self.serie_codigo is None:
            raise ValueError(
                'Si el tipo de ajuste es INDICE, especificar serie_codigo'
            )
        return self


class PublicacionRespuesta(PublicacionCrear):
    id: int
