from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def peso_field(**kwargs):
    return models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(20), MaxValueValidator(400)],
        **kwargs,
    )


def medida_field(verbose_name):
    return models.DecimalField(
        verbose_name,
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(30), MaxValueValidator(300)],
    )


class Perfil(models.Model):
    SEXOS = [("F", "Mujer"), ("M", "Hombre")]

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    peso_inicial = peso_field(verbose_name="peso inicial (kg)")
    fecha_inicio = models.DateField("fecha de inicio")
    peso_meta = peso_field(verbose_name="peso meta (kg)")
    meta_pasos = models.PositiveIntegerField(
        "meta diaria de pasos", default=8000, validators=[MinValueValidator(1), MaxValueValidator(100_000)]
    )
    # Opcionales en la base porque hay perfiles creados antes; el formulario los exige.
    sexo = models.CharField(max_length=1, choices=SEXOS, blank=True)
    fecha_nacimiento = models.DateField("fecha de nacimiento", null=True, blank=True)
    altura_cm = models.PositiveSmallIntegerField(
        "altura (cm)", null=True, blank=True, validators=[MinValueValidator(100), MaxValueValidator(250)]
    )

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfiles"

    def __str__(self):
        return f"Perfil de {self.usuario}"


class RegistroDiario(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registros")
    fecha = models.DateField()
    peso = peso_field(verbose_name="peso (kg)", null=True, blank=True)
    pasos = models.PositiveIntegerField(null=True, blank=True, validators=[MaxValueValidator(200_000)])
    calorias_activas = models.PositiveIntegerField(
        "calorías activas", null=True, blank=True, validators=[MaxValueValidator(5_000)]
    )
    cintura = medida_field("cintura (cm)")
    cadera = medida_field("cadera (cm)")

    class Meta:
        verbose_name = "registro diario"
        verbose_name_plural = "registros diarios"
        ordering = ["-fecha"]
        constraints = [
            models.UniqueConstraint(fields=["usuario", "fecha"], name="un_registro_por_dia"),
        ]

    def __str__(self):
        return f"{self.usuario} · {self.fecha}"


class Comida(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comidas")
    fecha = models.DateField()
    calorias = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10_000)])
    descripcion = models.CharField("descripción", max_length=250, blank=True)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "comida"
        verbose_name_plural = "comidas"
        ordering = ["fecha", "creada"]
        indexes = [models.Index(fields=["usuario", "fecha"])]

    def __str__(self):
        return f"{self.calorias} kcal · {self.fecha}"
