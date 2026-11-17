from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alquilometro_api.core.database import Base
from alquilometro_api.domain.desglose_costo import DesgloseCosto
from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.moneda import Moneda

if TYPE_CHECKING:
    from alquilometro_api.models.propiedad import Propiedad
    from alquilometro_api.models.usuario import Usuario


class Publicacion(Base):
    """Aviso de alquiler publicado para una propiedad."""

    __tablename__ = 'publicaciones'

    id: Mapped[int] = mapped_column(primary_key=True)

    propiedad_id: Mapped[int] = mapped_column(
        ForeignKey('propiedades.id'),
        index=True,
    )
    publicador_id: Mapped[int] = mapped_column(
        ForeignKey('usuarios.id'),
        index=True,
    )

    precio_alquiler_monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    precio_alquiler_moneda: Mapped[str] = mapped_column(String(3))

    expensas_mensuales_monto: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    expensas_mensuales_moneda: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    abl_monto: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    abl_moneda: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    seguro_caucion_monto: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    seguro_caucion_moneda: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    deposito_monto: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    deposito_moneda: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    duracion_contrato_meses: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    tipo_garantia_aceptada: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    tipo_ajuste: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    tasa_ajuste: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    serie_codigo: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    patrocinada: Mapped[bool] = mapped_column(Boolean, default=False)
    fuente: Mapped[str | None] = mapped_column(String(100), nullable=True)

    propiedad: Mapped[Propiedad] = relationship(
        back_populates='publicaciones',
    )
    publicador: Mapped[Usuario] = relationship(
        back_populates='publicaciones',
    )

    @property
    def precio_alquiler(self) -> Dinero:
        return Dinero(
            self.precio_alquiler_monto,
            Moneda(self.precio_alquiler_moneda),
        )

    @property
    def expensas_mensuales(self) -> Dinero | None:
        return self._dinero_opcional(
            self.expensas_mensuales_monto,
            self.expensas_mensuales_moneda,
        )

    @property
    def abl_mensual(self) -> Dinero | None:
        return self._dinero_opcional(
            self.abl_monto,
            self.abl_moneda,
        )

    @property
    def seguro_caucion(self) -> Dinero | None:
        return self._dinero_opcional(
            self.seguro_caucion_monto,
            self.seguro_caucion_moneda,
        )

    @property
    def deposito(self) -> Dinero | None:
        return self._dinero_opcional(
            self.deposito_monto,
            self.deposito_moneda,
        )

    def calcular_costo_real(self) -> DesgloseCosto:
        """Arma el desglose mensual con los datos de la publicación."""
        return DesgloseCosto(
            alquiler=self.precio_alquiler,
            expensas=self.expensas_mensuales,
            abl=self.abl_mensual,
            seguro_caucion=self.seguro_caucion,
            duracion_contrato_meses=self.duracion_contrato_meses,
        )

    @staticmethod
    def _dinero_opcional(
        monto: Decimal | None,
        moneda: str | None,
    ) -> Dinero | None:
        if monto is None or moneda is None:
            return None

        return Dinero(monto, Moneda(moneda))
