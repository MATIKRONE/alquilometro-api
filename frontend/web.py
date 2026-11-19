"""Publica la interfaz y conecta sus consultas con la API del TP."""

from pathlib import Path

from starlette.responses import FileResponse

from alquilometro_api.app import app as api

CARPETA = Path(__file__).resolve().parent
ARCHIVOS = {
    '/': ('index.html', 'text/html'),
    '/index.html': ('index.html', 'text/html'),
    '/style.css': ('style.css', 'text/css'),
    '/app.js': ('app.js', 'text/javascript'),
}


async def app(scope, receive, send):
    if scope['type'] == 'http':
        ruta = scope['path']
        if ruta.startswith('/api/'):
            scope = {**scope, 'path': ruta[4:]}
            if 'raw_path' in scope:
                scope['raw_path'] = scope['raw_path'][4:]
        elif scope['method'] in {'GET', 'HEAD'} and ruta in ARCHIVOS:
            nombre, tipo = ARCHIVOS[ruta]
            respuesta = FileResponse(CARPETA / nombre, media_type=tipo)
            await respuesta(scope, receive, send)
            return

    await api(scope, receive, send)
