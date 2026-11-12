from datetime import date
from decimal import Decimal

import pytest

from alquilometro_api.domain.ajuste import (
    AjusteFijo,
    AjusteIndice,
    FabricaMecanismoAjuste,
    IndicesEnMemoria,
    MecanismoAjuste,
    TipoAjuste,
)
from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.errores import (
    ConflictoDominio,
    IndiceNoDisponible,
    ValidacionError,
)
from alquilometro_api.domain.moneda import Moneda

INICIO = date(2026, 1, 1)
PRIMER_AJUSTE = date(2026, 4, 1)
SEGUNDO_AJUSTE = date(2026, 7, 1)
TRIMESTRAL = 3
PERIODOS_AL_SEMESTRE = 2


@pytest.fixture
def monto_base() -> Dinero:
    return Dinero(Decimal('500000'), Moneda.ARS)


@pytest.fixture
def indices() -> IndicesEnMemoria:
    """Serie ICL de ejemplo: 100 en enero, 130 en abril, 169 en julio."""
    repositorio = IndicesEnMemoria()
    repositorio.cargar('ICL', INICIO, '100')
    repositorio.cargar('ICL', PRIMER_AJUSTE, '130')
    repositorio.cargar('ICL', SEGUNDO_AJUSTE, '169')
    return repositorio


def test_ajuste_fijo_capitaliza_cada_periodo(monto_base: Dinero) -> None:
    mecanismo = AjusteFijo('10')

    resultado = mecanismo.ajustar(
        monto_base, INICIO, SEGUNDO_AJUSTE, TRIMESTRAL
    )

    assert resultado.periodos == PERIODOS_AL_SEMESTRE
    assert resultado.monto_ajustado == Dinero(Decimal('605000.00'), Moneda.ARS)


def test_ajuste_por_indice_parte_del_monto_base(
    monto_base: Dinero,
    indices: IndicesEnMemoria,
) -> None:
    mecanismo = AjusteIndice('ICL', indices)

    resultado = mecanismo.ajustar(
        monto_base, INICIO, PRIMER_AJUSTE, TRIMESTRAL
    )

    assert resultado.coeficiente == Decimal('1.3')
    assert resultado.monto_ajustado == Dinero(Decimal('650000.00'), Moneda.ARS)


def test_el_segundo_ajuste_no_encadena_sobre_el_anterior(
    monto_base: Dinero,
    indices: IndicesEnMemoria,
) -> None:
    """El error de encadenamiento, que es el diferencial del producto.

    Lo correcto es 500.000 × (169 ÷ 100) = 845.000. El error habitual es
    aplicar la variación acumulada desde el inicio sobre el alquiler que
    ya venía ajustado: 650.000 × 1,69 = 1.098.500, casi un 30% de más.
    """
    mecanismo = AjusteIndice('ICL', indices)

    primero = mecanismo.ajustar(monto_base, INICIO, PRIMER_AJUSTE, TRIMESTRAL)
    segundo = mecanismo.ajustar(monto_base, INICIO, SEGUNDO_AJUSTE, TRIMESTRAL)

    encadenado = primero.monto_ajustado.multiplicar(segundo.coeficiente)

    assert segundo.monto_ajustado == Dinero(Decimal('845000.00'), Moneda.ARS)
    assert segundo.monto_ajustado != encadenado.redondear()


def test_la_formula_explica_el_calculo(
    monto_base: Dinero,
    indices: IndicesEnMemoria,
) -> None:
    mecanismo = AjusteIndice('ICL', indices)

    resultado = mecanismo.ajustar(
        monto_base, INICIO, PRIMER_AJUSTE, TRIMESTRAL
    )

    assert 'ICL' in resultado.formula
    assert INICIO.isoformat() in resultado.formula


def test_indice_sin_valor_cargado_avisa(monto_base: Dinero) -> None:
    mecanismo = AjusteIndice('IPC', IndicesEnMemoria())

    with pytest.raises(IndiceNoDisponible):
        mecanismo.ajustar(monto_base, INICIO, PRIMER_AJUSTE, TRIMESTRAL)


def test_no_se_puede_ajustar_antes_de_que_venza_el_periodo(
    monto_base: Dinero,
    indices: IndicesEnMemoria,
) -> None:
    mecanismo = AjusteIndice('ICL', indices)

    with pytest.raises(ConflictoDominio):
        mecanismo.ajustar(monto_base, INICIO, date(2026, 2, 1), TRIMESTRAL)


def test_fecha_de_ajuste_anterior_al_inicio_es_invalida(
    monto_base: Dinero,
) -> None:
    mecanismo = AjusteFijo('10')

    with pytest.raises(ValidacionError):
        mecanismo.ajustar(monto_base, INICIO, date(2025, 12, 1), TRIMESTRAL)


def test_periodicidad_invalida(monto_base: Dinero) -> None:
    mecanismo = AjusteFijo('10')

    with pytest.raises(ValidacionError):
        mecanismo.ajustar(monto_base, INICIO, SEGUNDO_AJUSTE, 0)


@pytest.mark.parametrize(
    ('tasa'),
    ['-1', '1001'],
)
def test_tasa_fuera_de_rango(tasa: str) -> None:
    with pytest.raises(ValidacionError):
        AjusteFijo(tasa)


def test_la_tasa_no_acepta_float() -> None:
    with pytest.raises(TypeError):
        AjusteFijo(10.5)


def test_el_indice_exige_codigo_de_serie() -> None:
    with pytest.raises(ValidacionError):
        AjusteIndice('   ', IndicesEnMemoria())


def test_la_fabrica_crea_un_ajuste_fijo() -> None:
    mecanismo = FabricaMecanismoAjuste.crear(
        TipoAjuste.FIJO, tasa_porcentual='15'
    )

    assert isinstance(mecanismo, AjusteFijo)
    assert mecanismo.tipo is TipoAjuste.FIJO


def test_la_fabrica_crea_un_ajuste_por_indice(
    indices: IndicesEnMemoria,
) -> None:
    mecanismo = FabricaMecanismoAjuste.crear(
        'indice', serie='icl', repositorio=indices
    )

    assert isinstance(mecanismo, AjusteIndice)
    assert isinstance(mecanismo, MecanismoAjuste)
    assert mecanismo.serie == 'ICL'


def test_la_fabrica_rechaza_un_tipo_desconocido() -> None:
    with pytest.raises(ValidacionError):
        FabricaMecanismoAjuste.crear('UVA_LOCA')


def test_la_fabrica_exige_la_tasa_del_ajuste_fijo() -> None:
    with pytest.raises(ValidacionError):
        FabricaMecanismoAjuste.crear(TipoAjuste.FIJO)


def test_la_fabrica_exige_la_serie_del_ajuste_por_indice() -> None:
    with pytest.raises(ValidacionError):
        FabricaMecanismoAjuste.crear(TipoAjuste.INDICE)
