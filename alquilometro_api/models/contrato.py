from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alquilometro_api.core.database import Base
from alquilometro_api.domain.ajuste import (
    FabricaMecanismoAjuste,
    MecanismoAjuste,
    RepositorioIndices,
    sumar_meses,
)
from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.domain.verificacion import ResultadoVerificacion

if TYPE_CHECKING:
    from alquilometro_api.models.usuario import Usuario


class ContratoAlquiler(Base):
    """Contrato firmado por un inquilino: la base del seguimiento (RQ5)."""

    __tablename__ = 'contratos'

    id: Mapped[int] = mapped_column(primary_key=True)
    inquilino_id: Mapped[int] = mapped_column(
        ForeignKey('usuarios.id'),
        index=True,
    )
    # Opcional: el contrato puede no venir de una publicación cargada.
    publicacion_id: Mapped[int | None] = mapped_column(
        ForeignKey('publicaciones.id'),
        nullable=True,
    )

    fecha_inicio: Mapped[date] = mapped_column(Date)
    duracion_meses: Mapped[int] = mapped_column(Integer)

    monto_base_monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    monto_base_moneda: Mapped[str] = mapped_column(String(3))

    tipo_ajuste: Mapped[str] = mapped_column(String(10))
    tasa_ajuste: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    serie_codigo: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    meses_periodicidad: Mapped[int] = mapped_column(Integer)

    inquilino: Mapped[Usuario] = relationship()
    verificaciones: Mapped[list[VerificacionAjuste]] = relationship(
        back_populates='contrato',
        cascade='all, delete-orphan',
        order_by='VerificacionAjuste.id',
    )

    @property
    def monto_base(self) -> Dinero:
        return Dinero(self.monto_base_monto, Moneda(self.monto_base_moneda))

    @property
    def fecha_fin(self) -> date:
        return sumar_meses(self.fecha_inicio, self.duracion_meses)

    def mecanismo(self, repositorio: RepositorioIndices) -> MecanismoAjuste:
        """Traduce lo guardado a la estrategia de ajuste (Simple Factory)."""
        return FabricaMecanismoAjuste.crear(
            self.tipo_ajuste,
            tasa_porcentual=self.tasa_ajuste,
            serie=self.serie_codigo,
            repositorio=repositorio,
        )


class VerificacionAjuste(Base):
    """Una verificación hecha por el inquilino, guardada en su historial."""

    __tablename__ = 'verificaciones_ajuste'

    id: Mapped[int] = mapped_column(primary_key=True)
    contrato_id: Mapped[int] = mapped_column(
        ForeignKey('contratos.id'),
        index=True,
    )
    fecha_ajuste: Mapped[date] = mapped_column(Date)
    moneda: Mapped[str] = mapped_column(String(3))
    monto_informado: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    monto_esperado: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    resultado: Mapped[str] = mapped_column(String(20))
    formula: Mapped[str] = mapped_column(Text)
    explicacion: Mapped[str] = mapped_column(Text)
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    contrato: Mapped[ContratoAlquiler] = relationship(
        back_populates='verificaciones',
    )

    @property
    def resultado_verificacion(self) -> ResultadoVerificacion:
        return ResultadoVerificacion(self.resultado)

    @property
    def informado(self) -> Dinero:
        return Dinero(self.monto_informado, Moneda(self.moneda))

    @property
    def esperado(self) -> Dinero:
        return Dinero(self.monto_esperado, Moneda(self.moneda))

    @property
    def diferencia(self) -> Dinero:
        return self.informado.restar(self.esperado)

    @property
    def diferencia_porcentual(self) -> Decimal:
        return self.diferencia.porcentaje_de(self.esperado)
