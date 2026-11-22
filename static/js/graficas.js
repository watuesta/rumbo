// Dibuja las gráficas de peso, pasos, calorías y medidas con los datos que deja
// la vista en <script id="datos-graficas">. Se vuelven a dibujar al cambiar de
// tema y, la de medidas, al elegir otra medida.
(function () {
  var datos = JSON.parse(document.getElementById("datos-graficas").textContent);
  // La vista elige la medida según ?medida= de la URL (la primera si no hay).
  var medidaElegida = datos.medida_elegida || 0;

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

  // Crea (o vuelve a crear) una gráfica con su definición actual.
  function dibujarUna(id, defs) {
    var lienzo = document.getElementById(id);
    if (!lienzo || !defs[id]) return;
    var previa = Chart.getChart(lienzo);
    if (previa) previa.destroy();
    new Chart(lienzo, defs[id]);
  }

  function dibujar() {
    var defs = definiciones();
    Object.keys(defs).forEach(function (id) {
      dibujarUna(id, defs);
    });
  }

  // Elegir otra medida cambia solo su gráfica y su resumen, sin recargar. La
  // medida queda en la URL y en los enlaces de rango para conservarla al cambiar
  // de rango.
  var botones = Array.prototype.slice.call(document.querySelectorAll("[data-medida]"));

  function elegirMedida(boton) {
    medidaElegida = Number(boton.dataset.medida);
    var medida = datos.medidas[medidaElegida];
    botones.forEach(function (b) {
      var esta = b === boton;
      b.setAttribute("aria-checked", String(esta));
      b.tabIndex = esta ? 0 : -1;
    });
    document.getElementById("resumen-medida").textContent = medida.resumen;
    document.getElementById("grafica-medidas").setAttribute("aria-label", medida.nombre + " en centímetros por día");

    var url = new URL(window.location.href);
    url.searchParams.set("medida", medida.clave);
    history.replaceState(null, "", url);
    document.querySelectorAll("a[data-rango]").forEach(function (enlace) {
      var destino = new URL(enlace.href);
      destino.searchParams.set("medida", medida.clave);
      enlace.href = destino.pathname + destino.search;
    });

    dibujarUna("grafica-medidas", definiciones());
  }

  botones.forEach(function (boton, i) {
    boton.addEventListener("click", function () {
      elegirMedida(boton);
    });
    // Como un grupo de opciones: las flechas pasan a la medida anterior o siguiente.
    boton.addEventListener("keydown", function (evento) {
      var paso = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[evento.key];
      if (!paso) return;
      evento.preventDefault();
      var otro = botones[(i + paso + botones.length) % botones.length];
      otro.focus();
      elegirMedida(otro);
    });
  });

  dibujar();
  document.addEventListener("rumbo:tema", dibujar);
})();
