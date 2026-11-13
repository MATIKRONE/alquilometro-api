from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alquilometro_api.core.database import Base
from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import ValidacionError
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.domain.rol import Rol

if TYPE_CHECKING:
    from alquilometro_api.models.publicacion import Publicacion


class Usuario(Base):
    """Persona que publica avisos o usa la plataforma."""

    __tablename__ = 'usuarios'
    __table_args__ = (
        CheckConstraint(
            '(ingreso_referencia_monto IS NULL)'
            ' AND ingreso_referencia_moneda IS NULL'
            ' OR (ingreso_referencia_moneda IS NOT NULL'
            ' AND ingreso_referencia_moneda IS NOT NULL)',
            name='ck_usuarios_ingreso_completo',
        ),
    )  # sirve para impedir monto sin especificar
    # ARS O USD o viseversa y arruinar calculo

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(String(255))

    rol: Mapped[Rol] = mapped_column(
        Enum(Rol, native_enum=False, lenght=20),
        default=Rol.BUSCADOR,
    )

    ingreso_referencia_monto: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    ingreso_referencia_moneda: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    publicaciones: Mapped[list['Publicacion']] = relationship(
        back_populates='publicador',
    )

    @property  # getter: returnea Dinero
    def ingreso_referencia(self) -> Dinero | None:
        if (
            self.ingreso_referencia_monto is None
            or self.ingreso_referencia_moneda is None
        ):
            return None
        return Dinero(
            self.ingreso_referencia_monto,
            Moneda(self.ingreso_referencia_moneda),
        )

    @ingreso_referencia.setter
    def ingreso_referencia(self, valor: Dinero | None) -> None:
        if valor is None:
            self.ingreso_referencia_monto = None
            self.ingreso_referencia_moneda = None
            return
        if valor.monto <= 0:
            msg = 'El ingreso de referencia debe ser mayor a cero.'
            raise ValidacionError(msg)
        self.ingreso_referencia_monto = valor.redondear().monto
        self.ingreso_referencia_moneda = valor.moneda.value
