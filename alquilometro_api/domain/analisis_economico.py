from dataclasses import dataclass
from decimal import Decimal

from alquilometro_api.domain.desglose_costo import CostoEntrada, DesgloseCosto
from alquilometro_api.domain.dinero import Dinero


@dataclass(frozen=True, slots=True)
class AnalisisEconomico:
    """Costo real y de entrada de una publicación frente a un ingreso."""

    costo_real: DesgloseCosto
    ingreso_referencia: Dinero
    costo_entrada: CostoEntrada

    @property
    def porcentaje_ingreso(self) -> Decimal:
        return self.costo_real.total.porcentaje_de(
            self.ingreso_referencia,
        )
