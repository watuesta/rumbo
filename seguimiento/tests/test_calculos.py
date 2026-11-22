from datetime import date, timedelta
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


class EdadTests(SimpleTestCase):
    def test_cumple_anos_el_dia_del_cumpleanos(self):
        self.assertEqual(calculos.edad(date(1990, 5, 20), date(2026, 5, 19)), 35)
        self.assertEqual(calculos.edad(date(1990, 5, 20), date(2026, 5, 20)), 36)

    def test_nacido_el_29_de_febrero_cumple_el_1_de_marzo(self):
        self.assertEqual(calculos.edad(date(2000, 2, 29), date(2026, 2, 28)), 25)
        self.assertEqual(calculos.edad(date(2000, 2, 29), date(2026, 3, 1)), 26)


class CaloriasObjetivoTests(SimpleTestCase):
    def test_mujer_con_deficit_de_500(self):
        # Reposo: 10·70 + 6,25·165 − 5·30 − 161 = 1420,25; mantenimiento ×1,2 = 1704,3.
        calorias = calculos.calorias_objetivo("F", Decimal("70"), 165, 30)
        self.assertEqual((calorias["reposo"], calorias["mantenimiento"], calorias["objetivo"]), (1420, 1704, 1204))

    def test_hombre_con_deficit_de_500(self):
        # Reposo: 10·90 + 6,25·180 − 5·35 + 5 = 1855; mantenimiento ×1,2 = 2226.
        calorias = calculos.calorias_objetivo("M", Decimal("90"), 180, 35)
        self.assertEqual((calorias["mantenimiento"], calorias["objetivo"]), (2226, 1726))

    def test_objetivo_no_baja_del_minimo_seguro(self):
        self.assertEqual(calculos.calorias_objetivo("F", Decimal("50"), 150, 60)["objetivo"], 1200)
        self.assertEqual(calculos.calorias_objetivo("M", Decimal("55"), 160, 70)["objetivo"], 1500)

    def test_sin_datos_completos_no_hay_objetivo(self):
        self.assertIsNone(calculos.calorias_objetivo("", Decimal("70"), 165, 30))
        self.assertIsNone(calculos.calorias_objetivo("X", Decimal("70"), 165, 30))
        self.assertIsNone(calculos.calorias_objetivo("F", Decimal("70"), None, 30))
        self.assertIsNone(calculos.calorias_objetivo("F", Decimal("70"), 165, None))


class ObjetivoDelDiaTests(SimpleTestCase):
    def test_suma_las_calorias_activas(self):
        self.assertEqual(calculos.objetivo_del_dia(1500, 350), 1850)

    def test_sin_calorias_activas_queda_el_objetivo(self):
        self.assertEqual(calculos.objetivo_del_dia(1500, None), 1500)


class CaloriasSemanaTests(SimpleTestCase):
    # El 16 de noviembre de 2026 es lunes.
    LUNES = date(2026, 11, 16)

    def test_el_lunes_cuenta_los_siete_dias(self):
        semana = calculos.calorias_semana(1500, {self.LUNES: 600}, {}, self.LUNES)
        self.assertEqual(semana["presupuesto"], 7 * 1500)
        self.assertEqual(semana["restan"], 7 * 1500 - 600)
        self.assertEqual(semana["dias_restantes"], 7)
        # Lo comido hoy no achica el promedio: sigue siendo el objetivo completo.
        self.assertEqual(semana["por_dia"], 1500)
        self.assertEqual(semana["domingo"], date(2026, 11, 22))

    def test_dia_pasado_sin_comidas_sale_del_presupuesto(self):
        miercoles = self.LUNES + timedelta(days=2)
        calorias = {self.LUNES: 1400, self.LUNES - timedelta(days=1): 3000}
        semana = calculos.calorias_semana(1500, calorias, {}, miercoles)
        # Cuentan lunes, hoy y los cuatro que faltan; el martes no. El domingo anterior es de otra semana.
        self.assertEqual(semana["presupuesto"], 6 * 1500)
        self.assertEqual(semana["consumidas"], 1400)
        self.assertEqual(semana["dias_sin_comidas"], 1)
        self.assertEqual(semana["dias_restantes"], 5)

    def test_las_activas_suman_al_presupuesto(self):
        domingo = self.LUNES + timedelta(days=6)
        calorias = {self.LUNES + timedelta(days=i): 1500 for i in range(6)}
        semana = calculos.calorias_semana(1500, calorias, {self.LUNES: 300, domingo: 200}, domingo)
        self.assertEqual(semana["presupuesto"], 7 * 1500 + 500)
        self.assertEqual(semana["restan"], 1500 + 500)
        self.assertEqual(semana["por_dia"], 2000)

    def test_restan_negativo_si_te_pasas(self):
        sabado = self.LUNES + timedelta(days=5)
        calorias = {self.LUNES + timedelta(days=i): 3000 for i in range(6)}
        semana = calculos.calorias_semana(1500, calorias, {}, sabado)
        self.assertEqual(semana["restan"], 7 * 1500 - 6 * 3000)
        # Lo que quedaba al empezar el sábado, repartido entre sábado y domingo.
        self.assertEqual(semana["por_dia"], (7 * 1500 - 5 * 3000) // 2)

    def test_por_dia_reparte_el_margen_de_los_dias_pasados(self):
        miercoles = self.LUNES + timedelta(days=2)
        calorias = {self.LUNES: 1200, self.LUNES + timedelta(days=1): 1300, miercoles: 800}
        semana = calculos.calorias_semana(1500, calorias, {}, miercoles)
        # Lunes y martes dejaron 500 kcal de margen para los cinco días que quedan.
        self.assertEqual(semana["por_dia"], 1600)


class DiasEnObjetivoTests(SimpleTestCase):
    def test_cuenta_solo_dias_con_comidas(self):
        calorias = [1500, None, 2100, 1800]
        objetivos = [1700, 1700, 2050, 1800]
        # 1500 ≤ 1700 y 1800 ≤ 1800 quedan dentro; el día sin comidas no cuenta.
        self.assertEqual(calculos.dias_en_objetivo(calorias, objetivos), {"dentro": 2, "con_comidas": 3})


class CambioEnRangoTests(SimpleTestCase):
    def test_compara_la_primera_y_la_ultima_medida_aunque_lleguen_desordenadas(self):
        valores = {date(2026, 11, 15): Decimal("79.5"), date(2026, 11, 1): Decimal("82.5"), date(2026, 11, 8): Decimal("81")}
        resultado = calculos.cambio_en_rango(valores)
        self.assertEqual(resultado["desde"], date(2026, 11, 1))
        self.assertEqual(resultado["hasta"], date(2026, 11, 15))
        self.assertEqual(resultado["mediciones"], 3)
        self.assertEqual(resultado["cambio"], Decimal("-3.0"))

    def test_con_una_sola_medida_no_hay_cambio(self):
        resultado = calculos.cambio_en_rango({date(2026, 11, 1): Decimal("80")})
        self.assertEqual(resultado["mediciones"], 1)
        self.assertEqual(resultado["cambio"], 0)

    def test_sin_medidas_devuelve_none(self):
        self.assertIsNone(calculos.cambio_en_rango({}))
