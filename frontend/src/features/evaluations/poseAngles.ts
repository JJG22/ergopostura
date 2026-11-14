/**
 * Ángulos de RULA a partir de los puntos del cuerpo que detecta MediaPipe Pose.
 * Traducción a TypeScript de static/js/pose-angles.js: mismas convenciones y mismos umbrales.
 *
 * Funciona sobre una fotografía de perfil del lado evaluado. Solo calcula lo que una imagen
 * de perfil permite medir: los cinco ángulos. Giros, inclinaciones laterales, abducción o
 * apoyo no se ven de perfil y los sigue registrando el evaluador.
 *
 *   brazo   flexión (+) o extensión (-) respecto a la línea del tronco
 *   codo    flexión del codo: 0 con el brazo extendido
 *   muñeca  desviación respecto al antebrazo, en valor absoluto
 *   cuello  flexión (+) o extensión (-) respecto a la línea del tronco
 *   tronco  flexión (+) respecto a la vertical; negativo es extensión
 */

export type Side = "derecho" | "izquierdo";
export interface Landmark { x: number; y: number; visibility?: number }
export interface Point { x: number; y: number; visible: boolean }
type PointName = "ear" | "shoulder" | "elbow" | "wrist" | "index" | "hip" | "nose";

export const ANGLE_NAMES = ["upper_arm_angle", "lower_arm_angle", "wrist_angle", "neck_angle", "trunk_angle"] as const;
export type AngleName = (typeof ANGLE_NAMES)[number];

// Índices de MediaPipe Pose. «Izquierdo» es el lado izquierdo de la persona.
const POINTS: Record<Side, Record<Exclude<PointName, "nose">, number>> = {
  izquierdo: { ear: 7, shoulder: 11, elbow: 13, wrist: 15, index: 19, hip: 23 },
  derecho: { ear: 8, shoulder: 12, elbow: 14, wrist: 16, index: 20, hip: 24 },
};
const NOSE = 0;
const MIN_VISIBILITY = 0.5;
// Separación de hombros sobre largo del tronco a partir de la cual la foto no es de perfil.
const FRONTAL_RATIO = 0.35;

interface Vector { x: number; y: number }

// Las coordenadas de la imagen crecen hacia abajo; aquí «y» crece hacia arriba.
const vector = (from: Point, to: Point): Vector => ({ x: to.x - from.x, y: from.y - to.y });

/** Ángulo con signo, en grados, para girar `a` hasta `b` en sentido antihorario. */
export function counterClockwise(a: Vector, b: Vector): number {
  return (Math.atan2(a.x * b.y - a.y * b.x, a.x * b.x + a.y * b.y) * 180) / Math.PI;
}

const between = (a: Vector, b: Vector) => Math.abs(counterClockwise(a, b));

function roundHalf(value: number): number {
  const rounded = Math.round(value * 2) / 2;
  return rounded === 0 ? 0 : rounded; // evita -0
}

export interface PoseResult {
  angles: Record<AngleName, number | null>;
  facing: number;
  frontal: boolean;
  missing: AngleName[];
  points: Partial<Record<PointName, Point | undefined>>;
}

export function computeAngles(landmarks: Landmark[], side: Side, width: number, height: number): PoseResult {
  const ids = POINTS[side];
  const px = (index: number): Point | undefined => {
    const point = landmarks[index];
    if (!point) return undefined;
    return { x: point.x * width, y: point.y * height, visible: (point.visibility ?? 1) >= MIN_VISIBILITY };
  };
  const p: Partial<Record<PointName, Point | undefined>> = {
    ear: px(ids.ear), shoulder: px(ids.shoulder), elbow: px(ids.elbow), wrist: px(ids.wrist),
    index: px(ids.index), hip: px(ids.hip), nose: px(NOSE),
  };
  const ok = (...names: PointName[]) => names.every((name) => p[name]?.visible === true);
  const at = (name: PointName) => p[name] as Point;

  // Hacia dónde mira la persona: la nariz va delante de la oreja.
  let facing = 0;
  if (ok("nose", "ear")) facing = at("nose").x >= at("ear").x ? 1 : -1;
  else if (ok("nose", "shoulder")) facing = at("nose").x >= at("shoulder").x ? 1 : -1;

  const angles: Record<AngleName, number | null> = {
    upper_arm_angle: null, lower_arm_angle: null, wrist_angle: null, neck_angle: null, trunk_angle: null,
  };
  const up = { x: 0, y: 1 };

  // De perfil, mirando a la derecha, inclinar el tronco o el cuello hacia delante gira en
  // sentido horario; levantar el brazo hacia delante gira en sentido antihorario.
  if (facing && ok("hip", "shoulder")) {
    const trunkUp = vector(at("hip"), at("shoulder"));
    angles.trunk_angle = roundHalf(-facing * counterClockwise(up, trunkUp));
    if (ok("ear")) angles.neck_angle = roundHalf(-facing * counterClockwise(trunkUp, vector(at("shoulder"), at("ear"))));
    if (ok("elbow")) {
      angles.upper_arm_angle = roundHalf(facing * counterClockwise(vector(at("shoulder"), at("hip")), vector(at("shoulder"), at("elbow"))));
    }
  }
  if (ok("shoulder", "elbow", "wrist")) {
    angles.lower_arm_angle = roundHalf(between(vector(at("shoulder"), at("elbow")), vector(at("elbow"), at("wrist"))));
  }
  if (ok("elbow", "wrist", "index")) {
    angles.wrist_angle = roundHalf(between(vector(at("elbow"), at("wrist")), vector(at("wrist"), at("index"))));
  }

  // De perfil los dos hombros casi se superponen; de frente quedan separados.
  let frontal = false;
  const other = landmarks[side === "izquierdo" ? 12 : 11];
  if (other && ok("shoulder", "hip") && (other.visibility ?? 1) >= MIN_VISIBILITY) {
    const gap = Math.abs(other.x * width - at("shoulder").x);
    const trunk = Math.hypot(at("shoulder").x - at("hip").x, at("shoulder").y - at("hip").y);
    frontal = trunk > 0 && gap / trunk > FRONTAL_RATIO;
  }

  const missing = ANGLE_NAMES.filter((name) => angles[name] === null);
  return { angles, facing, frontal, missing, points: p };
}

export const SKELETON: readonly [PointName, PointName][] = [
  ["ear", "shoulder"], ["shoulder", "hip"], ["shoulder", "elbow"], ["elbow", "wrist"], ["wrist", "index"],
];
