from decimal import Decimal

from fastapi import status
from fastapi.testclient import TestClient

from alquilometro_api.app import app
from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.domain.moneda import Moneda
from alquilometro_api.schemas.publicacion import DineroEntrada

client = TestClient(app)


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


def test_crear_publicacion() -> None:
    response = client.post('/publicaciones', json=datos_publicacion())

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()['id'] == 1
    assert response.json()['propiedad']['zona'] == 'Caballito'
    assert response.json()['precio_alquiler'] == {
        'monto': '650000',
        'moneda': 'ARS',
    }


def test_listar_publicaciones() -> None:
    client.post('/publicaciones', json=datos_publicacion())

    response = client.get('/publicaciones')

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]['id'] == 1


def test_crear_publicacion_rechaza_un_precio_negativo() -> None:
    datos = datos_publicacion()
    datos['precio_alquiler'] = {'monto': '-1', 'moneda': 'ARS'}

    response = client.post('/publicaciones', json=datos)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_crear_publicacion_expensas_cero_da_201() -> None:
    datos = datos_publicacion()
    datos['expensas_mensuales'] = {'monto': '0', 'moneda': 'ARS'}

    response = client.post('/publicaciones', json=datos)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()['expensas_mensuales']['monto'] == '0'


def test_crear_publicacion_alquiler_cero_da_422() -> None:
    datos = datos_publicacion()
    datos['precio_alquiler'] = {'monto': '0', 'moneda': 'ARS'}

    response = client.post('/publicaciones', json=datos)

    # Verifica que actúe nuestro @field_validator
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_crear_publicacion_moneda_eur_da_422() -> None:
    datos = datos_publicacion()
    datos['precio_alquiler']['moneda'] = 'EUR'

    response = client.post('/publicaciones', json=datos)

    # Falla porque EUR no está en el Enum de Moneda
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_crear_publicacion_tres_decimales_da_422() -> None:
    datos = datos_publicacion()
    datos['precio_alquiler']['monto'] = '650000.125'

    response = client.post('/publicaciones', json=datos)

    # Falla por el decimal_places=2 de Pydantic
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_listar_publicaciones_vacio_devuelve_lista_vacia() -> None:
    response = client.get('/publicaciones')

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_crear_publicacion_sin_propiedad_da_422() -> None:
    datos = datos_publicacion()
    del datos['propiedad']

    response = client.post('/publicaciones', json=datos)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_crear_publicacion_en_usd_da_201() -> None:
    datos = datos_publicacion()
    datos['precio_alquiler']['moneda'] = 'USD'

    response = client.post('/publicaciones', json=datos)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()['precio_alquiler']['moneda'] == 'USD'


def test_crear_publicacion_fijo_sin_tasa_da_422() -> None:
    datos = datos_publicacion()
    datos['tipo_ajuste'] = 'FIJO'
    # No enviamos tasa_ajuste
    response = client.post('/publicaciones', json=datos)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_crear_publicacion_indice_sin_serie_codigo_da_422() -> None:
    datos = datos_publicacion()
    datos['tipo_ajuste'] = 'INDICE'
    datos['tasa_ajuste'] = '10.5'
    # No enviamos el campo serie_codigo

    response = client.post('/publicaciones', json=datos)

    # Verifica que actúe nuestro @model_validator de coherencia
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_crear_publicacion_indice_con_serie_codigo_da_201() -> None:
    datos = datos_publicacion()
    datos['tipo_ajuste'] = 'INDICE'
    datos['serie_codigo'] = 'ICL'
    # No enviamos el campo tasa ajuste

    response = client.post('/publicaciones', json=datos)

    # Verifica que actúe nuestro @model_validator de coherencia
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()['tipo_ajuste'] == 'INDICE'
    assert response.json()['serie_codigo'] == 'ICL'


def test_a_dominio_a_dinero() -> None:
    d = DineroEntrada(monto=Decimal('10.50'), moneda=Moneda.USD)
    assert d.a_dominio() == Dinero(Decimal('10.50'), Moneda.USD)
