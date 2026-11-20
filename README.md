# Alquilómetro API

API REST para conocer el **costo real** de un alquiler antes de firmar y
**verificar cada ajuste** del contrato después de firmar.

Los portales de avisos acompañan al inquilino hasta que alquila; después,
cada ajuste le llega como un número nuevo que no tiene cómo comprobar.
Alquilómetro calcula lo que corresponde pagar según el contrato y detecta el
error más común: el **encadenamiento**, que aplica la variación acumulada del
índice sobre un alquiler ya ajustado en lugar de sobre el monto base.

Trabajo práctico integrador de Programación 2 (UNSAM).

## Qué hace

| Requerimiento | Endpoints | Estado |
|---|---|---|
| Autenticación (transversal) | `POST /auth/registro`, `POST /auth/login`, `GET /usuarios/me`, `PUT /usuarios/me/ingreso-referencia` | ✅ |
| Publicaciones (alta, consulta, edición, baja) | `POST /publicaciones`, `GET /publicaciones`, `GET`, `PUT` y `DELETE /publicaciones/{id}` (solo su dueño o un admin) | ✅ |
| RQ1 · Búsqueda y costo real | `GET /publicaciones?zona=&orden=...`, `GET /publicaciones/{id}/costo-real` | ✅ (orden por % del ingreso: pendiente) |
| RQ3 · Costo de entrada, costo sobre el ingreso y proyección a 12 y 24 meses | `GET /publicaciones/{id}/costo-entrada`, `/analisis`, `/proyeccion` | ✅ |
| RQ5 · Seguimiento del contrato | `POST /contratos`, `GET /contratos`, `GET /contratos/{id}`, `GET /contratos/{id}/calendario`, `GET /contratos/{id}/ajuste?fecha=` | ✅ |
| RQ5 · Verificación de ajustes | `POST /contratos/{id}/verificaciones`, `GET /contratos/{id}/verificaciones` | ✅ |
| Series de índices | `GET /indices/{serie}/valores`, `POST /indices/{serie}/valores` (solo admin) | ✅ |
| RQ2 · Búsquedas guardadas y alertas | — | Fuera del MVP |
| RQ4 · Shortlists compartidas | — | Fuera del MVP |

Los errores de dominio responden con un código HTTP coherente y un cuerpo
uniforme `{"detail": "..."}`: 401 sin token, 403 sin permiso, 404 recurso
inexistente o ajeno, 409 conflicto (por ejemplo, un ajuste después del final
del contrato), 422 datos inválidos o índice no publicado.

## Requisitos

