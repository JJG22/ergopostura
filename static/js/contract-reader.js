/* Lectura del contrato con IA en el formulario.
 *
 * Envia el PDF elegido al servidor, que lo lee con Claude y devuelve los datos. Los
 * valores llenan los campos y quedan marcados como sugeridos hasta que el ingeniero los
 * cambie. Nada se guarda hasta que el pulsa «Guardar».
 */
(function () {
  "use strict";

  var form = document.querySelector("[data-contract-form]");
  if (!form) return;

  var panel = form.querySelector("[data-ai-panel]");
  var button = form.querySelector("[data-ai-read]");
  var status = form.querySelector("[data-ai-status]");
  var result = form.querySelector("[data-ai-result]");
  var fileInput = form.querySelector("input[type=file][name=document]");
  if (!panel || !button || !fileInput) return;

  function say(text, kind) {
    status.textContent = text;
    status.className = "ai-status" + (kind ? " ai-status-" + kind : "");
  }

  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  function setField(name, value) {
    if (value === null || value === undefined || value === "") return false;
    var input = form.elements[name];
    if (!input) return false;
    input.value = value;
    var field = input.closest(".field");
    if (field) field.classList.add("is-ai-suggested");
    return true;
  }

  fileInput.addEventListener("change", function () {
    button.disabled = !fileInput.files.length;
    result.hidden = true;
    say(fileInput.files.length ? "Listo para leer «" + fileInput.files[0].name + "»." : "");
  });

  form.addEventListener("input", function (event) {
    var field = event.target.closest && event.target.closest(".is-ai-suggested");
    if (field) field.classList.remove("is-ai-suggested");
  });

  button.addEventListener("click", function () {
    if (!fileInput.files.length) return;
    var data = new FormData();
    data.append("document", fileInput.files[0]);
    data.append("csrfmiddlewaretoken", form.elements.csrfmiddlewaretoken.value);

    button.disabled = true;
    result.hidden = true;
    say("Leyendo el contrato. Puede tardar entre 10 y 40 segundos…", "busy");

    fetch(form.getAttribute("data-read-url"), { method: "POST", body: data, credentials: "same-origin" })
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (body) {
          if (!response.ok) throw new Error(body.error || "No se pudo leer el contrato. Intenta de nuevo.");
          return body;
        });
      })
      .then(function (body) {
        var filled = 0;
        Object.keys(body.fields || {}).forEach(function (name) {
          if (setField(name, body.fields[name])) filled += 1;
        });

        var html = "";
        if (body.summary) html += "<p>" + escapeHtml(body.summary) + "</p>";
        if (body.client_nit && !body.company_found) {
          html += '<p class="ai-warning">El NIT del documento (' + escapeHtml(body.client_nit) + ") no corresponde a ninguna empresa registrada. Regístrala antes de guardar el contrato.</p>";
        } else if (!body.fields.company && body.client) {
          html += '<p class="ai-warning">No se identificó la empresa «' + escapeHtml(body.client) + "». Elígela en la lista.</p>";
        }
        if (body.alerts && body.alerts.length) {
          html += "<strong>Para revisar</strong><ul>" + body.alerts.map(function (alert) {
            return "<li>" + escapeHtml(alert) + "</li>";
          }).join("") + "</ul>";
        }
        result.innerHTML = html;
        result.hidden = !html;
        say("Se llenaron " + filled + " campos. Revísalos antes de guardar.", "ok");
      })
      .catch(function (error) {
        say(error.message, "error");
      })
      .then(function () { button.disabled = !fileInput.files.length; });
  });
})();
