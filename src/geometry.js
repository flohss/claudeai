// ---------------------------------------------------------------------
// Géométrie pure — aucune dépendance React. Toutes les coordonnées sont
// exprimées dans l'espace "monde" (indépendant du zoom/pan de la vue).
// ---------------------------------------------------------------------

export function dist(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

export function getBBox(points) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of points) {
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.y > maxY) maxY = p.y;
  }
  return { minX, minY, maxX, maxY, w: maxX - minX, h: maxY - minY, cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 };
}

export function bboxFromPoints(a, b) {
  const minX = Math.min(a.x, b.x), maxX = Math.max(a.x, b.x);
  const minY = Math.min(a.y, b.y), maxY = Math.max(a.y, b.y);
  return { minX, minY, maxX, maxY, w: maxX - minX, h: maxY - minY, cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 };
}

export function bboxesIntersect(a, b) {
  return a.minX <= b.maxX && a.maxX >= b.minX && a.minY <= b.maxY && a.maxY >= b.minY;
}

export function unionBBox(boxes) {
  if (boxes.length === 0) return null;
  const minX = Math.min(...boxes.map((b) => b.minX));
  const minY = Math.min(...boxes.map((b) => b.minY));
  const maxX = Math.max(...boxes.map((b) => b.maxX));
  const maxY = Math.max(...boxes.map((b) => b.maxY));
  return { minX, minY, maxX, maxY, w: maxX - minX, h: maxY - minY, cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 };
}

function perpDist(p, a, b) {
  const num = Math.abs((b.y - a.y) * p.x - (b.x - a.x) * p.y + b.x * a.y - b.y * a.x);
  const den = Math.hypot(b.y - a.y, b.x - a.x) || 1e-6;
  return num / den;
}

// Simplification de Ramer-Douglas-Peucker : réduit un tracé bruité à ses
// points de rupture significatifs.
function rdp(points, epsilon) {
  if (points.length < 3) return points.slice();
  let dmax = 0, index = 0;
  const end = points.length - 1;
  for (let i = 1; i < end; i++) {
    const d = perpDist(points[i], points[0], points[end]);
    if (d > dmax) { dmax = d; index = i; }
  }
  if (dmax > epsilon) {
    const left = rdp(points.slice(0, index + 1), epsilon);
    const right = rdp(points.slice(index), epsilon);
    return left.slice(0, -1).concat(right);
  }
  return [points[0], points[end]];
}

function pathLength(points) {
  let len = 0;
  for (let i = 1; i < points.length; i++) len += dist(points[i - 1], points[i]);
  return len;
}

function dedupeClose(points, minDist) {
  const out = [points[0]];
  for (let i = 1; i < points.length; i++) {
    if (dist(points[i], out[out.length - 1]) > minDist) out.push(points[i]);
  }
  return out;
}

function angleAt(p0, p1, p2) {
  const v1 = { x: p0.x - p1.x, y: p0.y - p1.y };
  const v2 = { x: p2.x - p1.x, y: p2.y - p1.y };
  const m1 = Math.hypot(v1.x, v1.y), m2 = Math.hypot(v2.x, v2.y);
  if (m1 < 1e-6 || m2 < 1e-6) return 180;
  let cos = (v1.x * v2.x + v1.y * v2.y) / (m1 * m2);
  cos = Math.max(-1, Math.min(1, cos));
  return (Math.acos(cos) * 180) / Math.PI;
}

// ---------------------------------------------------------------------
// Classifieur de formes (heuristique — voir CLAUDE.md / commentaires App.jsx)
// ---------------------------------------------------------------------

// Sommets d'un polygone fermé, dans l'ordre du tracé (utilisé pour dédupliquer
// le point de fermeture après simplification RDP).
function closedCorners(rawPoints, epsilon, mergeDist) {
  let simplified = rdp(rawPoints, epsilon);
  simplified = dedupeClose(simplified, mergeDist);
  if (simplified.length > 1 && dist(simplified[0], simplified[simplified.length - 1]) < mergeDist * 1.3) {
    simplified = simplified.slice(0, -1);
  }
  return simplified;
}

// Vérifie que les sommets tournent tous dans le même sens (polygone convexe),
// avec une tolérance pour le bruit du tracé à main levée.
function isConvex(points) {
  const n = points.length;
  let sign = 0;
  for (let i = 0; i < n; i++) {
    const a = points[i], b = points[(i + 1) % n], c = points[(i + 2) % n];
    const cross = (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x);
    if (Math.abs(cross) < 1e-3) continue;
    const s = cross > 0 ? 1 : -1;
    if (sign === 0) sign = s;
    else if (s !== sign) return false;
  }
  return true;
}

