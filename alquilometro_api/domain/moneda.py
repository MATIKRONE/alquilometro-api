from enum import StrEnum


class Moneda(StrEnum):
    """Monedas con las que la API conserva importes."""

    ARS = 'ARS'
    USD = 'USD'

    @property
    def decimales(self) -> int:
        """Cantidad de decimales de la regla de redondeo de la moneda."""
        return _DECIMALES[self]


_DECIMALES: dict[Moneda, int] = {
    Moneda.ARS: 2,
    Moneda.USD: 2,
}
