from django import template
from django.template.defaultfilters import floatformat

register = template.Library()


@register.filter
def kg(valor):
    """Peso o medida con un decimal y coma decimal: 84,2."""
    return "" if valor is None else floatformat(valor, 1)


@register.filter
def kg_abs(valor):
    return "" if valor is None else floatformat(abs(valor), 1)
