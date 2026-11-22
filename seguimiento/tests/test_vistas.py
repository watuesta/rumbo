from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from seguimiento import calculos
from seguimiento.models import Comida, Perfil, RegistroDiario


def crear_usuario(nombre):
    usuario = User.objects.create_user(nombre, password="clave-de-prueba-123")
    Perfil.objects.create(
        usuario=usuario, peso_inicial=Decimal("90.0"), peso_meta=Decimal("80.0"), fecha_inicio=date(2026, 1, 1)
    )
    return usuario


def datos_perfil(**cambios):
    """POST válido del formulario de perfil, con datos inventados."""
    datos = {
        "first_name": "Ana", "email": "", "sexo": "F", "fecha_nacimiento": "1990-05-20", "altura_cm": "165",
        "peso_inicial": "92,5", "peso_meta": "75", "fecha_inicio": "2026-11-01", "meta_pasos": "8000",
    }
    return {**datos, **cambios}


class AccesoTests(TestCase):
    def test_sin_sesion_redirige_al_login(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertRedirects(respuesta, f"{reverse('entrar')}?next=/")

    def test_sin_perfil_pide_crearlo(self):
        self.client.force_login(User.objects.create_user("nuevo"))
        self.assertRedirects(self.client.get(reverse("inicio")), reverse("perfil"))

    def test_crear_perfil_acepta_coma_decimal(self):
        self.client.force_login(User.objects.create_user("nuevo"))
        respuesta = self.client.post(reverse("perfil"), datos_perfil())
        self.assertRedirects(respuesta, reverse("inicio"))
        self.assertEqual(Perfil.objects.get().peso_inicial, Decimal("92.5"))

    def test_meta_mayor_que_inicio_es_invalida(self):
        self.client.force_login(User.objects.create_user("nuevo"))
        respuesta = self.client.post(reverse("perfil"), datos_perfil(peso_inicial="80", peso_meta="85"))
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

    def test_guarda_las_medidas_del_cuerpo(self):
        medidas = {
            "pecho": "95,5", "cuello": "34", "brazo": "28", "antebrazo": "24,5",
            "cintura": "80", "cadera": "100", "muslo": "55", "pantorrilla": "36",
        }
        self.client.post(self.url, medidas)
        registro = RegistroDiario.objects.get()
        self.assertEqual(registro.pecho, Decimal("95.5"))
        self.assertEqual(registro.antebrazo, Decimal("24.5"))
        self.assertEqual(registro.pantorrilla, Decimal("36"))
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, '<details class="medidas" open>')
        self.assertContains(respuesta, "8 de 8 en cm")
        self.assertContains(respuesta, 'value="95,5"')
        self.assertContains(respuesta, 'value="100"')

    def test_una_sola_medida_basta_para_guardar_el_dia(self):
        self.client.post(self.url, {"pantorrilla": "36"})
        self.assertEqual(RegistroDiario.objects.get().pantorrilla, Decimal("36"))

    def test_medida_fuera_de_rango_abre_el_desplegable(self):
        respuesta = self.client.post(self.url, {"peso": "88", "brazo": "5"})
        self.assertFalse(RegistroDiario.objects.exists())
        self.assertTrue(respuesta.context["form"].errors["brazo"])
        self.assertContains(respuesta, '<details class="medidas" open>')

    def test_sin_medidas_el_desplegable_sale_cerrado(self):
        RegistroDiario.objects.create(usuario=self.usuario, fecha=self.hoy, peso=Decimal("88"))
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, '<details class="medidas">')
        self.assertContains(respuesta, "En cm, opcionales")

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

    def test_descripcion_larga_de_comida(self):
        url = reverse("agregar_comida", args=[self.hoy.isoformat()])
        self.client.post(url, {"calorias": "500", "descripcion": "a" * 250})
        self.assertEqual(Comida.objects.get().descripcion, "a" * 250)
        respuesta = self.client.post(url, {"calorias": "500", "descripcion": "a" * 251})
        self.assertContains(respuesta, "250 caracteres")
        self.assertEqual(Comida.objects.count(), 1)

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


class DatosPerfilTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("ana")
        self.client.force_login(self.usuario)

    def test_guarda_datos_personales_y_muestra_la_edad(self):
        respuesta = self.client.post(reverse("perfil"), datos_perfil(email="ana@ejemplo.com"))
        self.assertRedirects(respuesta, reverse("perfil"))
        self.usuario.refresh_from_db()
        perfil = self.usuario.perfil
        self.assertEqual((self.usuario.first_name, self.usuario.email), ("Ana", "ana@ejemplo.com"))
        self.assertEqual((perfil.sexo, perfil.altura_cm, perfil.fecha_nacimiento), ("F", 165, date(1990, 5, 20)))
        hoy = timezone.localdate()
        self.assertEqual(self.client.get(reverse("perfil")).context["edad"], calculos.edad(date(1990, 5, 20), hoy))

    def test_fecha_de_nacimiento_futura_es_invalida(self):
        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        respuesta = self.client.post(reverse("perfil"), datos_perfil(fecha_nacimiento=manana))
        self.assertContains(respuesta, "Revisa la fecha de nacimiento")
        self.assertIsNone(Perfil.objects.get().fecha_nacimiento)

    def test_nombre_y_datos_nuevos_son_obligatorios(self):
        respuesta = self.client.post(reverse("perfil"), datos_perfil(first_name="", sexo="", altura_cm=""))
        self.assertEqual(respuesta.status_code, 200)
        for campo in ("sexo", "altura_cm"):
            self.assertTrue(respuesta.context["form"].has_error(campo))
        self.assertTrue(respuesta.context["usuario_form"].has_error("first_name"))

    def test_envio_con_errores_no_cambia_el_resumen(self):
        respuesta = self.client.post(reverse("perfil"), datos_perfil(first_name="Pepe", altura_cm="50"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["faltan_datos"])
        self.assertIsNone(respuesta.context["edad"])
        self.assertContains(respuesta, "Salir de ana")

    def test_perfil_viejo_sin_datos_nuevos_sigue_funcionando(self):
        self.assertEqual(self.client.get(reverse("inicio")).status_code, 200)
        contexto = self.client.get(reverse("perfil")).context
        self.assertTrue(contexto["faltan_datos"])
        self.assertIsNone(contexto["edad"])


def completar_perfil(usuario):
    """Agrega los datos para calcular calorías y devuelve el objetivo con el peso inicial (90 kg)."""
    perfil = usuario.perfil
    perfil.sexo, perfil.altura_cm = "F", 165
    perfil.fecha_nacimiento = date(1990, 5, 20)
    perfil.save()
    edad = calculos.edad(perfil.fecha_nacimiento, timezone.localdate())
    return calculos.calorias_objetivo("F", Decimal("90"), 165, edad)["objetivo"]


class CaloriasObjetivoVistasTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("ana")
        self.objetivo = completar_perfil(self.usuario)
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()

    def test_inicio_muestra_lo_que_queda_del_objetivo(self):
        Comida.objects.create(usuario=self.usuario, fecha=self.hoy, calorias=600)
        contexto = self.client.get(reverse("inicio")).context
        self.assertEqual(contexto["consumidas"], 600)
        self.assertEqual(contexto["restan"], self.objetivo - 600)

    def test_dia_compara_el_total_con_el_objetivo(self):
        Comida.objects.create(usuario=self.usuario, fecha=self.hoy, calorias=3000)
        respuesta = self.client.get(reverse("dia", args=[self.hoy.isoformat()]))
        # La app separa los miles con punto.
        objetivo = f"{self.objetivo:,}".replace(",", ".")
        self.assertContains(respuesta, f"3.000 de {objetivo} kcal")

    def test_usa_el_ultimo_pesaje(self):
        RegistroDiario.objects.create(usuario=self.usuario, fecha=self.hoy, peso=Decimal("80"))
        edad = calculos.edad(date(1990, 5, 20), self.hoy)
        esperado = calculos.calorias_objetivo("F", Decimal("80"), 165, edad)
        self.assertEqual(self.client.get(reverse("perfil")).context["calorias"], esperado)

    def test_sin_datos_del_perfil_invita_a_completarlo(self):
        perfil = self.usuario.perfil
        perfil.altura_cm = None
        perfil.save()
        respuesta = self.client.get(reverse("inicio"))
        self.assertIsNone(respuesta.context["calorias"])
        self.assertContains(respuesta, "Completa tu perfil")


class CaloriasActivasTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("ana")
        self.objetivo = completar_perfil(self.usuario)
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()
        self.url = reverse("dia", args=[self.hoy.isoformat()])

    def test_guardar_solo_calorias_activas(self):
        self.assertRedirects(self.client.post(self.url, {"calorias_activas": "350"}), self.url)
        self.assertEqual(RegistroDiario.objects.get().calorias_activas, 350)

    def test_las_activas_se_suman_al_objetivo_del_dia(self):
        RegistroDiario.objects.create(usuario=self.usuario, fecha=self.hoy, calorias_activas=350)
        Comida.objects.create(usuario=self.usuario, fecha=self.hoy, calorias=500)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.context["objetivo"], self.objetivo + 350)
        self.assertContains(respuesta, "500 de " + f"{self.objetivo + 350:,}".replace(",", ".") + " kcal")
        self.assertEqual(self.client.get(reverse("inicio")).context["restan"], self.objetivo + 350 - 500)

    def test_historial_muestra_las_activas(self):
        RegistroDiario.objects.create(usuario=self.usuario, fecha=self.hoy, pasos=8000, calorias_activas=350)
        fila = self.client.get(reverse("historial")).context["pagina"][0]
        self.assertEqual(fila["datos"], [(8000, "pasos"), (350, "kcal activas")])


class GraficaCaloriasTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("ana")
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()
        self.url = reverse("graficas") + "?rango=30"

    def test_objetivo_de_cada_dia_suma_las_activas(self):
        objetivo = completar_perfil(self.usuario)
        ayer = self.hoy - timedelta(days=1)
        RegistroDiario.objects.create(usuario=self.usuario, fecha=ayer, calorias_activas=400)
        Comida.objects.create(usuario=self.usuario, fecha=ayer, calorias=objetivo + 300)
        Comida.objects.create(usuario=self.usuario, fecha=self.hoy, calorias=objetivo + 300)
        anteayer = self.hoy - timedelta(days=2)
        Comida.objects.create(usuario=self.usuario, fecha=anteayer, calorias=objetivo + 300)
        contexto = self.client.get(self.url).context
        self.assertEqual(contexto["datos"]["objetivo_calorias"][-2:], [objetivo + 400, objetivo])
        # Ayer las activas lo dejan dentro, anteayer se pasó y hoy no cuenta porque no ha terminado.
        self.assertEqual(contexto["en_objetivo"], {"dentro": 1, "con_comidas": 2})

    def test_la_linea_usa_el_ultimo_pesaje(self):
        completar_perfil(self.usuario)
        RegistroDiario.objects.create(usuario=self.usuario, fecha=self.hoy, peso=Decimal("80"))
        esperado = calculos.calorias_objetivo("F", Decimal("80"), 165, calculos.edad(date(1990, 5, 20), self.hoy))
        objetivos = self.client.get(self.url).context["datos"]["objetivo_calorias"]
        self.assertEqual(objetivos[-1], esperado["objetivo"])

    def test_sin_datos_del_perfil_no_hay_linea_de_objetivo(self):
        Comida.objects.create(usuario=self.usuario, fecha=self.hoy, calorias=1500)
        respuesta = self.client.get(self.url)
        self.assertIsNone(respuesta.context["datos"]["objetivo_calorias"])
        self.assertContains(respuesta, "para ver tu objetivo en la gráfica")


class InicioNombreTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("ana")
        self.client.force_login(self.usuario)

    def test_muestra_nombre_y_edad(self):
        self.usuario.first_name = "Ana"
        self.usuario.save()
        completar_perfil(self.usuario)
        respuesta = self.client.get(reverse("inicio"))
        edad = calculos.edad(self.usuario.perfil.fecha_nacimiento, timezone.localdate())
        self.assertContains(respuesta, f"Ana <span>{edad} años</span>", html=False)

    def test_sin_nombre_ni_nacimiento_usa_el_usuario(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertIsNone(respuesta.context["edad"])
        self.assertContains(respuesta, '<h1 class="ruta-quien">ana</h1>', html=True)


class CaloriasSemanaVistasTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("ana")
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()
        self.lunes = self.hoy - timedelta(days=self.hoy.weekday())

    def test_suma_de_lunes_a_hoy_sin_la_semana_anterior(self):
        objetivo = completar_perfil(self.usuario)
        Comida.objects.create(usuario=self.usuario, fecha=self.hoy, calorias=700)
        Comida.objects.create(usuario=self.usuario, fecha=self.lunes, calorias=400)
        Comida.objects.create(usuario=self.usuario, fecha=self.lunes - timedelta(days=1), calorias=2500)
        otro = crear_usuario("eva")
        Comida.objects.create(usuario=otro, fecha=self.hoy, calorias=900)
        semana = self.client.get(reverse("inicio")).context["semana"]
        self.assertEqual(semana["consumidas"], 1100)
        self.assertEqual(semana["dias_restantes"], 7 - self.hoy.weekday())
        # Entran el lunes (si ya pasó), hoy y lo que falta; los demás días pasados no tienen comidas.
        dias = semana["dias_restantes"] + (1 if self.hoy > self.lunes else 0)
        self.assertEqual(semana["presupuesto"], objetivo * dias)

    def test_sin_datos_del_perfil_no_hay_semana(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertIsNone(respuesta.context["semana"])
        self.assertNotContains(respuesta, "Esta semana")
