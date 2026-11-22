// Dibuja las gráficas de peso, pasos, calorías y medidas con los datos que deja
// la vista en <script id="datos-graficas">. Se vuelven a dibujar al cambiar de
// tema y, la de medidas, al elegir otra medida.
(function () {
  var datos = JSON.parse(document.getElementById("datos-graficas").textContent);
  var graficas = [];
  var medidaElegida = 0;

  var formatoDia = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "short", timeZone: "UTC" });
  var etiquetas = datos.fechas.map(function (f) {
    return formatoDia.format(new Date(f + "T00:00:00Z"));
  });
  var numero = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 1 });
  Chart.defaults.font.family = "Bricolage Grotesque, system-ui, sans-serif";

  function color(nombre) {
    return getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
  }

  // `valor` es una meta fija o una lista con la meta de cada día.
  function lineaMeta(valor, etiqueta) {
    var porDia = Array.isArray(valor);
    return {
      type: "line",
      label: etiqueta,
      data: porDia
        ? valor
        : datos.fechas.map(function () {
            return valor;
          }),
      stepped: porDia ? "middle" : false,
      borderColor: color("--tenue"),
      borderDash: [6, 6],
      borderWidth: 1.5,
      pointRadius: 0,
      pointHoverRadius: 0,
      pointStyle: "line",
      order: 0,
    };
  }

  function opciones(unidad) {
    return {
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: color("--tenue"), usePointStyle: true, pointStyleWidth: 18, boxHeight: 8 },
        },
        tooltip: {
          filter: function (item) {
            return item.parsed.y != null;
          },
          callbacks: {
            label: function (ctx) {
              return ctx.dataset.label + ": " + numero.format(ctx.parsed.y) + " " + unidad;
            },
          },
        },
      },
      scales: {
        x: {
          ticks: { color: color("--tenue"), maxTicksLimit: 6, maxRotation: 0 },
          grid: { display: false },
          border: { color: color("--linea") },
        },
        y: {
          ticks: {
            color: color("--tenue"),
            callback: function (v) {
              return numero.format(v);
            },
          },
          grid: { color: color("--linea") },
          border: { display: false },
        },
      },
    };
  }

  // Con una sola serie la leyenda repite el chip elegido. Pocas marcas en el
  // eje: con cambios de 1 o 2 cm Chart.js pondría una cada 0,2.
  function opcionesMedidas() {
    var op = opciones("cm");
    op.plugins.legend.display = false;
    op.scales.y.ticks.maxTicksLimit = 5;
    return op;
  }

  function definiciones() {
    var acento = color("--acento");
    var linea = color("--acento-texto");
    var texto = color("--texto");
    return {
      "grafica-peso": {
        type: "line",
        data: {
          labels: etiquetas,
          datasets: [
            {
              label: "Pesaje",
              data: datos.peso,
              showLine: false,
              pointRadius: 3,
              pointBackgroundColor: texto,
              pointBorderWidth: 0,
              pointStyle: "circle",
              order: 2,
            },
            {
              label: "Promedio 7 días",
              data: datos.tendencia,
              borderColor: linea,
              borderWidth: 3,
              pointRadius: 0,
              pointStyle: "line",
              tension: 0.3,
              spanGaps: true,
              order: 1,
            },
            lineaMeta(datos.meta_peso, "Meta"),
          ],
        },
        options: opciones("kg"),
      },
      "grafica-pasos": {
        type: "bar",
        data: {
          labels: etiquetas,
          datasets: [
            { label: "Pasos", data: datos.pasos, backgroundColor: acento, borderRadius: 3, order: 1 },
            lineaMeta(datos.meta_pasos, "Meta diaria"),
          ],
        },
        options: opciones("pasos"),
      },
      "grafica-calorias": {
        type: "bar",
        data: {
          labels: etiquetas,
          datasets: [
            { label: "Consumidas", data: datos.calorias, backgroundColor: texto, borderRadius: 3, order: 1 },
          ].concat(datos.objetivo_calorias ? [lineaMeta(datos.objetivo_calorias, "Objetivo del día")] : []),
        },
        options: opciones("kcal"),
      },
      "grafica-medidas": datos.medidas.length && {
        type: "line",
        data: {
          labels: etiquetas,
          datasets: [
            {
              label: datos.medidas[medidaElegida].nombre,
              data: datos.medidas[medidaElegida].valores,
              borderColor: linea,
              borderWidth: 2.5,
              pointRadius: 4,
              pointBackgroundColor: linea,
              pointBorderWidth: 0,
              pointStyle: "circle",
              // Las medidas son espaciadas: la línea une los días medidos.
              spanGaps: true,
            },
          ],
        },
        options: opcionesMedidas(),
      },
    };
  }

  function dibujar() {
    graficas.forEach(function (g) {
      g.destroy();
    });
    graficas = [];
    var defs = definiciones();
    Object.keys(defs).forEach(function (id) {
      var lienzo = document.getElementById(id);
      if (lienzo && defs[id]) graficas.push(new Chart(lienzo, defs[id]));
    });
  }

  // Cambia la medida de la gráfica y su resumen sin recargar la página.
  var botones = document.querySelectorAll("[data-medida]");
  botones.forEach(function (boton) {
    boton.addEventListener("click", function () {
      medidaElegida = Number(boton.dataset.medida);
      botones.forEach(function (b) {
        b.setAttribute("aria-pressed", String(b === boton));
      });
      document.getElementById("resumen-medida").textContent = datos.medidas[medidaElegida].resumen;
      dibujar();
    });
  });

  dibujar();
  document.addEventListener("rumbo:tema", dibujar);
})();
