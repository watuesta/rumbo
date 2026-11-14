from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("entrar/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="entrar"),
    path("salir/", auth_views.LogoutView.as_view(), name="salir"),
    path("", include("seguimiento.urls")),
]
