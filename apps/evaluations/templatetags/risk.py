from django import template
from django.utils.html import format_html

from apps.rula.risk import TrafficLight, action_level_for

register = template.Library()

_CSS = {
    TrafficLight.GREEN: "risk-adecuado",
    TrafficLight.YELLOW: "risk-revision",
    TrafficLight.RED: "risk-intervencion",
}


@register.simple_tag
def risk_badge(score):
    """Semaforo con su significado en texto (RNF-004): el color nunca va solo."""
    if score is None:
        return format_html('<span class="status status-neutral">Sin resultado</span>')
    action = action_level_for(score)
    return format_html(
        '<span class="risk {}"><i></i>{} · Nivel {}</span>',
        _CSS[action.traffic_light],
        action.traffic_light_meaning,
        action.level,
    )
