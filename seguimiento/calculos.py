"""Cálculos del resumen y de las gráficas.

Funciones puras sobre fechas y números: no consultan la base de datos, así que
se prueban sin fixtures.
"""

from datetime import timedelta
from decimal import Decimal

# Clave en la URL: (nombre en pantalla, días hacia atrás; None es todo).
RANGOS = {"30": ("30 días", 30), "90": ("90 días", 90), "todo": ("Todo", None)}
RANGO_POR_DEFECTO = "30"


def inicio_de_rango(rango, hoy, primera_fecha):
    """Primer día que muestra la gráfica para un rango válido de RANGOS."""
    dias = RANGOS[rango][1]
    if dias is None:
        return min(primera_fecha or hoy, hoy)
    return hoy - timedelta(days=dias - 1)


def dias_entre(desde, hasta):
    return [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]


def promedio_movil(pesajes, fechas, ventana=7):
    """Promedio de los pesajes de los últimos `ventana` días de calendario.

    `pesajes` es un dict {fecha: peso}. Devuelve un valor por cada fecha de
    `fechas` (None si no hubo pesajes en esa ventana). Los días sin pesaje no
    cuentan, porque no todos los días hay pesaje.
    """
    resultado = []
    for dia in fechas:
        ventana_dias = (dia - timedelta(days=i) for i in range(ventana))
        valores = [pesajes[d] for d in ventana_dias if d in pesajes]
        resultado.append(round(sum(valores) / len(valores), 2) if valores else None)
    return resultado


def promedio_pasos_semana(pasos_por_fecha, hoy):
    """Promedio de pasos de lunes a hoy, contando solo los días con pasos."""
    lunes = hoy - timedelta(days=hoy.weekday())
    valores = [p for f, p in pasos_por_fecha.items() if lunes <= f <= hoy and p is not None]
    return round(sum(valores) / len(valores)) if valores else None


def edad(fecha_nacimiento, hoy):
    """Años cumplidos. Quien nació un 29 de febrero los cumple el 1 de marzo."""
    antes_del_cumpleanos = (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    return hoy.year - fecha_nacimiento.year - antes_del_cumpleanos


def progreso(peso_inicial, peso_meta, peso_actual):
    """Kilos perdidos, kilos que faltan y fracción del camino recorrido (0 a 1)."""
    perdidos = peso_inicial - peso_actual
    faltan = max(peso_actual - peso_meta, Decimal("0"))
    total = peso_inicial - peso_meta
    fraccion = float(perdidos / total) if total > 0 else 1.0
    return {
        "perdidos": perdidos,
        "faltan": faltan,
        "fraccion": min(max(fraccion, 0.0), 1.0),
    }
