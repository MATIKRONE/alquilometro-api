from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from alquilometro_api.core.database import Base


class ValorIndice(Base):
    """Valor mensual de una serie de índices (ICL, IPC, UVA...).

    Las series se guardan en la base a propósito: si dependiéramos de una
    API externa en vivo, el sistema dejaría de funcionar cuando se caiga.
    """

    __tablename__ = 'valores_indice'
    __table_args__ = (
        UniqueConstraint('serie', 'fecha', name='uq_valores_indice_mes'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    serie: Mapped[str] = mapped_column(String(20), index=True)
    # Siempre el primer día del mes: los índices son mensuales.
    fecha: Mapped[date] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 6))
