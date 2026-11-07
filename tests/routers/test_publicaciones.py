import pytest
from fastapi import status
from fastapi.testclient import TestClient

from alquilometro_api.app import app
from alquilometro_api.routers.publicaciones import publicaciones

client = TestClient(app)


@pytest.fixture(autouse=True)
def limpiar_publicaciones() -> None:
    publicaciones.clear()


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
        'costo_caucion_total': {'monto': '180000', 'moneda': 'ARS'},
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
