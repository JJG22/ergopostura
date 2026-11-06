/* Sugerencia de angulos con IA en la pantalla de analisis RULA.
 *
 * La deteccion corre en el navegador con MediaPipe Pose: la fotografia no se envia a
 * ningun servicio. La libreria y el modelo se descargan solo al pulsar el boton, con la
 * version fija. Los valores sugeridos llenan el formulario y el evaluador los revisa;
 * nada se guarda hasta que el pulsa «Calcular y guardar».
 */
(function () {
  "use strict";

  var root = document.querySelector("[data-pose-assist]");
  if (!root) return;

  var VERSION = "0.10.14";
  var CDN = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@" + VERSION;
  var MODEL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";
  var LABELS = {
    upper_arm_angle: "Brazo",
    lower_arm_angle: "Antebrazo",
    wrist_angle: "Muñeca",
    neck_angle: "Cuello",
    trunk_angle: "Tronco"
  };
  var SEGMENTS = [["ear", "shoulder"], ["shoulder", "hip"], ["shoulder", "elbow"], ["elbow", "wrist"], ["wrist", "index"]];

  var button = root.querySelector("[data-pose-run]");
  var status = root.querySelector("[data-pose-status]");
  var output = root.querySelector("[data-pose-result]");
  var hidden = document.querySelector("input[name=ai_suggestion]");
  var image = document.getElementById("assessment-photo");
  var canvas = document.getElementById("pose-overlay");
  var side = root.getAttribute("data-side");
  var landmarkerPromise = null;

  function say(text, kind) {
    status.textContent = text;
    status.className = "pose-status" + (kind ? " pose-status-" + kind : "");
  }

  function loadLandmarker() {
    if (!landmarkerPromise) {
      landmarkerPromise = import(CDN + "/vision_bundle.mjs").then(function (vision) {
        return vision.FilesetResolver.forVisionTasks(CDN + "/wasm").then(function (fileset) {
          return vision.PoseLandmarker.createFromOptions(fileset, {
            baseOptions: { modelAssetPath: MODEL, delegate: "CPU" },
            runningMode: "IMAGE",
            numPoses: 1
          });
        });
      });
      landmarkerPromise.catch(function () { landmarkerPromise = null; });
    }
    return landmarkerPromise;
  }

  function imageReady() {
    if (image.complete && image.naturalWidth) return Promise.resolve();
    return new Promise(function (resolve, reject) {
      image.addEventListener("load", resolve, { once: true });
      image.addEventListener("error", reject, { once: true });
    });
  }

  function selectedPhotoId() {
    var checked = document.querySelector("input[name=photo]:checked");
    return checked ? Number(checked.value) : null;
  }

  /* Rectangulo donde se ve la imagen dentro de su caja (object-fit: contain). */
  function contentBox() {
    var box = image.getBoundingClientRect();
    var scale = Math.min(box.width / image.naturalWidth, box.height / image.naturalHeight);
    var width = image.naturalWidth * scale;
    var height = image.naturalHeight * scale;
    return { left: (box.width - width) / 2, top: (box.height - height) / 2, width: width, height: height, outer: box };
  }

  function drawSkeleton(points) {
    var box = contentBox();
    var ratio = window.devicePixelRatio || 1;
    canvas.width = box.outer.width * ratio;
    canvas.height = box.outer.height * ratio;
    canvas.style.width = box.outer.width + "px";
    canvas.style.height = box.outer.height + "px";
    var context = canvas.getContext("2d");
    context.scale(ratio, ratio);
    var place = function (point) {
      return {
        x: box.left + point.x / image.naturalWidth * box.width,
        y: box.top + point.y / image.naturalHeight * box.height
      };
    };
    context.lineWidth = 3;
    context.lineCap = "round";
    SEGMENTS.forEach(function (pair) {
      var a = points[pair[0]], b = points[pair[1]];
      if (!a || !b || !a.visible || !b.visible) return;
      var from = place(a), to = place(b);
      context.strokeStyle = "#2dd4bf";
      context.beginPath();
      context.moveTo(from.x, from.y);
      context.lineTo(to.x, to.y);
      context.stroke();
    });
    Object.keys(points).forEach(function (name) {
      var point = points[name];
      if (!point || !point.visible || name === "nose") return;
      var at = place(point);
      context.fillStyle = "#f0fdfa";
      context.strokeStyle = "#0f766e";
      context.beginPath();
      context.arc(at.x, at.y, 5, 0, Math.PI * 2);
      context.fill();
      context.stroke();
    });
    canvas.hidden = false;
  }

  function clearSkeleton() {
    canvas.hidden = true;
  }

  function fill(angles) {
    var list = [];
    Object.keys(LABELS).forEach(function (name) {
      var input = document.getElementById("id_" + name);
      var value = angles[name];
      var field = input && input.closest(".field");
      if (!input) return;
      if (value === null) {
        list.push("<li><span>" + LABELS[name] + "</span><em>No se detectó; mídelo a mano</em></li>");
        return;
      }
      input.value = value;
      if (field) field.classList.add("is-ai-suggested");
      list.push("<li><span>" + LABELS[name] + "</span><strong>" + String(value).replace(".", ",") + "°</strong></li>");
    });
    output.innerHTML = "<ul>" + list.join("") + "</ul>";
  }

  // Si el evaluador cambia un valor sugerido, el campo deja de marcarse como sugerido.
  document.addEventListener("input", function (event) {
    var field = event.target.closest && event.target.closest(".is-ai-suggested");
    if (field) field.classList.remove("is-ai-suggested");
  });

  // Otra fotografia invalida la sugerencia dibujada.
  document.addEventListener("change", function (event) {
    if (event.target.name === "photo") {
      clearSkeleton();
      say("Elegiste otra fotografía. Vuelve a pedir la sugerencia si la necesitas.");
    }
  });

  button.addEventListener("click", function () {
    button.disabled = true;
    clearSkeleton();
    say("Cargando el modelo de detección. La primera vez puede tardar unos segundos…", "busy");
    Promise.all([loadLandmarker(), imageReady()])
      .then(function (results) {
        say("Analizando la fotografía…", "busy");
        var detection = results[0].detect(image);
        if (!detection.landmarks || !detection.landmarks.length) {
          say("No se detectó a una persona en la fotografía. Registra los ángulos a mano.", "error");
          return;
        }
        var result = window.ErgoPoseAngles.compute(detection.landmarks[0], side, image.naturalWidth, image.naturalHeight);
        if (!result.facing) {
          say("No se pudo saber hacia dónde mira la persona. Usa una foto de perfil o mide a mano.", "error");
          return;
        }
        drawSkeleton(result.points);
        fill(result.angles);
        hidden.value = JSON.stringify({ photo: selectedPhotoId(), side: side, model: "mediapipe-pose-lite@" + VERSION, frontal: result.frontal, angles: result.angles });
        var found = 5 - result.missing.length;
        if (result.frontal) {
          say("Sugerencia lista, pero la foto parece tomada de frente: los ángulos de perfil pueden no ser fiables. Mídelos a mano o usa una foto de perfil.", "error");
        } else {
          say("Sugerencia lista: " + found + " de 5 ángulos. Revísalos sobre la fotografía antes de guardar.", "ok");
        }
      })
      .catch(function (error) {
        if (window.console) console.error("Sugerencia de ángulos:", error);
        say("No se pudo cargar el modelo. Revisa la conexión a internet o registra los ángulos a mano.", "error");
      })
      .then(function () { button.disabled = false; });
  });
})();
