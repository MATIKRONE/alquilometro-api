from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alquilometro_api.core.database import Base

if TYPE_CHECKING:
    from alquilometro_api.models.publicacion import Publicacion


class Propiedad(Base):
    """Inmueble sobre el que se puede publicar un aviso de alquiler."""

    __tablename__ = 'propiedades'

    id: Mapped[int] = mapped_column(primary_key=True)
    direccion: Mapped[str] = mapped_column(String(200))
    zona: Mapped[str] = mapped_column(String(100))
    tipo: Mapped[str] = mapped_column(String(30))
    ambientes: Mapped[int] = mapped_column(Integer)
    metros_cuadrados: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    permite_mascotas: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    publicaciones: Mapped[list['Publicacion']] = relationship(
        back_populates='propiedad',
    )
