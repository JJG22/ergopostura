/* Angulos de RULA a partir de los puntos del cuerpo que detecta MediaPipe Pose.
 *
 * Funciona sobre una fotografia de perfil del lado evaluado. Solo calcula lo que una
 * imagen de perfil permite medir: los cinco angulos. Giros, inclinaciones laterales,
 * abduccion o apoyo no se ven de perfil y los sigue registrando el evaluador.
 *
 * Convenciones, iguales a las del formulario:
 *   brazo   flexion (+) o extension (-) respecto a la linea del tronco
 *   codo    flexion del codo: 0 con el brazo extendido
 *   muneca  desviacion respecto al antebrazo, en valor absoluto
 *   cuello  flexion (+) o extension (-) respecto a la linea del tronco
 *   tronco  flexion (+) respecto a la vertical; negativo es extension
 */
(function (global) {
  "use strict";

  // Indices de MediaPipe Pose. "Izquierdo" es el lado izquierdo de la persona.
  var POINTS = {
    izquierdo: { ear: 7, shoulder: 11, elbow: 13, wrist: 15, index: 19, hip: 23 },
    derecho: { ear: 8, shoulder: 12, elbow: 14, wrist: 16, index: 20, hip: 24 }
  };
  var NOSE = 0;
  var MIN_VISIBILITY = 0.5;
  // Separacion de hombros sobre largo del tronco a partir de la cual la foto no es de perfil.
  var FRONTAL_RATIO = 0.35;

  function vector(from, to) {
    // Las coordenadas de la imagen crecen hacia abajo; aqui y crece hacia arriba.
    return { x: to.x - from.x, y: from.y - to.y };
  }

  /* Angulo con signo, en grados, para girar `a` hasta `b` en sentido antihorario. */
  function counterClockwise(a, b) {
    var cross = a.x * b.y - a.y * b.x;
    var dot = a.x * b.x + a.y * b.y;
    return Math.atan2(cross, dot) * 180 / Math.PI;
  }

  function between(a, b) {
    return Math.abs(counterClockwise(a, b));
  }

  function roundHalf(value) {
    var rounded = Math.round(value * 2) / 2;
    return rounded === 0 ? 0 : rounded; // evita -0
  }

  /**
   * landmarks: puntos normalizados de MediaPipe ({x, y, visibility}).
   * side: "derecho" o "izquierdo", el lado evaluado en la postura.
   * width, height: tamano real de la imagen, para no deformar los angulos.
   * Devuelve {angles, facing, missing}: un angulo es null si sus puntos no se ven bien.
   */
  function compute(landmarks, side, width, height) {
    var ids = POINTS[side] || POINTS.derecho;
    var px = function (index) {
      var point = landmarks[index];
      if (!point) return null;
      return { x: point.x * width, y: point.y * height, visible: (point.visibility == null ? 1 : point.visibility) >= MIN_VISIBILITY };
    };
    var p = {
      ear: px(ids.ear), shoulder: px(ids.shoulder), elbow: px(ids.elbow), wrist: px(ids.wrist),
      index: px(ids.index), hip: px(ids.hip), nose: px(NOSE)
    };
    var ok = function () {
      for (var i = 0; i < arguments.length; i++) {
        var point = p[arguments[i]];
        if (!point || !point.visible) return false;
      }
      return true;
    };

    // Hacia donde mira la persona: la nariz va delante de la oreja.
    var facing = 0;
    if (ok("nose", "ear")) facing = p.nose.x >= p.ear.x ? 1 : -1;
    else if (ok("nose", "shoulder")) facing = p.nose.x >= p.shoulder.x ? 1 : -1;

    var angles = { upper_arm_angle: null, lower_arm_angle: null, wrist_angle: null, neck_angle: null, trunk_angle: null };
    var missing = [];
    var up = { x: 0, y: 1 };

    // De perfil, mirando a la derecha, inclinar el tronco o el cuello hacia delante gira en
    // sentido horario; levantar el brazo hacia delante gira en sentido antihorario.
    if (facing && ok("hip", "shoulder")) {
      var trunkUp = vector(p.hip, p.shoulder);
      angles.trunk_angle = roundHalf(-facing * counterClockwise(up, trunkUp));
      if (ok("ear")) angles.neck_angle = roundHalf(-facing * counterClockwise(trunkUp, vector(p.shoulder, p.ear)));
      if (ok("elbow")) {
        var trunkDown = vector(p.shoulder, p.hip);
        angles.upper_arm_angle = roundHalf(facing * counterClockwise(trunkDown, vector(p.shoulder, p.elbow)));
      }
    }
    if (ok("shoulder", "elbow", "wrist")) {
      angles.lower_arm_angle = roundHalf(between(vector(p.shoulder, p.elbow), vector(p.elbow, p.wrist)));
    }
    if (ok("elbow", "wrist", "index")) {
      angles.wrist_angle = roundHalf(between(vector(p.elbow, p.wrist), vector(p.wrist, p.index)));
    }

    // De perfil los dos hombros casi se superponen; de frente quedan separados.
    var frontal = false;
    var other = landmarks[side === "izquierdo" ? 12 : 11];
    if (other && ok("shoulder", "hip") && (other.visibility == null || other.visibility >= MIN_VISIBILITY)) {
      var shoulderGap = Math.abs(other.x * width - p.shoulder.x);
      var trunkLength = Math.hypot(p.shoulder.x - p.hip.x, p.shoulder.y - p.hip.y);
      frontal = trunkLength > 0 && shoulderGap / trunkLength > FRONTAL_RATIO;
    }

    Object.keys(angles).forEach(function (name) { if (angles[name] === null) missing.push(name); });
    return { angles: angles, facing: facing, frontal: frontal, missing: missing, points: p };
  }

  global.ErgoPoseAngles = { compute: compute, POINTS: POINTS, counterClockwise: counterClockwise };
})(window);
