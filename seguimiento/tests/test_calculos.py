from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from seguimiento import calculos


class PromedioMovilTests(SimpleTestCase):
    def test_promedia_solo_los_dias_con_pesaje_en_la_ventana(self):
        pesajes = {date(2026, 11, 1): 90.0, date(2026, 11, 4): 88.0, date(2026, 11, 7): 86.0}
        fechas = calculos.dias_entre(date(2026, 11, 7), date(2026, 11, 8))
        # El 7 entran los tres pesajes; el 8 el del día 1 ya quedó fuera de la ventana.
        self.assertEqual(calculos.promedio_movil(pesajes, fechas), [88.0, 87.0])

    def test_sin_pesajes_en_la_ventana_devuelve_none(self):
        pesajes = {date(2026, 11, 1): 90.0}
        self.assertEqual(calculos.promedio_movil(pesajes, [date(2026, 11, 10)]), [None])


class PromedioPasosSemanaTests(SimpleTestCase):
    def test_cuenta_de_lunes_a_hoy_e_ignora_dias_sin_pasos(self):
        hoy = date(2026, 11, 12)  # jueves
        pasos = {
            date(2026, 11, 8): 20_000,  # domingo anterior: fuera
            date(2026, 11, 9): 6_000,
            date(2026, 11, 10): None,
            date(2026, 11, 11): 9_000,
        }
        self.assertEqual(calculos.promedio_pasos_semana(pasos, hoy), 7_500)

    def test_sin_pasos_devuelve_none(self):
        self.assertIsNone(calculos.promedio_pasos_semana({}, date(2026, 11, 12)))


class ProgresoTests(SimpleTestCase):
    def test_a_mitad_de_camino(self):
        r = calculos.progreso(Decimal("90.0"), Decimal("80.0"), Decimal("85.0"))
        self.assertEqual(r["perdidos"], Decimal("5.0"))
        self.assertEqual(r["faltan"], Decimal("5.0"))
        self.assertEqual(r["fraccion"], 0.5)

    def test_por_encima_del_inicio_no_avanza(self):
        r = calculos.progreso(Decimal("90.0"), Decimal("80.0"), Decimal("91.0"))
        self.assertEqual(r["perdidos"], Decimal("-1.0"))
        self.assertEqual(r["fraccion"], 0.0)

    def test_pasada_la_meta_no_faltan_kilos(self):
        r = calculos.progreso(Decimal("90.0"), Decimal("80.0"), Decimal("79.0"))
        self.assertEqual(r["faltan"], Decimal("0"))
        self.assertEqual(r["fraccion"], 1.0)


class InicioDeRangoTests(SimpleTestCase):
    def test_rangos(self):
        hoy = date(2026, 11, 30)
        self.assertEqual(calculos.inicio_de_rango("30", hoy, None), date(2026, 11, 1))
        self.assertEqual(calculos.inicio_de_rango("todo", hoy, date(2026, 1, 5)), date(2026, 1, 5))
        self.assertEqual(calculos.inicio_de_rango("todo", hoy, None), hoy)
        self.assertEqual(calculos.inicio_de_rango("90", hoy, None), date(2026, 9, 2))
