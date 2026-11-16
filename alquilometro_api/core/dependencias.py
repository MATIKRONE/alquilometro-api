from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from alquilometro_api.core.database import get_session
from alquilometro_api.domain.errores import NoAutenticado
from alquilometro_api.models.usuario import Usuario
from alquilometro_api.services.auth import ServicioAuth

seguridad_http = HTTPBearer(auto_error=False)


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(
        seguridad_http,
    ),
    sesion: Session = Depends(get_session),
) -> Usuario:
    """Obtiene el usuario dueño del token enviado en la request."""
    if credenciales is None:
        raise NoAutenticado('Se requiere un token de acceso.')

    servicio_auth = ServicioAuth(sesion)
    return servicio_auth.usuario_actual(credenciales.credentials)
