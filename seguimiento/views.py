from datetime import date, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import Min, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import floatformat
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.formats import date_format
from django.views.decorators.http import require_POST

from . import calculos
from .forms import MEDIDAS, ComidaForm, PerfilForm, RegistroDiarioForm, UsuarioForm
from .models import Comida, Perfil, RegistroDiario


def perfil_requerido(vista):
    """Exige sesión y un perfil creado; sin perfil, manda a crearlo."""

    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        perfil = Perfil.objects.filter(usuario=request.user).first()
        if perfil is None:
            messages.info(request, "Antes de empezar, completa tu perfil.")
            return redirect("perfil")
        request.perfil = perfil
        return vista(request, *args, **kwargs)

    return envoltura


PRIMERA_FECHA = date(2000, 1, 1)


def fecha_valida(texto):
    try:
        fecha = date.fromisoformat(texto)
    except ValueError:
        raise Http404("Fecha inválida")
    if not PRIMERA_FECHA <= fecha <= timezone.localdate():
        raise Http404("Fecha fuera de rango")
    return fecha


def ultimo_pesaje(usuario):
    return RegistroDiario.objects.filter(usuario=usuario, peso__isnull=False).order_by("-fecha").first()


def peso_actual(usuario, perfil):
    ultimo = ultimo_pesaje(usuario)
    return ultimo.peso if ultimo else perfil.peso_inicial


def edad_del_perfil(perfil):
    """Edad de hoy, o None si el perfil no tiene fecha de nacimiento."""
    if perfil.fecha_nacimiento is None:
        return None
    return calculos.edad(perfil.fecha_nacimiento, timezone.localdate())


def calorias_del_perfil(perfil, peso):
    """Objetivo de calorías con el peso dado y la edad de hoy; None si faltan datos."""
    return calculos.calorias_objetivo(perfil.sexo, peso, perfil.altura_cm, edad_del_perfil(perfil))


@perfil_requerido
def inicio(request):
    perfil = request.perfil
    hoy = timezone.localdate()
    ultimo = ultimo_pesaje(request.user)
    lunes = calculos.lunes_de(hoy)
    registros_semana = RegistroDiario.objects.filter(usuario=request.user, fecha__gte=lunes, fecha__lte=hoy)
    pasos_semana = {r.fecha: r.pasos for r in registros_semana}
    activas_semana = {r.fecha: r.calorias_activas for r in registros_semana}
    calorias_semana = dict(
        Comida.objects.filter(usuario=request.user, fecha__gte=lunes, fecha__lte=hoy)
        .values("fecha")
        .annotate(total=Sum("calorias"))
        .values_list("fecha", "total")
    )
    peso = ultimo.peso if ultimo else perfil.peso_inicial
    consumidas = calorias_semana.get(hoy, 0)
    calorias = calorias_del_perfil(perfil, peso)
    objetivo = calculos.objetivo_del_dia(calorias["objetivo"], activas_semana.get(hoy)) if calorias else None
    semana = (
        calculos.calorias_semana(calorias["objetivo"], calorias_semana, activas_semana, hoy) if calorias else None
    )
    return render(
        request,
        "seguimiento/inicio.html",
        {
            "perfil": perfil,
            "nombre": request.user.first_name or request.user.get_username(),
            "edad": edad_del_perfil(perfil),
            "ultimo": ultimo,
            "peso_actual": peso,
            "progreso": calculos.progreso(perfil.peso_inicial, perfil.peso_meta, peso),
            "promedio_pasos": calculos.promedio_pasos_semana(pasos_semana, hoy),
            "consumidas": consumidas,
            "calorias": calorias,
            "objetivo": objetivo,
            "restan": objetivo - consumidas if objetivo is not None else None,
            "semana": semana,
        },
    )


@perfil_requerido
def hoy(request):
    return redirect("dia", fecha=timezone.localdate().isoformat())


