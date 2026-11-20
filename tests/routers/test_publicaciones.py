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


def test_listar_publicaciones_filtradas_por_zona(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    caballito = crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_publicacion(),
    )

    datos_palermo = datos_publicacion()
    datos_palermo['propiedad'] = {
        **datos_palermo['propiedad'],
        'zona': 'Palermo',
    }
    crear_publicacion(cliente, headers_inmobiliaria, datos_palermo)

    respuesta = cliente.get(
        '/publicaciones',
        params={'zona': 'Caballito'},
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert [publicacion['id'] for publicacion in respuesta.json()] == [
        caballito.json()['id'],
    ]


def test_listar_publicaciones_filtradas_por_ambientes(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    dos_ambientes = crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_publicacion(),
    )

    datos_tres_ambientes = datos_publicacion()
    datos_tres_ambientes['propiedad'] = {
        **datos_tres_ambientes['propiedad'],
        'ambientes': 3,
    }
    crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_tres_ambientes,
    )

    respuesta = cliente.get(
        '/publicaciones',
        params={'ambientes': 2},
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert [publicacion['id'] for publicacion in respuesta.json()] == [
        dos_ambientes.json()['id'],
    ]


def test_listar_publicaciones_rechaza_cero_ambientes(
    cliente: TestClient,
) -> None:
    respuesta = cliente.get(
        '/publicaciones',
        params={'ambientes': 0},
    )

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


def test_listar_publicaciones_combina_filtros(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    buscada = crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_publicacion(),
    )

    datos_no_coincidente = datos_publicacion()
    datos_no_coincidente['propiedad'] = {
        **datos_no_coincidente['propiedad'],
        'permite_mascotas': False,
    }
    datos_no_coincidente['tipo_garantia_aceptada'] = 'garantía propietaria'
    crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_no_coincidente,
    )

    respuesta = cliente.get(
        '/publicaciones',
        params={
            'zona': 'Caballito',
            'ambientes': 2,
            'permite_mascotas': True,
            'tipo_garantia': 'seguro de caución',
        },
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert [publicacion['id'] for publicacion in respuesta.json()] == [
        buscada.json()['id'],
    ]


def test_listar_publicaciones_filtradas_por_rango_de_alquiler(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    dentro_del_rango = crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_publicacion(),
    )

    datos_fuera_del_rango = datos_publicacion()
    datos_fuera_del_rango['precio_alquiler'] = {
        'monto': '800000',
        'moneda': 'ARS',
    }
    crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_fuera_del_rango,
    )

    datos_en_dolares = datos_publicacion()
    datos_en_dolares['precio_alquiler'] = {
        'monto': '650',
        'moneda': 'USD',
    }
    crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_en_dolares,
    )

    respuesta = cliente.get(
        '/publicaciones',
        params={
            'alquiler_min': '600000',
            'alquiler_max': '700000',
            'moneda': 'ARS',
        },
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert [publicacion['id'] for publicacion in respuesta.json()] == [
        dentro_del_rango.json()['id'],
    ]


def test_listar_publicaciones_filtradas_por_costo_real(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    dentro_del_rango = crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_publicacion(),
    )

    datos_con_expensas_altas = datos_publicacion()
    datos_con_expensas_altas['expensas_mensuales'] = {
        'monto': '200000',
        'moneda': 'ARS',
    }
    crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_con_expensas_altas,
    )

    respuesta = cliente.get(
        '/publicaciones',
        params={
            'costo_real_min': '700000',
            'costo_real_max': '800000',
            'moneda': 'ARS',
        },
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert [publicacion['id'] for publicacion in respuesta.json()] == [
        dentro_del_rango.json()['id'],
    ]


def test_listar_publicaciones_ordenadas_por_alquiler_descendente(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    alquiler_menor = crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_publicacion(),
    )

    datos_alquiler_mayor = datos_publicacion()
    datos_alquiler_mayor['precio_alquiler'] = {
        'monto': '800000',
        'moneda': 'ARS',
    }
    alquiler_mayor = crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_alquiler_mayor,
    )

    respuesta = cliente.get(
        '/publicaciones',
        params={
            'moneda': 'ARS',
            'orden': 'alquiler',
            'descendente': 'true',
        },
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert [publicacion['id'] for publicacion in respuesta.json()] == [
        alquiler_mayor.json()['id'],
        alquiler_menor.json()['id'],
    ]


def test_listar_publicaciones_ordenadas_por_costo_real_descendente(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    costo_menor = crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_publicacion(),
    )

    datos_con_expensas_altas = datos_publicacion()
    datos_con_expensas_altas['expensas_mensuales'] = {
        'monto': '200000',
        'moneda': 'ARS',
    }
    costo_mayor = crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_con_expensas_altas,
    )

    respuesta = cliente.get(
        '/publicaciones',
        params={
            'moneda': 'ARS',
            'orden': 'costo_real',
            'descendente': 'true',
        },
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert [publicacion['id'] for publicacion in respuesta.json()] == [
        costo_mayor.json()['id'],
        costo_menor.json()['id'],
    ]


def test_listar_publicaciones_ordenadas_por_precio_m2_descendente(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    precio_m2_mayor = crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_publicacion(),
    )

    datos_precio_m2_menor = datos_publicacion()
    datos_precio_m2_menor['propiedad'] = {
        **datos_precio_m2_menor['propiedad'],
        'metros_cuadrados': '80',
    }
    datos_precio_m2_menor['precio_alquiler'] = {
        'monto': '800000',
        'moneda': 'ARS',
    }
    precio_m2_menor = crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_precio_m2_menor,
    )

    datos_sin_metros = datos_publicacion()
    datos_sin_metros['propiedad'] = {
        **datos_sin_metros['propiedad'],
        'metros_cuadrados': None,
    }
    sin_metros = crear_publicacion(
        cliente,
        headers_inmobiliaria,
        datos_sin_metros,
    )

    respuesta = cliente.get(
        '/publicaciones',
        params={
            'moneda': 'ARS',
            'orden': 'precio_m2',
            'descendente': 'true',
        },
    )

    assert respuesta.status_code == HTTPStatus.OK
    assert [publicacion['id'] for publicacion in respuesta.json()] == [
        precio_m2_mayor.json()['id'],
        precio_m2_menor.json()['id'],
        sin_metros.json()['id'],
    ]


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


def test_consultar_analisis_con_monedas_distintas_da_422(
    cliente: TestClient,
    headers_inmobiliaria: dict[str, str],
) -> None:
    datos = datos_publicacion()
    for campo in ('precio_alquiler', 'expensas_mensuales', 'abl_mensual'):
        datos[campo] = {'monto': '700', 'moneda': 'USD'}
    datos['seguro_caucion'] = None
    crear_publicacion(cliente, headers_inmobiliaria, datos)
    cliente.put(
        '/usuarios/me/ingreso-referencia',
        json={'monto': '1500000', 'moneda': 'ARS'},
        headers=headers_inmobiliaria,
    )

    respuesta = cliente.get(
        '/publicaciones/1/analisis',
        headers=headers_inmobiliaria,
    )

    assert respuesta.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert 'sin una cotización' in respuesta.json()['detail']


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