const POLYGON_NAMES = { 5: 'un pentagone', 6: 'un hexagone', 7: 'un heptagone', 8: 'un octogone' };

export function classifyShape(rawPoints) {
  if (rawPoints.length < 5) return null;
  const bbox = getBBox(rawPoints);
  const diag = Math.hypot(bbox.w, bbox.h);
  if (diag < 20) return null; // trop petit, probablement un point

  const first = rawPoints[0];
  const last = rawPoints[rawPoints.length - 1];
  const closed = dist(first, last) < Math.max(20, diag * 0.18);
  const length = pathLength(rawPoints);

  if (!closed) {
    const maxDev = Math.max(...rawPoints.map((p) => perpDist(p, first, last)));
    if (maxDev < Math.max(6, diag * 0.06) && length > 25) {
      return { type: 'line', points: [first, last], label: 'un trait droit' };
    }
    return null;
  }

  const { cx, cy } = bbox;

  // 1. Circularité : variance des rayons autour du centre de la bbox
  const radii = rawPoints.map((p) => Math.hypot(p.x - cx, p.y - cy));
  const meanR = radii.reduce((a, b) => a + b, 0) / radii.length;
  const variance = radii.reduce((a, r) => a + (r - meanR) ** 2, 0) / radii.length;
  const stdR = Math.sqrt(variance);
  if (meanR > 0 && stdR / meanR < 0.22) {
    const aspect = bbox.w / (bbox.h || 1);
    const isCircle = aspect <= 1.35 && aspect >= 0.74;
    return { type: 'ellipse', bbox, label: isCircle ? 'un cercle' : 'une ellipse' };
  }

  // 2. Étoile : sommets alternant pointes (loin du centre) et creux (près du
  // centre). On utilise un epsilon plus fin pour capter les petites entailles.
  if (diag > 40) {
    const starEpsilon = Math.max(6, diag * 0.025);
    const starMerge = Math.max(8, diag * 0.035);
    const starCorners = closedCorners(rawPoints, starEpsilon, starMerge);
    if (starCorners.length >= 8 && starCorners.length <= 14 && starCorners.length % 2 === 0) {
      const rs = starCorners.map((p) => Math.hypot(p.x - cx, p.y - cy));
      const groupA = rs.filter((_, i) => i % 2 === 0);
      const groupB = rs.filter((_, i) => i % 2 === 1);
      const avg = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length;
      const std = (arr, m) => Math.sqrt(arr.reduce((a, r) => a + (r - m) ** 2, 0) / arr.length);
      const avgA = avg(groupA), avgB = avg(groupB);
      const outer = avgA >= avgB ? groupA : groupB;
      const inner = avgA >= avgB ? groupB : groupA;
      const outerAvg = avg(outer), innerAvg = avg(inner);
      const spiky = outerAvg > 0 && innerAvg / outerAvg < 0.75;
      const consistent = std(outer, outerAvg) / outerAvg < 0.3 && std(inner, innerAvg) / (innerAvg || 1) < 0.35;
      if (spiky && consistent) {
        return { type: 'polygon', points: starCorners, label: 'une étoile' };
      }
    }
  }

  // 3. Polygones (triangle, carré/rectangle/losange, pentagone à octogone),
  // à partir des sommets détectés — on garde les points réels, pas de forme
  // idéalisée, pour respecter l'orientation et les proportions du tracé.
  const epsilon = Math.max(8, diag * 0.045);
  const merge = Math.max(10, diag * 0.06);
  const corners = closedCorners(rawPoints, epsilon, merge);
  const n = corners.length;

  if (n === 3) {
    return { type: 'polygon', points: corners, label: 'un triangle' };
  }
  if (n === 4) {
    const sides = [0, 1, 2, 3].map((i) => dist(corners[i], corners[(i + 1) % 4]));
    const angles = [0, 1, 2, 3].map((i) => angleAt(corners[(i + 3) % 4], corners[i], corners[(i + 1) % 4]));
    const rightAngled = angles.every((a) => Math.abs(a - 90) < 28);
    const equalSides = Math.max(...sides) / Math.min(...sides) < 1.3;
    let label = 'un quadrilatère';
    if (rightAngled && equalSides) label = 'un carré';
    else if (rightAngled) label = 'un rectangle';
    else if (equalSides) label = 'un losange';
    return { type: 'polygon', points: corners, label };
  }
  if (n >= 5 && n <= 8 && isConvex(corners)) {
    return { type: 'polygon', points: corners, label: POLYGON_NAMES[n] };
  }
  return null;
}

