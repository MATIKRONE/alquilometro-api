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


@dataclass(frozen=True, slots=True)
class CostoEntrada:
    """Gastos para firmar: primer mes, depósito, comisión, garantía y otros.

    Suma solo lo informado e identifica lo que falta. `otros_gastos` es
    opcional por naturaleza (sellados, certificaciones, etc.), por eso no
    figura como faltante.
    """

    primer_mes: Dinero
    deposito: Dinero | None = None
    comision: Dinero | None = None
    seguro_caucion: Dinero | None = None
    otros_gastos: Dinero | None = None

    @property
    def componentes_informados(self) -> dict[str, Dinero]:
        candidatos = {
            'primer_mes': self.primer_mes,
            'deposito': self.deposito,
            'comision': self.comision,
            'seguro_caucion': self.seguro_caucion,
            'otros_gastos': self.otros_gastos,
        }
        return {
            nombre: monto
            for nombre, monto in candidatos.items()
            if monto is not None
        }

    @property
    def faltantes(self) -> list[str]:
        return [
            nombre
            for nombre in ('deposito', 'comision', 'seguro_caucion')
            if getattr(self, nombre) is None
        ]

    @property
    def total(self) -> Dinero:
        return Dinero.total(
            self.componentes_informados.values(),
            self.primer_mes.moneda,
        )
