from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from alquilometro_api.domain.errores import ValidacionError
from alquilometro_api.services.indices import RepositorioIndicesDB


def test_cualquier_dia_del_mes_lee_el_valor_mensual(sesion: Session) -> None:
    indices = RepositorioIndicesDB(sesion)
    indices.cargar('icl', date(2026, 4, 1), Decimal(130))

    assert indices.valor('ICL', date(2026, 4, 20)) == Decimal(130)
    assert indices.valor('ICL', date(2026, 5, 1)) is None


def test_cargar_de_nuevo_corrige_el_valor(sesion: Session) -> None:
    indices = RepositorioIndicesDB(sesion)
    indices.cargar('ICL', date(2026, 4, 1), Decimal(130))
    indices.cargar('ICL', date(2026, 4, 1), Decimal(131))

    assert indices.valor('ICL', date(2026, 4, 1)) == Decimal(131)


def test_rechaza_valores_no_positivos(sesion: Session) -> None:
    with pytest.raises(ValidacionError):
        RepositorioIndicesDB(sesion).cargar(
            'ICL', date(2026, 4, 1), Decimal(0)
        )
