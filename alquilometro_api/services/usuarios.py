from sqlalchemy.orm import Session

from alquilometro_api.domain.dinero import Dinero
from alquilometro_api.models.usuario import Usuario


class ServicioUsuarios:
    """Datos del perfil del usuario (más allá del login)."""

    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def actualizar_ingreso_referencia(
        self, usuario: Usuario, ingreso: Dinero | None
    ) -> Usuario:
        """Guarda el ingreso (o lo borra con None); debe ser mayor a cero."""
        usuario.ingreso_referencia = ingreso
        self.sesion.add(usuario)
        self.sesion.commit()
        return usuario
