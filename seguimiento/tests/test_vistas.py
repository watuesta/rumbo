from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from seguimiento.models import Comida, Perfil, RegistroDiario


def crear_usuario(nombre):
    usuario = User.objects.create_user(nombre, password="clave-de-prueba-123")
    Perfil.objects.create(
        usuario=usuario, peso_inicial=Decimal("90.0"), peso_meta=Decimal("80.0"), fecha_inicio=date(2026, 1, 1)
    )
    return usuario


class AccesoTests(TestCase):
    def test_sin_sesion_redirige_al_login(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertRedirects(respuesta, f"{reverse('entrar')}?next=/")

    def test_sin_perfil_pide_crearlo(self):
        self.client.force_login(User.objects.create_user("nuevo"))
        self.assertRedirects(self.client.get(reverse("inicio")), reverse("perfil"))

    def test_crear_perfil_acepta_coma_decimal(self):
        self.client.force_login(User.objects.create_user("nuevo"))
        respuesta = self.client.post(
            reverse("perfil"),
            {"peso_inicial": "92,5", "peso_meta": "75", "fecha_inicio": "2026-11-01", "meta_pasos": "8000"},
        )
        self.assertRedirects(respuesta, reverse("inicio"))
        self.assertEqual(Perfil.objects.get().peso_inicial, Decimal("92.5"))

    def test_meta_mayor_que_inicio_es_invalida(self):
        self.client.force_login(User.objects.create_user("nuevo"))
        respuesta = self.client.post(
            reverse("perfil"),
            {"peso_inicial": "80", "peso_meta": "85", "fecha_inicio": "2026-11-01", "meta_pasos": "8000"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Perfil.objects.exists())


class AislamientoTests(TestCase):
    """Cada usuario solo ve y modifica sus propios datos."""

    def setUp(self):
        self.ana = crear_usuario("ana")
        self.beto = crear_usuario("beto")
        self.hoy = timezone.localdate()
        RegistroDiario.objects.create(usuario=self.beto, fecha=self.hoy, peso=Decimal("123.4"), pasos=4321)
        self.comida_beto = Comida.objects.create(usuario=self.beto, fecha=self.hoy, calorias=777, descripcion="arepa")
        self.client.force_login(self.ana)

    def test_no_ve_datos_ajenos(self):
        for url in [reverse("inicio"), reverse("historial"), reverse("dia", args=[self.hoy.isoformat()]),
                    reverse("graficas") + "?rango=todo"]:
            contenido = self.client.get(url).content.decode()
            self.assertNotIn("123,4", contenido, url)
            self.assertNotIn("arepa", contenido, url)
            self.assertNotIn("777", contenido, url)

    def test_no_puede_borrar_comida_ajena(self):
        respuesta = self.client.post(reverse("borrar_comida", args=[self.comida_beto.pk]))
        self.assertEqual(respuesta.status_code, 404)
        self.assertTrue(Comida.objects.filter(pk=self.comida_beto.pk).exists())

    def test_borrar_dia_solo_borra_lo_propio(self):
        Comida.objects.create(usuario=self.ana, fecha=self.hoy, calorias=500)
        self.client.post(reverse("borrar_dia", args=[self.hoy.isoformat()]))
        self.assertFalse(Comida.objects.filter(usuario=self.ana).exists())
        self.assertTrue(RegistroDiario.objects.filter(usuario=self.beto).exists())
        self.assertTrue(Comida.objects.filter(usuario=self.beto).exists())

    def test_guardar_dia_crea_registro_propio(self):
        self.client.post(reverse("dia", args=[self.hoy.isoformat()]), {"peso": "88,4", "pasos": "9000"})
        registro = RegistroDiario.objects.get(usuario=self.ana)
        self.assertEqual(registro.peso, Decimal("88.4"))
        self.assertEqual(RegistroDiario.objects.get(usuario=self.beto).peso, Decimal("123.4"))


class DiaTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("ana")
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()
        self.url = reverse("dia", args=[self.hoy.isoformat()])

    def test_registrar_hoy_lleva_al_dia_de_hoy(self):
        self.assertRedirects(self.client.get(reverse("hoy")), self.url)

    def test_guardar_dos_veces_edita_el_mismo_registro(self):
        self.client.post(self.url, {"peso": "88"})
        self.client.post(self.url, {"peso": "88", "pasos": "7000"})
        self.assertEqual(RegistroDiario.objects.count(), 1)
        self.assertEqual(RegistroDiario.objects.get().pasos, 7000)

    def test_formulario_vacio_no_guarda(self):
        respuesta = self.client.post(self.url, {})
        self.assertContains(respuesta, "Escribe al menos un dato")
        self.assertFalse(RegistroDiario.objects.exists())

    def test_suma_calorias_del_dia(self):
        url = reverse("agregar_comida", args=[self.hoy.isoformat()])
        self.client.post(url, {"calorias": "450", "descripcion": "Desayuno"})
        self.client.post(url, {"calorias": "700"})
        self.assertEqual(self.client.get(self.url).context["total_calorias"], 1150)

    def test_dia_futuro_no_existe(self):
        manana = (self.hoy + timedelta(days=1)).isoformat()
        self.assertEqual(self.client.get(reverse("dia", args=[manana])).status_code, 404)
        self.assertEqual(self.client.get(reverse("dia", args=["no-es-fecha"])).status_code, 404)


class ResumenYGraficasTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("ana")
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()

    def test_resumen_usa_el_ultimo_pesaje(self):
        RegistroDiario.objects.create(usuario=self.usuario, fecha=self.hoy - timedelta(days=3), peso=Decimal("87"))
        RegistroDiario.objects.create(usuario=self.usuario, fecha=self.hoy - timedelta(days=1), peso=Decimal("86.5"))
        RegistroDiario.objects.create(usuario=self.usuario, fecha=self.hoy, pasos=5000)
        contexto = self.client.get(reverse("inicio")).context
        self.assertEqual(contexto["peso_actual"], Decimal("86.5"))
        self.assertEqual(contexto["progreso"]["perdidos"], Decimal("3.5"))
        self.assertEqual(contexto["progreso"]["faltan"], Decimal("6.5"))

    def test_graficas_traen_un_valor_por_dia_del_rango(self):
        RegistroDiario.objects.create(usuario=self.usuario, fecha=self.hoy, peso=Decimal("88"), pasos=9000)
        Comida.objects.create(usuario=self.usuario, fecha=self.hoy, calorias=1200)
        datos = self.client.get(reverse("graficas") + "?rango=30").context["datos"]
        self.assertEqual(len(datos["fechas"]), 30)
        self.assertEqual(datos["peso"][-1], 88.0)
        self.assertEqual(datos["pasos"][-1], 9000)
        self.assertEqual(datos["calorias"][-1], 1200)
        self.assertEqual(datos["meta_peso"], 80.0)


class CorreccionesTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("ana")
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()

    def test_editar_perfil_conserva_la_fecha_de_inicio(self):
        form = self.client.get(reverse("perfil")).context["form"]
        self.assertEqual(form["fecha_inicio"].value(), date(2026, 1, 1))

    def test_idioma_no_depende_del_navegador(self):
        RegistroDiario.objects.create(usuario=self.usuario, fecha=self.hoy, peso=Decimal("85.5"))
        respuesta = self.client.get(reverse("inicio"), HTTP_ACCEPT_LANGUAGE="en-US")
        self.assertContains(respuesta, "85,5")

    def test_editar_comida_propia(self):
        comida = Comida.objects.create(usuario=self.usuario, fecha=self.hoy, calorias=500)
        respuesta = self.client.post(reverse("editar_comida", args=[comida.pk]), {"calorias": "650", "descripcion": "Almuerzo"})
        self.assertRedirects(respuesta, reverse("dia", args=[self.hoy.isoformat()]))
        comida.refresh_from_db()
        self.assertEqual((comida.calorias, comida.descripcion), (650, "Almuerzo"))

    def test_no_puede_editar_comida_ajena(self):
        ajena = Comida.objects.create(usuario=crear_usuario("beto"), fecha=self.hoy, calorias=500)
        url = reverse("editar_comida", args=[ajena.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {"calorias": "1"}).status_code, 404)
        ajena.refresh_from_db()
        self.assertEqual(ajena.calorias, 500)

    def test_fecha_extrema_da_404(self):
        self.assertEqual(self.client.get(reverse("dia", args=["0001-01-01"])).status_code, 404)

    def test_envio_doble_del_mismo_formulario_no_duplica(self):
        url = reverse("dia", args=[self.hoy.isoformat()])
        # Ambos envíos parten de la página sin registro, como un doble toque.
        self.client.post(url, {"peso": "88"})
        self.client.post(url, {"peso": "87,5"})
        self.assertEqual(RegistroDiario.objects.get().peso, Decimal("87.5"))

    def test_sin_pesajes_dentro_del_rango_no_dibuja_peso(self):
        RegistroDiario.objects.create(usuario=self.usuario, fecha=self.hoy - timedelta(days=31), peso=Decimal("88"))
        self.assertFalse(self.client.get(reverse("graficas") + "?rango=30").context["hay_peso"])


class ContrasenaTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("ana")
        self.client.force_login(self.usuario)
        self.url = reverse("cambiar_contrasena")

    def test_cambiar_contrasena_mantiene_la_sesion(self):
        datos = {
            "old_password": "clave-de-prueba-123",
            "new_password1": "otra-clave-segura-456",
            "new_password2": "otra-clave-segura-456",
        }
        self.assertRedirects(self.client.post(self.url, datos), reverse("perfil"))
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("otra-clave-segura-456"))
        self.assertEqual(self.client.get(reverse("inicio")).status_code, 200)

    def test_contrasena_actual_equivocada_no_cambia(self):
        datos = {
            "old_password": "no-es-esta",
            "new_password1": "otra-clave-segura-456",
            "new_password2": "otra-clave-segura-456",
        }
        self.assertEqual(self.client.post(self.url, datos).status_code, 200)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("clave-de-prueba-123"))

    def test_sin_sesion_redirige_al_login(self):
        self.client.logout()
        respuesta = self.client.get(self.url)
        self.assertRedirects(respuesta, f"{reverse('entrar')}?next={self.url}")
