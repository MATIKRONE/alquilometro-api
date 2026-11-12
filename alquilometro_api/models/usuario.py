from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alquilometro_api.core.database import Base

if TYPE_CHECKING:
    from alquilometro_api.models.publicacion import Publicacion


class Usuario(Base):
    """Persona que publica avisos o usa la plataforma."""

    __tablename__ = 'usuarios'

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    ingreso_referencia: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    publicaciones: Mapped[list['Publicacion']] = relationship(
        back_populates='publicador',
    )