@perfil_requerido
def dia(request, fecha):
    fecha = fecha_valida(fecha)
    registro = RegistroDiario.objects.filter(usuario=request.user, fecha=fecha).first()

    if request.method == "POST":
        form = RegistroDiarioForm(request.POST, instance=registro)
        if form.is_valid():
            # update_or_create evita un registro duplicado si se envía dos veces seguidas.
            RegistroDiario.objects.update_or_create(
                usuario=request.user, fecha=fecha, defaults=form.cleaned_data
            )
            messages.success(request, "Día guardado.")
            return redirect("dia", fecha=fecha.isoformat())
    else:
        form = RegistroDiarioForm(instance=registro)

    return render_dia(request, fecha, registro, form, ComidaForm())


@require_POST
@perfil_requerido
def agregar_comida(request, fecha):
    fecha = fecha_valida(fecha)
    form = ComidaForm(request.POST)
    if form.is_valid():
        comida = form.save(commit=False)
        comida.usuario = request.user
        comida.fecha = fecha
        comida.save()
        messages.success(request, "Comida agregada.")
        return redirect("dia", fecha=fecha.isoformat())
    registro = RegistroDiario.objects.filter(usuario=request.user, fecha=fecha).first()
    return render_dia(request, fecha, registro, RegistroDiarioForm(instance=registro), form)


def render_dia(request, fecha, registro, form, comida_form):
    comidas = Comida.objects.filter(usuario=request.user, fecha=fecha)
    hoy = timezone.localdate()
    total_calorias = sum(c.calorias for c in comidas)
    calorias = calorias_del_perfil(request.perfil, peso_actual(request.user, request.perfil))
    activas = registro.calorias_activas if registro else None
    objetivo = calculos.objetivo_del_dia(calorias["objetivo"], activas) if calorias else None
    return render(
        request,
        "seguimiento/dia.html",
        {
            "fecha": fecha,
            "es_hoy": fecha == hoy,
            "anterior": fecha - timedelta(days=1) if fecha > PRIMERA_FECHA else None,
            "siguiente": fecha + timedelta(days=1) if fecha < hoy else None,
            "registro": registro,
            "form": form,
            "comida_form": comida_form,
            "comidas": comidas,
            "total_calorias": total_calorias,
            "calorias": calorias,
            "activas": activas,
            "objetivo": objetivo,
        },
    )


@perfil_requerido
def editar_comida(request, pk):
    comida = get_object_or_404(Comida, pk=pk, usuario=request.user)
    form = ComidaForm(request.POST or None, instance=comida)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Comida guardada.")
        return redirect("dia", fecha=comida.fecha.isoformat())
    return render(request, "seguimiento/comida.html", {"comida": comida, "form": form})


@require_POST
@perfil_requerido
def borrar_comida(request, pk):
    comida = get_object_or_404(Comida, pk=pk, usuario=request.user)
    comida.delete()
    messages.success(request, "Comida borrada.")
    return redirect("dia", fecha=comida.fecha.isoformat())


@require_POST
@perfil_requerido
def borrar_dia(request, fecha):
    fecha = fecha_valida(fecha)
    RegistroDiario.objects.filter(usuario=request.user, fecha=fecha).delete()
    Comida.objects.filter(usuario=request.user, fecha=fecha).delete()
    messages.success(request, "Día borrado.")
    return redirect("historial")


@perfil_requerido
def historial(request):
    registros = {r.fecha: r for r in RegistroDiario.objects.filter(usuario=request.user)}
    calorias = {
        fila["fecha"]: fila
        for fila in Comida.objects.filter(usuario=request.user)
        .values("fecha")
        .annotate(total=Sum("calorias"))
    }
    filas = []
    for f in sorted(registros.keys() | calorias.keys(), reverse=True):
        registro = registros.get(f)
        datos = [
            (registro.pasos if registro else None, "pasos"),
            (calorias.get(f, {}).get("total"), "kcal"),
            (registro.calorias_activas if registro else None, "kcal activas"),
        ]
        filas.append({
            "fecha": f,
            "peso": registro.peso if registro else None,
            "datos": [(valor, unidad) for valor, unidad in datos if valor is not None],
        })
    pagina = Paginator(filas, 30).get_page(request.GET.get("pagina"))
    return render(request, "seguimiento/historial.html", {"pagina": pagina})


