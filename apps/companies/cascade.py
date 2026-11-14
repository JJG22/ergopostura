"""Listas dependientes: elegir un registro solo entre las opciones permitidas.

Las opciones se calculan en el servidor a partir de lo elegido y de lo que el usuario puede
ver. Un valor enviado a mano que no esta entre las opciones se descarta, y el formulario lo
rechaza.
"""


def pick(queryset, value):
    """Devuelve el registro elegido si pertenece a las opciones permitidas."""
    try:
        return queryset.filter(pk=value).first()
    except (TypeError, ValueError):
        return None
