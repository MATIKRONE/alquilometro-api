from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alquilometro_api.core.database import Base

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
