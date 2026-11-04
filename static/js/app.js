(function () {
  "use strict";

  var modalRoot = function () { return document.getElementById("modal-root"); };

  function closeModal() {
    var root = modalRoot();
    if (root) root.innerHTML = "";
  }

  document.addEventListener("click", function (event) {
    var closer = event.target.closest("[data-modal-close]");
    if (closer && closer.closest("#modal-root")) {
      event.preventDefault();
      closeModal();
      return;
    }

    if (event.target.classList && event.target.classList.contains("overlay")) {
      closeModal();
      return;
    }

    if (event.target.closest("[data-toast-close]")) {
      event.target.closest(".toast").remove();
      return;
    }

    var sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;
    if (event.target.closest("[data-sidebar-toggle]")) {
      sidebar.classList.toggle("sidebar-open");
    } else if (!event.target.closest(".sidebar")) {
      sidebar.classList.remove("sidebar-open");
    }
  });

  document.addEventListener("submit", function (event) {
    var message = event.target.getAttribute && event.target.getAttribute("data-confirm");
    if (message && !window.confirm(message)) event.preventDefault();
  });

  document.addEventListener("change", function (event) {
    var url = event.target.getAttribute && event.target.getAttribute("data-photo-preview");
    var preview = document.getElementById("assessment-photo");
    if (url && preview) preview.src = url;
  });

  var focusId = new URLSearchParams(window.location.search).get("foco");
  var focusTarget = focusId && document.getElementById(focusId);
  if (focusTarget) focusTarget.scrollIntoView();

  var checkedPhoto = document.querySelector("[data-photo-preview]:checked");
  var photoPreview = document.getElementById("assessment-photo");
  if (checkedPhoto && photoPreview) photoPreview.src = checkedPhoto.getAttribute("data-photo-preview");

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeModal();
  });

  document.body.addEventListener("htmx:afterSwap", function (event) {
    if (event.target.id !== "modal-root") return;
    var field = event.target.querySelector(".has-error input, .has-error select, input:not([type=hidden]), select, textarea");
    if (field) field.focus();
  });

  document.querySelectorAll(".toast").forEach(function (toast) {
    setTimeout(function () { toast.remove(); }, 4000);
  });
})();
