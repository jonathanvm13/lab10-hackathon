"""Dígito de control ISO 7064 MOD 97-10 sobre letras y dígitos ASCII.

Cada letra ASCII vale 1..26, cada dígito ASCII vale tal cual y el resto de
caracteres se ignora. La comparación con el segmento recibido es textual:
`02` no es `2` (`docs/standards/openapi.yml`).
"""

from app.configuracion import CONSTANTE_CONTROL, FACTOR_CONTROL, MODULO_CONTROL

_CERO = "0"
_LONGITUD_MINIMA = 1
_LONGITUD_MAXIMA = 2
_BASE_LETRA = 64


def calcular_control(mensaje: str) -> str:
    """Calcula el control textual de un mensaje sin el segmento de control.

    Args:
        mensaje: Texto anterior al último `;`, o cadena vacía.

    Returns:
        Control en decimal, sin ceros a la izquierda, en el rango 2..98.
    """
    numero = _numero(mensaje)
    valor = CONSTANTE_CONTROL - (numero * FACTOR_CONTROL) % MODULO_CONTROL
    return str(valor)


def formato_valido(control: str) -> bool:
    """Indica si el control trae uno o dos dígitos ASCII.

    Args:
        control: Último segmento del mensaje, sin recortar.

    Returns:
        `True` cuando el formato es aceptable. El valor se compara aparte.
    """
    if not _LONGITUD_MINIMA <= len(control) <= _LONGITUD_MAXIMA:
        return False
    return all("0" <= caracter <= "9" for caracter in control)


def coincide(recibido: str, mensaje: str) -> bool:
    """Compara el control recibido con el calculado, como texto.

    Args:
        recibido: Segmento de control tal como llegó.
        mensaje: Mensaje sin ese segmento.

    Returns:
        `True` solo si los textos son idénticos.
    """
    return recibido == calcular_control(mensaje)


def _numero(mensaje: str) -> int:
    piezas: list[str] = []
    for caracter in mensaje:
        if "a" <= caracter <= "z" or "A" <= caracter <= "Z":
            piezas.append(str(ord(caracter.upper()) - _BASE_LETRA))
        elif "0" <= caracter <= "9":
            piezas.append(caracter)
    return int("".join(piezas) or _CERO)
