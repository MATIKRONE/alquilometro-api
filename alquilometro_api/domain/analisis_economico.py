from dataclasses import dataclass
from decimal import Decimal

from alquilometro_api.domain.desglose_costo import DesgloseCosto
from alquilometro_api.domain.dinero import Dinero


@dataclass(frozen=True, slots=True)
class AnalisisEconomico:
    """Compara el costo real de una publicación con un ingreso mensual."""

    costo_real: DesgloseCosto
    ingreso_referencia: Dinero

    @property
    def porcentaje_ingreso(self) -> Decimal:
        return self.costo_real.total.porcentaje_de(
            self.ingreso_referencia,
        )
