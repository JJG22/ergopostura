"""Reglas del NIT colombiano. Sin dependencias de Django para probarlas de forma aislada."""
import re
from dataclasses import dataclass

# Pesos oficiales de la DIAN, aplicados de derecha a izquierda.
_WEIGHTS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)
_PATTERN = re.compile(r"^([1-9]\d{5,9})(?:-(\d))?$")


class InvalidNit(ValueError):
    pass


def check_digit(number: str) -> int:
    total = sum(int(digit) * weight for digit, weight in zip(reversed(number), _WEIGHTS))
    remainder = total % 11
    return remainder if remainder < 2 else 11 - remainder


@dataclass(frozen=True)
class Nit:
    """Se guarda solo el numero base: el digito de verificacion se deriva de el.

    Asi 900.123.456-8, 900123456-8 y 900123456 son la misma empresa.
    """

    number: str

    @classmethod
    def parse(cls, raw: str) -> "Nit":
        cleaned = re.sub(r"[\s.]", "", raw or "")
        match = _PATTERN.match(cleaned)
        if not match:
            raise InvalidNit("Escribe un NIT válido, por ejemplo 900.123.456-8.")

        number, given_digit = match.groups()
        if given_digit is not None and int(given_digit) != check_digit(number):
            raise InvalidNit("El dígito de verificación no corresponde a este NIT.")

        # 9001234568 sin guion puede ser un NIT de 9 digitos con su verificacion pegada.
        # Aceptarlo como numero de 10 digitos permitiria registrar dos veces la misma empresa.
        if given_digit is None and len(number) == 10 and int(number[-1]) == check_digit(number[:-1]):
            raise InvalidNit("Separa el dígito de verificación con un guion, por ejemplo 900123456-8.")

        return cls(number)

    @property
    def check_digit(self) -> int:
        return check_digit(self.number)

    def __str__(self) -> str:
        grouped = f"{int(self.number):,}".replace(",", ".")
        return f"{grouped}-{self.check_digit}"
