from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    """
    Configuración de la app: variables de entorno o archivo '.env'
    """

    # TODO: SQLite para desarrolo y tests; postgresql + psycopg al final
    DATABASE_URL: str = 'sqlite:///./alquilometro.db'
    sql_echo: bool = False

    # Cambiar jwt_secret_key en produccion
    jwt_secret_key: str = 'clave-desarrollo'
    jwt_algoritmo: str = 'HS256'
    jwt_minutos_expiracion: int = 60

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )


@lru_cache
def get_config() -> Configuracion:
    return Configuracion()