- Python 3.13 o superior
- [Poetry](https://python-poetry.org/) 2.x

## Instalación

```bash
git clone https://github.com/MATIKRONE/alquilometro-api
cd alquilometro-api
poetry install
```

Los atajos `poetry serve`, `poetry test` y `poetry lint` usan el plugin
poethepoet, que se instala una sola vez por máquina:

```bash
poetry self add "poethepoet[poetry_plugin]"
```

Sin el plugin, todo funciona igual con `poetry run ...` (ver más abajo).

## Configuración

Copiar `.env.example` a `.env` y ajustar:

| Variable | Para qué | Por defecto |
|---|---|---|
| `DATABASE_URL` | Base de datos (SQLAlchemy) | `sqlite:///./alquilometro.db` |
| `JWT_SECRET_KEY` | Firma de los tokens: **cambiarla fuera de desarrollo** | `clave-desarrollo` |
| `JWT_MINUTOS_EXPIRACION` | Vigencia del token | `60` |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Opcionales: crean un administrador al correr la semilla | — |

## Ejecución

```bash
poetry run fastapi dev alquilometro_api/app.py   # o: poetry serve
```

La documentación interactiva queda en <http://127.0.0.1:8000/docs>.

### Datos de ejemplo

```bash
poetry run python -m alquilometro_api.semilla
```

Carga: una serie **ICL de ejemplo** (24 meses, crece 2,5% por mes desde enero
de 2025; no es la oficial del BCRA), una serie **IPC** armada con las
variaciones mensuales del INDEC (enero 2024 a octubre 2025, base dic-2023 =
100; transcriptas a mano, verificarlas contra el INDEC antes de presentarlas
como oficiales) y **20 avisos** variados (ARS y USD, ajuste fijo, por ICL, por
IPC o sin informar, con y sin datos faltantes). Los avisos pertenecen a un
usuario ADMIN `sistema@alquilometro.local` sin contraseña utilizable, así que
solo un administrador puede modificarlos. Si están definidas `ADMIN_EMAIL` y
`ADMIN_PASSWORD`, también crea un administrador (el único rol que puede
cargar índices). Es idempotente: no duplica avisos.

Para usar series oficiales, descargarlas como CSV `fecha,valor` (fecha ISO) y:

```bash
poetry run python -m alquilometro_api.semilla --csv ICL icl.csv
```

Si ya tenías un `alquilometro.db` de antes, borralo: las tablas se crean con
`create_all`, que no agrega columnas nuevas (comisión y otros gastos de
entrada) a tablas existentes.

### Recorrido de la demo

1. `POST /auth/registro` y `POST /auth/login`; pegar el token en **Authorize**.
2. `POST /contratos` con este cuerpo:
   ```json
   {
     "fecha_inicio": "2025-01-01",
     "duracion_meses": 12,
     "monto_base": {"monto": "500000", "moneda": "ARS"},
     "tipo_ajuste": "INDICE",
     "meses_periodicidad": 3,
     "serie_codigo": "ICL"
   }
   ```
3. `GET /contratos/{id}/calendario`: los tres ajustes trimestrales con su monto.
4. `POST /contratos/{id}/verificaciones` con
   `{"fecha_ajuste": "2025-07-01", "monto_informado": {"monto": "624440.47", "moneda": "ARS"}}`.
   La respuesta es `ENCADENADO`: lo correcto son $579.850 y le estaban
   cobrando $44.590,47 de más.

## Docker

```bash
docker compose up --build
```

Levanta la API en el puerto 8000 con SQLite en un volumen. Para usar
PostgreSQL: `docker compose --profile postgres up` y apuntar `DATABASE_URL` a
`postgresql+psycopg://alquilometro:alquilometro@db:5432/alquilometro`.

Al arrancar, el contenedor corre la semilla y después levanta la API, así que
siempre hay datos de demo cargados.

## Deploy

**Versión publicada:** https://alquilometro-unsam-t15n.onrender.com/
(página web) y https://alquilometro-unsam-t15n.onrender.com/docs (Swagger).

La versión publicada usa el Blueprint `frontend/render.yaml`: un solo servicio
sirve la página web en `/`, la API en `/api/` y Swagger en `/docs`. Los pasos
están en [`frontend/README.md`](frontend/README.md). El `render.yaml` de la
raíz sigue disponible para desplegar solo la API.

En el plan gratuito el servicio se duerme tras 15 minutos sin tráfico y tarda
cerca de un minuto en despertar: conviene abrirlo un rato antes de usarlo. El
disco no es persistente, así que los usuarios registrados se pierden al
reiniciar; la semilla vuelve a cargar los datos de ejemplo en cada arranque.

## Tests

```bash
poetry run pytest          # o: poetry test (corre lint + tests + cobertura)
poetry run ruff check .
```

Más de 300 tests (unitarios de dominio y servicios, y de integración contra la
API con una SQLite en memoria). Una GitHub Action corre `ruff` y `pytest` en
cada push y en cada pull request.

## Patrones de diseño


### Strategy: mecanismos de ajuste (`domain/ajuste.py`)

Desde el DNU 70/2023 cada contrato puede pactar su propio mecanismo de ajuste:
un porcentaje fijo o una serie publicada (ICL, IPC, UVA). Todos responden a la
misma pregunta, cuánto pasa a valer el alquiler, con fórmulas distintas.

`MecanismoAjuste` define la interfaz `ajustar(...)`; `AjusteFijo` y
`AjusteIndice` son las estrategias. El contrato y el servicio de contratos
usan la interfaz sin saber qué estrategia tienen. `AjusteIndice` es una sola
clase parametrizada por serie, no una subclase por índice.

La regla de oro: el ajuste por índice se calcula **siempre contra el monto
base** (`monto_base × índice actual ÷ índice inicial`), nunca encadenando.

La proyección del RQ3 reutiliza las mismas estrategias: arma un escenario de
índices futuros (el promedio de los últimos 12 meses de la serie, o una tasa
que indica el usuario) y se lo pasa a `AjusteIndice`. No tiene una fórmula
propia, así que lo proyectado y lo que después se verifica en el contrato no
pueden divergir.

### Simple Factory (`FabricaMecanismoAjuste`)

El contrato guarda un texto (`"FIJO"`, `"INDICE"`) y la fábrica lo traduce a
la estrategia concreta. Es el puente entre la persistencia y el dominio:
agregar un mecanismo nuevo es una clase y una rama en la fábrica, sin tocar
ningún servicio.

### Value Object: `Dinero` (`domain/dinero.py`)

Todos los importes son `Dinero`: inmutables, siempre `Decimal` (nunca
`float`), y no se pueden mezclar ARS con USD sin una cotización explícita. El
redondeo se aplica solo al final, para no acumular errores de centavos en los
ajustes.

### Repositorio por `Protocol` (`RepositorioIndices`)

El ajuste por índice pide los valores a un `RepositorioIndices`, que es un
`Protocol`. En producción lo cumple `RepositorioIndicesDB` (la base); en los
tests, `IndicesEnMemoria`. La estrategia no sabe de dónde vienen los datos.

## Estructura

```
alquilometro_api/
├── core/       configuración, base de datos, seguridad y JWT
├── domain/     reglas de negocio puras: Dinero, ajustes, verificación, errores
├── models/     modelos SQLAlchemy
├── schemas/    entrada y salida de la API (Pydantic)
├── services/   casos de uso que combinan dominio y persistencia
├── routers/    endpoints de FastAPI
└── semilla.py  datos de ejemplo para la demo
```
