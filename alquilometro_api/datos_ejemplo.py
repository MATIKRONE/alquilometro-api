"""Tabla de avisos de ejemplo para la semilla (ver semilla.py)."""

# ruff: noqa: E501, C408
from alquilometro_api.domain.moneda import Moneda

CALLES = (
    'Av. Santa Fe', 'Av. Cabildo', 'Av. Rivadavia', 'Thames', 'Defensa',
    'Av. Corrientes', 'Warnes', 'Av. Díaz Vélez', 'Av. Triunvirato',
    'Gorriti',
)  # fmt: skip

# zona, tipo, ambientes, m², alquiler, opciones
AVISOS_DE_EJEMPLO: tuple[tuple[object, ...], ...] = (
    ('Palermo', 'departamento', 2, 45, 650000, dict(expensas=85000, abl=12000, seguro=180000, dur=24, garantia='seguro de caución', mascotas=True, ajuste='ICL', deposito=650000, comision=650000)),
    ('Palermo', 'departamento', 1, 32, 520000, dict(expensas=60000, abl=9000, dur=24, garantia='garantía propietaria', mascotas=False, ajuste='IPC', deposito=520000)),
    ('Caballito', 'departamento', 3, 70, 780000, dict(expensas=110000, abl=15000, seguro=240000, dur=36, garantia='seguro de caución', mascotas=True, ajuste='ICL', comision=780000)),
    ('Caballito', 'ph', 2, 55, 590000, dict(abl=8000, dur=24, garantia='recibo de sueldo', mascotas=True, ajuste='FIJO 30')),
    ('Belgrano', 'departamento', 3, 85, 1100000, dict(expensas=180000, abl=25000, seguro=330000, dur=36, garantia='seguro de caución', mascotas=False, ajuste='ICL', deposito=1100000, comision=1100000, otros=150000)),
    ('Belgrano', 'departamento', 2, 52, 900000, dict(expensas=140000, dur=24, garantia='seguro de caución', mascotas=False, ajuste='IPC')),
    ('Villa Urquiza', 'casa', 4, 120, 1300000, dict(abl=30000, dur=24, garantia='garantía propietaria', mascotas=True, ajuste='IPC')),
    ('Villa Urquiza', 'departamento', 1, 30, 430000, dict(expensas=45000, abl=7000, seguro=130000, dur=24, garantia='seguro de caución', mascotas=False, ajuste='FIJO 25')),
    ('Almagro', 'departamento', 2, 48, 560000, dict(expensas=70000, abl=10000, dur=24, garantia='garantía propietaria', mascotas=True, ajuste='ICL', patrocinada=True)),
    ('Almagro', 'ph', 3, 75, 700000, dict(expensas=20000, abl=11000, dur=36, garantia='recibo de sueldo', mascotas=True)),
    ('Recoleta', 'departamento', 3, 95, 1400000, dict(expensas=250000, abl=35000, seguro=420000, dur=36, garantia='seguro de caución', mascotas=False, ajuste='ICL', deposito=1400000, comision=1400000)),
    ('Recoleta', 'departamento', 1, 38, 800000, dict(expensas=120000, abl=14000, dur=24, garantia='seguro de caución', mascotas=False, ajuste='IPC', patrocinada=True)),
    ('San Telmo', 'ph', 2, 60, 620000, dict(expensas=25000, abl=9000, dur=24, garantia='garantía propietaria', mascotas=True, ajuste='FIJO 35')),
    ('San Telmo', 'departamento', 1, None, 480000, dict(expensas=50000, garantia='recibo de sueldo')),
    ('Núñez', 'departamento', 2, 50, 550, dict(moneda=Moneda.USD, expensas=70, abl=9, dur=24, garantia='garantía propietaria', mascotas=True, ajuste='FIJO 12')),
    ('Puerto Madero', 'departamento', 3, 110, 1800, dict(moneda=Moneda.USD, expensas=400, abl=60, seguro=3000, dur=36, garantia='seguro de caución', mascotas=False, ajuste='FIJO 10', deposito=1800, comision=1800)),
    ('Colegiales', 'departamento', 2, 47, 610000, dict(expensas=80000, abl=9500, seguro=170000, dur=24, garantia='seguro de caución', mascotas=True, ajuste='IPC')),
    ('Flores', 'departamento', 2, 58, 480000, dict(expensas=55000, abl=7000, dur=24, garantia='recibo de sueldo', mascotas=True, ajuste='FIJO 28')),
    ('Devoto', 'casa', 3, 110, 950000, dict(abl=20000, dur=36, garantia='garantía propietaria', mascotas=True, ajuste='ICL')),
    ('Saavedra', 'ph', 2, 62, 540000, dict(expensas=30000, abl=8000, seguro=150000, dur=24, garantia='seguro de caución', mascotas=False, ajuste='IPC')),
)  # fmt: skip
