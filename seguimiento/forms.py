from decimal import Decimal

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from . import calculos
from .models import Comida, Perfil, RegistroDiario


class DecimalFlexible(forms.DecimalField):
    """Acepta coma o punto como separador decimal, según el teclado del iPhone."""

    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
        return super().to_python(value)


def decimal_widget(placeholder=""):
    return forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off", "placeholder": placeholder})


class MedidaInput(forms.TextInput):
    """Muestra 28.0 como 28 y 28.5 como 28,5."""

    def format_value(self, value):
        if isinstance(value, Decimal):
            return f"{value.normalize():f}".replace(".", ",")
        return super().format_value(value)


def medida_widget():
    return MedidaInput(attrs={"inputmode": "decimal", "autocomplete": "off", "placeholder": "--"})


def entero_widget(placeholder=""):
    return forms.NumberInput(
        attrs={"inputmode": "numeric", "pattern": "[0-9]*", "autocomplete": "off", "placeholder": placeholder}
    )


class UsuarioForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "email"]
        labels = {"first_name": "Nombre", "email": "Email"}
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "Opcional"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True


class PerfilForm(forms.ModelForm):
    EDAD_MINIMA, EDAD_MAXIMA = 14, 100

    class Meta:
        model = Perfil
        fields = [
            "sexo", "fecha_nacimiento", "altura_cm",
            "peso_inicial", "fecha_inicio", "peso_meta", "meta_pasos",
        ]
        field_classes = {"peso_inicial": DecimalFlexible, "peso_meta": DecimalFlexible}
        labels = {"fecha_nacimiento": "Fecha de nacimiento", "altura_cm": "Altura (cm)"}
        widgets = {
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "altura_cm": entero_widget(),
            "peso_inicial": decimal_widget(),
            "peso_meta": decimal_widget(),
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "meta_pasos": entero_widget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre in ("sexo", "fecha_nacimiento", "altura_cm"):
            self.fields[nombre].required = True
        self.fields["sexo"].choices = [("", "Elige"), *Perfil.SEXOS]

    def clean_fecha_nacimiento(self):
        nacimiento = self.cleaned_data["fecha_nacimiento"]
        anos = calculos.edad(nacimiento, timezone.localdate())
        if not self.EDAD_MINIMA <= anos <= self.EDAD_MAXIMA:
            raise forms.ValidationError("Revisa la fecha de nacimiento.")
        return nacimiento

    def clean(self):
        datos = super().clean()
        inicial, meta = datos.get("peso_inicial"), datos.get("peso_meta")
        if inicial is not None and meta is not None and meta >= inicial:
            self.add_error("peso_meta", "La meta debe ser menor que el peso inicial.")
        return datos


# Medidas del cuerpo en el orden en que se ven junto a la figura.
MEDIDAS_IZQUIERDA = ["pecho", "brazo", "antebrazo", "muslo"]
MEDIDAS_DERECHA = ["cuello", "cintura", "cadera", "pantorrilla"]
MEDIDAS = MEDIDAS_IZQUIERDA + MEDIDAS_DERECHA


class RegistroDiarioForm(forms.ModelForm):
    class Meta:
        model = RegistroDiario
        fields = ["peso", "pasos", "calorias_activas", *MEDIDAS]
        field_classes = {"peso": DecimalFlexible, **{m: DecimalFlexible for m in MEDIDAS}}
        labels = {
            "peso": "Peso", "pasos": "Pasos", "calorias_activas": "Calorías activas",
            **{m: m.capitalize() for m in MEDIDAS},
        }
        widgets = {
            "peso": decimal_widget(),
            "pasos": entero_widget(),
            "calorias_activas": entero_widget(),
            **{m: medida_widget() for m in MEDIDAS},
        }
        # Mensajes cortos: caben bajo los campos angostos de las medidas.
        error_messages = {
            m: {"min_value": "Mínimo %(limit_value)s cm.", "max_value": "Máximo %(limit_value)s cm."} for m in MEDIDAS
        }

    @property
    def medidas_izquierda(self):
        return [self[m] for m in MEDIDAS_IZQUIERDA]

    @property
    def medidas_derecha(self):
        return [self[m] for m in MEDIDAS_DERECHA]

    @property
    def medidas_anotadas(self):
        return sum(1 for m in MEDIDAS if self[m].value() not in (None, ""))

    @property
    def medidas_abiertas(self):
        """El desplegable se abre si ya hay medidas o si alguna tiene error."""
        return bool(self.medidas_anotadas or any(self[m].errors for m in MEDIDAS))

    def clean(self):
        datos = super().clean()
        if not self.errors and all(datos.get(c) is None for c in self.Meta.fields):
            raise forms.ValidationError("Escribe al menos un dato para guardar el día.")
        return datos


class ComidaForm(forms.ModelForm):
    class Meta:
        model = Comida
        fields = ["calorias", "descripcion"]
        labels = {"calorias": "Calorías", "descripcion": "Qué comiste"}
        widgets = {
            "calorias": entero_widget(),
            "descripcion": forms.Textarea(attrs={"rows": 2, "placeholder": "Opcional", "autocomplete": "off"}),
        }
