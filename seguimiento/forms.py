from django import forms

from .models import Comida, Perfil, RegistroDiario


class DecimalFlexible(forms.DecimalField):
    """Acepta coma o punto como separador decimal, según el teclado del iPhone."""

    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
        return super().to_python(value)


def decimal_widget(placeholder=""):
    return forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off", "placeholder": placeholder})


def entero_widget(placeholder=""):
    return forms.NumberInput(
        attrs={"inputmode": "numeric", "pattern": "[0-9]*", "autocomplete": "off", "placeholder": placeholder}
    )


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ["peso_inicial", "fecha_inicio", "peso_meta", "meta_pasos"]
        field_classes = {"peso_inicial": DecimalFlexible, "peso_meta": DecimalFlexible}
        widgets = {
            "peso_inicial": decimal_widget(),
            "peso_meta": decimal_widget(),
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "meta_pasos": entero_widget(),
        }

    def clean(self):
        datos = super().clean()
        inicial, meta = datos.get("peso_inicial"), datos.get("peso_meta")
        if inicial is not None and meta is not None and meta >= inicial:
            self.add_error("peso_meta", "La meta debe ser menor que el peso inicial.")
        return datos


class RegistroDiarioForm(forms.ModelForm):
    class Meta:
        model = RegistroDiario
        fields = ["peso", "pasos", "cintura", "cadera"]
        field_classes = {"peso": DecimalFlexible, "cintura": DecimalFlexible, "cadera": DecimalFlexible}
        labels = {"peso": "Peso", "pasos": "Pasos", "cintura": "Cintura", "cadera": "Cadera"}
        widgets = {
            "peso": decimal_widget(),
            "pasos": entero_widget(),
            "cintura": decimal_widget(),
            "cadera": decimal_widget(),
        }

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
            "descripcion": forms.TextInput(attrs={"placeholder": "Opcional", "autocomplete": "off"}),
        }
