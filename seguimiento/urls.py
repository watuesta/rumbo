from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("hoy/", views.hoy, name="hoy"),
    path("dia/<str:fecha>/", views.dia, name="dia"),
    path("dia/<str:fecha>/comida/", views.agregar_comida, name="agregar_comida"),
    path("dia/<str:fecha>/borrar/", views.borrar_dia, name="borrar_dia"),
    path("comida/<int:pk>/", views.editar_comida, name="editar_comida"),
    path("comida/<int:pk>/borrar/", views.borrar_comida, name="borrar_comida"),
    path("historial/", views.historial, name="historial"),
    path("graficas/", views.graficas, name="graficas"),
    path("perfil/", views.perfil, name="perfil"),
    path("perfil/contrasena/", views.CambiarContrasena.as_view(), name="cambiar_contrasena"),
]
