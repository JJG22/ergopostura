import json
from functools import lru_cache
from pathlib import Path

from django import template
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

register = template.Library()


@lru_cache(maxsize=1)
def _icons() -> dict:
    path = Path(__file__).resolve().parent.parent / "icons.json"
    return json.loads(path.read_text(encoding="utf-8"))


@register.simple_tag
def icon(name: str):
    """Dibuja un icono del diseno. Un nombre inexistente falla para detectarlo pronto."""
    parts = []
    for tag, attributes in _icons()[name]:
        rendered = format_html_join(" ", '{}="{}"', attributes.items())
        parts.append(format_html("<{} {}></{}>", mark_safe(tag), rendered, mark_safe(tag)))
    return format_html(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">{}</svg>',
        mark_safe("".join(parts)),
    )
