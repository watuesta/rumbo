// Cambia entre modo claro y oscuro y recuerda la elección en este dispositivo.
// El tema guardado se aplica antes de pintar con el script en línea de base.html.
(function () {
  var raiz = document.documentElement;
  var boton = document.querySelector("[data-cambiar-tema]");

  function temaActual() {
    return raiz.dataset.theme || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  }

  function actualizar() {
    var tema = temaActual();
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = getComputedStyle(raiz).getPropertyValue("--fondo").trim();
    if (boton) boton.setAttribute("aria-label", tema === "light" ? "Usar modo oscuro" : "Usar modo claro");
    document.dispatchEvent(new CustomEvent("rumbo:tema"));
  }

  if (boton) {
    boton.addEventListener("click", function () {
      var nuevo = temaActual() === "light" ? "dark" : "light";
      raiz.dataset.theme = nuevo;
      try {
        localStorage.setItem("rumbo-tema", nuevo);
      } catch (e) {}
      actualizar();
    });
  }

  matchMedia("(prefers-color-scheme: light)").addEventListener("change", actualizar);
  actualizar();
})();
