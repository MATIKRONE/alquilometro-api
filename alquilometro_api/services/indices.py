from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from alquilometro_api.domain.ajuste import (
    normalizar_serie,
    primer_dia_del_mes,
)
from alquilometro_api.domain.errores import ValidacionError
from alquilometro_api.models.indice import ValorIndice


class RepositorioIndicesDB:
    """Valores de índices guardados en la base.

    Cumple el Protocol `RepositorioIndices` del dominio, así que el
    mecanismo de ajuste no sabe si los valores vienen de acá o de memoria.
    """

    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def valor(self, serie: str, momento: date) -> Decimal | None:
        fila = self._buscar(normalizar_serie(serie), momento)
        return None if fila is None else fila.valor

    def cargar(self, serie: str, momento: date, valor: Decimal) -> ValorIndice:
        """Carga o corrige el valor de un mes."""
        if valor <= 0:
            msg = 'El valor de un índice debe ser mayor a cero.'
            raise ValidacionError(msg)
        serie = normalizar_serie(serie)
        fila = self._buscar(serie, momento)
        if fila is None:
            fila = ValorIndice(
                serie=serie,
                fecha=primer_dia_del_mes(momento),
                valor=valor,
            )
            self.sesion.add(fila)
        else:
            fila.valor = valor
        self.sesion.commit()
        return fila

    def listar(self, serie: str) -> list[ValorIndice]:
        consulta = (
            select(ValorIndice)
            .where(ValorIndice.serie == normalizar_serie(serie))
            .order_by(ValorIndice.fecha)
        )
        return list(self.sesion.scalars(consulta))

    def _buscar(self, serie: str, momento: date) -> ValorIndice | None:
        consulta = select(ValorIndice).where(
            ValorIndice.serie == serie,
            ValorIndice.fecha == primer_dia_del_mes(momento),
        )
        return self.sesion.scalars(consulta).first()
