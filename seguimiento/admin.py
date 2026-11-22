from django.contrib import admin

from .models import Comida, Perfil, RegistroDiario


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ["usuario", "peso_inicial", "peso_meta", "fecha_inicio", "meta_pasos"]


@admin.register(RegistroDiario)
class RegistroDiarioAdmin(admin.ModelAdmin):
    list_display = ["usuario", "fecha", "peso", "pasos", "cintura", "cadera"]
    list_filter = ["usuario"]
    date_hierarchy = "fecha"


@admin.register(Comida)
class ComidaAdmin(admin.ModelAdmin):
    list_display = ["usuario", "fecha", "calorias", "descripcion"]
    list_filter = ["usuario"]
    date_hierarchy = "fecha"