// ---------------------------------------------------------------------
// Rendu — géométrie partagée par les composants SVG
// ---------------------------------------------------------------------

export function smoothPathD(points) {
  if (points.length < 2) return '';
  if (points.length === 2) {
    return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`;
  }
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length - 1; i++) {
    const midX = (points[i].x + points[i + 1].x) / 2;
    const midY = (points[i].y + points[i + 1].y) / 2;
    d += ` Q ${points[i].x} ${points[i].y} ${midX} ${midY}`;
  }
  const p = points[points.length - 1];
  d += ` L ${p.x} ${p.y}`;
  return d;
}

const BBOX_SHAPE_TYPES = new Set(['ellipse', 'rect']);

// bbox englobante d'un tracé, qu'il soit resté à main levée ou converti en forme nette.
export function strokeBBox(stroke) {
  if (stroke.shape) {
    return BBOX_SHAPE_TYPES.has(stroke.shape.type) ? stroke.shape.bbox : getBBox(stroke.shape.points);
  }
  return getBBox(stroke.points);
}

// Sommets éditables d'une forme : les 4 coins de la bbox pour une forme basée
// bbox (ellipse, rectangle), les points réels sinon (ligne, flèche, polygone).
export function shapeHandlePoints(shape) {
  if (BBOX_SHAPE_TYPES.has(shape.type)) {
    const { minX, minY, maxX, maxY } = shape.bbox;
    return [
      { x: minX, y: minY },
      { x: maxX, y: minY },
      { x: maxX, y: maxY },
      { x: minX, y: maxY },
    ];
  }
  return shape.points;
}

export function updateShapeHandle(shape, index, pos) {
  if (BBOX_SHAPE_TYPES.has(shape.type)) {
    const corners = shapeHandlePoints(shape);
    const opposite = corners[(index + 2) % 4];
    const minX = Math.min(opposite.x, pos.x), maxX = Math.max(opposite.x, pos.x);
    const minY = Math.min(opposite.y, pos.y), maxY = Math.max(opposite.y, pos.y);
    return { ...shape, bbox: { minX, minY, maxX, maxY, w: maxX - minX, h: maxY - minY, cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 } };
  }
  const points = shape.points.map((p, i) => (i === index ? pos : p));
  return { ...shape, points };
}

export function translateShape(shape, dx, dy) {
  if (BBOX_SHAPE_TYPES.has(shape.type)) {
    const b = shape.bbox;
    const minX = b.minX + dx, maxX = b.maxX + dx, minY = b.minY + dy, maxY = b.maxY + dy;
    return { ...shape, bbox: { minX, minY, maxX, maxY, w: b.w, h: b.h, cx: b.cx + dx, cy: b.cy + dy } };
  }
  return { ...shape, points: shape.points.map((p) => ({ x: p.x + dx, y: p.y + dy })) };
}

export function translateStroke(stroke, dx, dy) {
  return {
    ...stroke,
    points: stroke.points.map((p) => ({ x: p.x + dx, y: p.y + dy })),
    shape: stroke.shape ? translateShape(stroke.shape, dx, dy) : null,
  };
}

// Pointe de flèche : triangle plein à l'extrémité p1, orienté selon p0->p1.
export function arrowHeadPoints(p0, p1, size) {
  const angle = Math.atan2(p1.y - p0.y, p1.x - p0.x);
  const spread = Math.PI / 7;
  return [
    p1,
    { x: p1.x - size * Math.cos(angle - spread), y: p1.y - size * Math.sin(angle - spread) },
    { x: p1.x - size * Math.cos(angle + spread), y: p1.y - size * Math.sin(angle + spread) },
  ];
}

// Construit l'objet "shape" d'un outil de tracé direct (ligne, flèche,
// rectangle, ellipse) à partir des points de début/fin du glisser.
export function shapeFromDrag(tool, start, end) {
  if (tool === 'line' || tool === 'arrow') {
    return { type: tool, points: [start, end] };
  }
  const bbox = bboxFromPoints(start, end);
  if (tool === 'rect') return { type: 'rect', bbox };
  if (tool === 'ellipse') return { type: 'ellipse', bbox, label: 'une ellipse' };
  return null;
}