# En la gráfica, cintura y cadera primero: son las que más dicen de la pérdida de grasa.
ORDEN_MEDIDAS = ["cintura", "cadera", *(m for m in MEDIDAS if m not in ("cintura", "cadera"))]


def fecha_corta(fecha, hoy):
    """"3 de noviembre", con el año solo si no es el actual; "hoy" si es hoy."""
    if fecha == hoy:
        return "hoy"
    formato = r"j \d\e F" if fecha.year == hoy.year else r"j \d\e F \d\e Y"
    return date_format(fecha, formato).lower()


def resumen_medida(nombre, cambio, hoy):
    """Frase bajo la gráfica de medidas, a partir de calculos.cambio_en_rango."""
    desde = fecha_corta(cambio["desde"], hoy)
    if cambio["mediciones"] == 1:
        dia = "la de hoy" if desde == "hoy" else f"la del {desde}"
        return f"Solo hay una medida de {nombre.lower()} en este rango: {dia}."
    hasta = fecha_corta(cambio["hasta"], hoy)
    periodo = f"entre el {desde} y {hasta}" if hasta == "hoy" else f"entre el {desde} y el {hasta}"
    if cambio["cambio"] == 0:
        return f"{nombre}: sin cambio {periodo}."
    signo = "−" if cambio["cambio"] < 0 else "+"
    return f"{nombre}: {signo}{floatformat(abs(cambio['cambio']), -1)} cm {periodo}."


def series_de_medidas(registros, fechas, hoy):
    """Valores por día y resumen de cada medida con datos en el rango, en ORDEN_MEDIDAS."""
    etiquetas = RegistroDiarioForm.base_fields
    series = []
    for clave in ORDEN_MEDIDAS:
        valores = {r.fecha: getattr(r, clave) for r in registros if getattr(r, clave) is not None}
        if not valores:
            continue
        # El mismo nombre que en el formulario del día.
        nombre = etiquetas[clave].label
        series.append({
            "clave": clave,
            "nombre": nombre,
            "valores": [float(valores[f]) if f in valores else None for f in fechas],
            "resumen": resumen_medida(nombre, calculos.cambio_en_rango(valores), hoy),
        })
    return series


def indice_de_medida(series, clave):
    """Posición de la medida pedida en la URL; la primera si no está en el rango."""
    claves = [m["clave"] for m in series]
    return claves.index(clave) if clave in claves else 0


