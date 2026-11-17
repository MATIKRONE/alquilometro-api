from dataclasses import dataclass
from decimal import Decimal

from alquilometro_api.domain.dinero import Dinero


@dataclass(frozen=True, slots=True)
class DesgloseCosto:
    """Costo mensual conocido de una publicación y sus datos faltantes."""

    alquiler: Dinero
    expensas: Dinero | None = None
    abl: Dinero | None = None
    seguro_caucion: Dinero | None = None
    duracion_contrato_meses: int | None = None

    @property
    def seguro_caucion_prorrateado(self) -> Dinero | None:
        """Parte mensual del seguro de caución, si se puede calcular."""
        if self.seguro_caucion is None or self.duracion_contrato_meses is None:
            return None

        factor_mensual = Decimal(1) / self.duracion_contrato_meses
        return self.seguro_caucion.multiplicar(factor_mensual).redondear()

    @property
    def componentes_informados(self) -> dict[str, Dinero]:
        componentes = {'alquiler': self.alquiler}

        if self.expensas is not None:
            componentes['expensas'] = self.expensas
        if self.abl is not None:
            componentes['abl'] = self.abl

        seguro_prorrateado = self.seguro_caucion_prorrateado
        if seguro_prorrateado is not None:
            componentes['seguro_caucion_prorrateado'] = seguro_prorrateado

        return componentes

    @property
    def faltantes(self) -> list[str]:
        faltantes = []

        if self.expensas is None:
            faltantes.append('expensas')
        if self.abl is None:
            faltantes.append('abl')
        if self.seguro_caucion is None:
            faltantes.append('seguro_caucion')
        elif self.duracion_contrato_meses is None:
            faltantes.append('duracion_contrato_meses')

        return faltantes

    @property
    def total(self) -> Dinero:
        return Dinero.total(
            self.componentes_informados.values(),
            self.alquiler.moneda,
        )
