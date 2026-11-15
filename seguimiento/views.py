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
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import calculos
from .forms import ComidaForm, PerfilForm, RegistroDiarioForm, UsuarioForm
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


@perfil_requerido
def inicio(request):
    perfil = request.perfil
    hoy = timezone.localdate()
    ultimo = ultimo_pesaje(request.user)
    pasos_semana = dict(
        RegistroDiario.objects.filter(
            usuario=request.user, fecha__gte=hoy - timedelta(days=hoy.weekday())
        ).values_list("fecha", "pasos")
    )
    peso_actual = ultimo.peso if ultimo else perfil.peso_inicial
    return render(
        request,
        "seguimiento/inicio.html",
        {
            "perfil": perfil,
            "ultimo": ultimo,
            "peso_actual": peso_actual,
            "progreso": calculos.progreso(perfil.peso_inicial, perfil.peso_meta, peso_actual),
            "promedio_pasos": calculos.promedio_pasos_semana(pasos_semana, hoy),
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
            "total_calorias": sum(c.calorias for c in comidas),
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
        filas.append({
            "fecha": f,
            "peso": registro.peso if registro else None,
            "pasos": registro.pasos if registro else None,
            "calorias": calorias.get(f, {}).get("total"),
        })
    pagina = Paginator(filas, 30).get_page(request.GET.get("pagina"))
    return render(request, "seguimiento/historial.html", {"pagina": pagina})


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
    }
    return render(
        request,
        "seguimiento/graficas.html",
        {
            "datos": datos,
            "rango": rango,
            "rangos": [(clave, nombre) for clave, (nombre, _) in calculos.RANGOS.items()],
            "hay_peso": any(v is not None for v in datos["peso"]),
            "hay_pasos": any(v is not None for v in datos["pasos"]),
            "hay_calorias": any(v is not None for v in datos["calorias"]),
        },
    )


@login_required
def perfil(request):
    actual = Perfil.objects.filter(usuario=request.user).first()
    # El resumen se arma antes de validar: los formularios copian lo enviado al
    # perfil y al usuario aunque no se guarde, y el resumen debe mostrar lo guardado.
    contexto = {"nuevo": actual is None, "nombre": request.user.first_name or request.user.get_username()}
    if actual is not None:
        ultimo = ultimo_pesaje(request.user)
        contexto["peso_actual"] = ultimo.peso if ultimo else actual.peso_inicial
        if actual.fecha_nacimiento:
            contexto["edad"] = calculos.edad(actual.fecha_nacimiento, timezone.localdate())
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