@perfil_requerido
def graficas(request):
    perfil = request.perfil
    hoy = timezone.localdate()
    rango = request.GET.get("rango", calculos.RANGO_POR_DEFECTO)
    if rango not in calculos.RANGOS:
        rango = calculos.RANGO_POR_DEFECTO

    registros = RegistroDiario.objects.filter(usuario=request.user)
    comidas = Comida.objects.filter(usuario=request.user)
    primeras = [q.aggregate(f=Min("fecha"))["f"] for q in (registros, comidas)]
    primera = min((f for f in primeras if f), default=None)
    desde = calculos.inicio_de_rango(rango, hoy, primera)
    fechas = calculos.dias_entre(desde, hoy)

    # Se traen 6 días antes del rango para que el promedio móvil arranque completo.
    filas = registros.filter(fecha__gte=desde - timedelta(days=6), fecha__lte=hoy)
    pesajes = {r.fecha: float(r.peso) for r in filas if r.peso is not None}
    pasos = {r.fecha: r.pasos for r in filas if r.pasos is not None}
    activas = {r.fecha: r.calorias_activas for r in filas if r.calorias_activas is not None}
    calorias = dict(
        comidas.filter(fecha__gte=desde, fecha__lte=hoy).values("fecha").annotate(total=Sum("calorias"))
        .values_list("fecha", "total")
    )

    datos = {
        "fechas": [f.isoformat() for f in fechas],
        "peso": [pesajes.get(f) for f in fechas],
        "tendencia": calculos.promedio_movil(pesajes, fechas),
        "meta_peso": float(perfil.peso_meta),
        "pasos": [pasos.get(f) for f in fechas],
        "meta_pasos": perfil.meta_pasos,
        "calorias": [calorias.get(f) for f in fechas],
        # Las medidas no llevan promedio móvil: solo cuentan los días del rango.
        "medidas": series_de_medidas([r for r in filas if r.fecha >= desde], fechas, hoy),
    }
    medida = indice_de_medida(datos["medidas"], request.GET.get("medida"))
    datos["medida_elegida"] = medida
    # El objetivo de cada día usa el peso y la edad de hoy más las activas de ese día.
    objetivo = calorias_del_perfil(perfil, peso_actual(request.user, perfil))
    datos["objetivo_calorias"] = (
        [calculos.objetivo_del_dia(objetivo["objetivo"], activas.get(f)) for f in fechas] if objetivo else None
    )
    # Hoy no ha terminado: el resumen solo cuenta los días anteriores (el último es hoy).
    en_objetivo = (
        calculos.dias_en_objetivo(datos["calorias"][:-1], datos["objetivo_calorias"][:-1]) if objetivo else None
    )
    return render(
        request,
        "seguimiento/graficas.html",
        {
            "datos": datos,
            "rango": rango,
            "medida_actual": datos["medidas"][medida] if datos["medidas"] else None,
            "rangos": [(clave, nombre) for clave, (nombre, _) in calculos.RANGOS.items()],
            "hay_peso": any(v is not None for v in datos["peso"]),
            "hay_pasos": any(v is not None for v in datos["pasos"]),
            "hay_calorias": any(v is not None for v in datos["calorias"]),
            "en_objetivo": en_objetivo,
        },
    )


@login_required
def perfil(request):
    actual = Perfil.objects.filter(usuario=request.user).first()
    # El resumen se arma antes de validar: los formularios copian lo enviado al
    # perfil y al usuario aunque no se guarde, y el resumen debe mostrar lo guardado.
    contexto = {"nuevo": actual is None, "nombre": request.user.first_name or request.user.get_username()}
    if actual is not None:
        contexto["peso_actual"] = peso_actual(request.user, actual)
        contexto["calorias"] = calorias_del_perfil(actual, contexto["peso_actual"])
        contexto["edad"] = edad_del_perfil(actual)
        contexto["faltan_datos"] = not (actual.sexo and actual.fecha_nacimiento and actual.altura_cm)

    if request.method == "POST":
        form = PerfilForm(request.POST, instance=actual)
        usuario_form = UsuarioForm(request.POST, instance=request.user)
        if all([form.is_valid(), usuario_form.is_valid()]):
            usuario_form.save()
            nuevo = form.save(commit=False)
            nuevo.usuario = request.user
            nuevo.save()
            messages.success(request, "Perfil guardado.")
            return redirect("inicio" if actual is None else "perfil")
    else:
        inicial = {"fecha_inicio": timezone.localdate()} if actual is None else None
        form = PerfilForm(instance=actual, initial=inicial)
        usuario_form = UsuarioForm(instance=request.user)

    contexto.update(form=form, usuario_form=usuario_form)
    return render(request, "seguimiento/perfil.html", contexto)


class CambiarContrasena(SuccessMessageMixin, PasswordChangeView):
    """Cambia la contraseña sin cerrar la sesión y vuelve al perfil."""

    success_url = reverse_lazy("perfil")
    success_message = "Contraseña cambiada."
