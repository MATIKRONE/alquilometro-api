from decimal import Decimal
from http import HTTPStatus

from fastapi.testclient import TestClient

from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.schemas.publicacion import DineroEntrada


def datos_publicacion() -> dict[str, object]:
    return {
        'propiedad': {
            'direccion': 'Avenida Rivadavia 5500',
            'zona': 'Caballito',
            'tipo': 'departamento',
            'ambientes': 2,
            'metros_cuadrados': '45',
            'permite_mascotas': True,
        },
        'precio_alquiler': {'monto': '650000', 'moneda': 'ARS'},
        'expensas_mensuales': {'monto': '85000', 'moneda': 'ARS'},
        'abl_mensual': {'monto': '12000', 'moneda': 'ARS'},
        'seguro_caucion': {'monto': '180000', 'moneda': 'ARS'},
        'duracion_contrato_meses': 24,
        'tipo_garantia_aceptada': 'seguro de caución',
    }


def crear_publicacion(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
    datos: dict[str, object],
):
    return cliente.post(
        '/publicaciones',
        json=datos,
        headers=headers_inmobiliaria,
    )


def test_crear_publicacion(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    respuesta = crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_publicacion(),
    )

    assert respuesta.status_code == HTTPStatus.CREATED
    assert respuesta.json()['id'] == 1
    assert respuesta.json()['propiedad']['zona'] == 'Caballito'
    assert respuesta.json()['precio_alquiler'] == {
        'monto': '650000.00',
        'moneda': 'ARS',
    }


def test_listar_publicaciones(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_publicacion(),
    )

    respuesta = cliente.get('/publicaciones')

    assert respuesta.status_code == HTTPStatus.OK
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]['id'] == 1


def test_crear_publicacion_rechaza_un_precio_negativo(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    datos = datos_publicacion()
    datos['precio_alquiler'] = {'monto': '-1', 'moneda': 'ARS'}

    respuesta = crear_publicacion(cliente, headers_inmobiliaria, datos)

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


def test_crear_publicacion_expensas_cero_da_201(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    datos = datos_publicacion()
    datos['expensas_mensuales'] = {'monto': '0', 'moneda': 'ARS'}

    respuesta = crear_publicacion(cliente, headers_inmobiliaria, datos)

    assert respuesta.status_code == HTTPStatus.CREATED
    assert respuesta.json()['expensas_mensuales']['monto'] == '0.00'


def test_crear_publicacion_alquiler_cero_da_422(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    datos = datos_publicacion()
    datos['precio_alquiler'] = {'monto': '0', 'moneda': 'ARS'}

    respuesta = crear_publicacion(cliente, headers_inmobiliaria, datos)

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


def test_crear_publicacion_moneda_eur_da_422(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    datos = datos_publicacion()
    datos['precio_alquiler'] = {'monto': '650000', 'moneda': 'EUR'}

    respuesta = crear_publicacion(cliente, headers_inmobiliaria, datos)

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


def test_crear_publicacion_tres_decimales_da_422(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    datos = datos_publicacion()
    datos['precio_alquiler'] = {'monto': '650000.125', 'moneda': 'ARS'}

    respuesta = crear_publicacion(cliente, headers_inmobiliaria, datos)

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


def test_listar_publicaciones_vacio_devuelve_lista_vacia(
    cliente: TestClient,
) -> None:
    respuesta = cliente.get('/publicaciones')

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json() == []


def test_crear_publicacion_sin_propiedad_da_422(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    datos = datos_publicacion()
    del datos['propiedad']

    respuesta = crear_publicacion(cliente, headers_inmobiliaria, datos)

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


def test_crear_publicacion_en_usd_da_201(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    datos = datos_publicacion()
    datos['precio_alquiler'] = {'monto': '650000', 'moneda': 'USD'}

    respuesta = crear_publicacion(cliente, headers_inmobiliaria, datos)

    assert respuesta.status_code == HTTPStatus.CREATED
    assert respuesta.json()['precio_alquiler']['moneda'] == 'USD'


def test_crear_publicacion_fijo_sin_tasa_da_422(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    datos = datos_publicacion()
    datos['tipo_ajuste'] = 'FIJO'

    respuesta = crear_publicacion(cliente, headers_inmobiliaria, datos)

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


def test_crear_publicacion_indice_sin_serie_codigo_da_422(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    datos = datos_publicacion()
    datos['tipo_ajuste'] = 'INDICE'
    datos['tasa_ajuste'] = '10.5'

    respuesta = crear_publicacion(cliente, headers_inmobiliaria, datos)

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


def test_crear_publicacion_indice_con_serie_codigo_da_201(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    datos = datos_publicacion()
    datos['tipo_ajuste'] = 'INDICE'
    datos['serie_codigo'] = 'ICL'

    respuesta = crear_publicacion(cliente, headers_inmobiliaria, datos)

    assert respuesta.status_code == HTTPStatus.CREATED
    assert respuesta.json()['tipo_ajuste'] == 'INDICE'
    assert respuesta.json()['serie_codigo'] == 'ICL'


def test_consultar_costo_real_de_una_publicacion(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_publicacion(),
    )

    respuesta = cliente.get('/publicaciones/1/costo-real')

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()['total'] == {
        'monto': '754500.00',
        'moneda': 'ARS',
    }
    assert respuesta.json()['faltantes'] == []
    assert respuesta.json()['componentes_informados'][
        'seguro_caucion_prorrateado'
    ] == {
        'monto': '7500.00',
        'moneda': 'ARS',
    }


def test_consultar_costo_real_de_publicacion_inexistente_da_404(
    cliente: TestClient,
) -> None:
    respuesta = cliente.get('/publicaciones/999/costo-real')

    assert respuesta.status_code == HTTPStatus.NOT_FOUND
    assert respuesta.json()['detail'] == 'No encontramos esa publicación.'


def test_consultar_analisis_calcula_porcentaje_sobre_el_ingreso(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_publicacion(),
    )

    cliente.put(
        '/usuarios/me/ingreso-referencia',
        json={
            'monto': '1500000',
            'moneda': 'ARS',
        },
        headers=headers_inmobiliaria,
    )

    respuesta = cliente.get(
        '/publicaciones/1/analisis',
        headers=headers_inmobiliaria,
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert respuesta.json()['porcentaje_ingreso'] == '50.30'
    assert respuesta.json()['costo_real']['total'] == {
        'monto': '754500.00',
        'moneda': 'ARS',
    }


def test_consultar_analisis_sin_ingreso_referencia_da_422(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_publicacion(),
    )

    respuesta = cliente.get(
        '/publicaciones/1/analisis',
        headers=headers_inmobiliaria,
    )

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert respuesta.json()['detail'] == (
        'Primero cargá tu ingreso de referencia.'
    )


def test_a_dominio_a_dinero() -> None:
    dinero = DineroEntrada(monto=Decimal('10.50'), moneda=Moneda.USD)

    assert dinero.a_dominio() == Dinero(Decimal('10.50'), Moneda.USD)
