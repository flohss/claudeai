import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Undo2, Redo2, Trash2, Check, X, Sparkles, PenLine } from 'lucide-react';

/**
 * ATELIER — assistant de dessin avec correction de traits (façon Autodraw)
 * ------------------------------------------------------------------------
 * Quand l'utilisateur termine un trait fermé ou une ligne, un classifieur
 * géométrique heuristique essaie de reconnaître une forme simple (ligne,
 * rectangle, triangle, cercle/ellipse). Si une forme est reconnue, une
 * suggestion apparaît : l'utilisateur peut la valider (le trait à main
 * levée est remplacé par une version nette) ou l'ignorer (le trait reste
 * tel quel, légèrement lissé).
 *
 * Points d'extension prévus :
 * 1. classifyShape() — remplacer/compléter l'heuristique géométrique par
 *    un vrai modèle (appel à une API de classification, ou un modèle
 *    entraîné sur des contours) pour reconnaître plus de formes (flèches,
 *    étoiles, icônes) comme le fait Autodraw avec sa bibliothèque de dessins.
 * 2. renderStroke() — passer à un rendu vectoriel (SVG) pour permettre
 *    l'édition après-coup (déplacer un sommet, redimensionner une forme).
 * 3. Persistance — sérialiser `strokes` (déjà un JSON simple) vers un
 *    stockage pour reprendre un dessin plus tard.
 * 4. Bibliothèque de formes — au lieu de formes géométriques pures,
 *    associer le contour détecté à des icônes prédessinées.
 */

// ---------------------------------------------------------------------
// Géométrie
// ---------------------------------------------------------------------

function dist(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function getBBox(points) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of points) {
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.y > maxY) maxY = p.y;
  }
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
// Classifieur de formes (heuristique v1 — voir point d'extension n°1)
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

function classifyShape(rawPoints) {
  if (rawPoints.length < 5) return null;
  const bbox = getBBox(rawPoints);
  const diag = Math.hypot(bbox.w, bbox.h);
  if (diag < 20) return null; // trop petit, probablement un point

  const first = rawPoints[0];
  const last = rawPoints[rawPoints.length - 1];
  const closed = dist(first, last) < Math.max(20, diag * 0.18);
  const length = pathLength(rawPoints);

  if (!closed) {
    // Point d'extension : reconnaître une flèche (trait + chevron) ici.
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
// Rendu
// ---------------------------------------------------------------------

function drawSmoothPath(ctx, points) {
  if (points.length < 2) return;
  if (points.length < 3) {
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    ctx.lineTo(points[1].x, points[1].y);
    ctx.stroke();
    return;
  }
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length - 1; i++) {
    const midX = (points[i].x + points[i + 1].x) / 2;
    const midY = (points[i].y + points[i + 1].y) / 2;
    ctx.quadraticCurveTo(points[i].x, points[i].y, midX, midY);
  }
  const p = points[points.length - 1];
  ctx.lineTo(p.x, p.y);
  ctx.stroke();
}

function renderStroke(ctx, stroke) {
  ctx.strokeStyle = stroke.color;
  ctx.lineWidth = stroke.width;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  if (stroke.type === 'corrected' && stroke.shape) {
    const s = stroke.shape;
    ctx.beginPath();
    if (s.type === 'line') {
      ctx.moveTo(s.points[0].x, s.points[0].y);
      ctx.lineTo(s.points[1].x, s.points[1].y);
    } else if (s.type === 'ellipse') {
      ctx.ellipse(s.bbox.cx, s.bbox.cy, Math.max(s.bbox.w / 2, 1), Math.max(s.bbox.h / 2, 1), 0, 0, Math.PI * 2);
    } else if (s.type === 'polygon') {
      ctx.moveTo(s.points[0].x, s.points[0].y);
      for (let i = 1; i < s.points.length; i++) ctx.lineTo(s.points[i].x, s.points[i].y);
      ctx.closePath();
    }
    ctx.stroke();
    return;
  }
  drawSmoothPath(ctx, stroke.points);
}

function drawPaper(ctx, w, h) {
  ctx.save();
  ctx.strokeStyle = '#E4DCC8';
  ctx.lineWidth = 1;
  for (let y = 34; y < h; y += 32) {
    ctx.beginPath();
    ctx.moveTo(0, y + 0.5);
    ctx.lineTo(w, y + 0.5);
    ctx.stroke();
  }
  ctx.strokeStyle = '#D8B9A8';
  ctx.beginPath();
  ctx.moveTo(46.5, 0);
  ctx.lineTo(46.5, h);
  ctx.stroke();
  ctx.restore();
}

// ---------------------------------------------------------------------
// Palette / constantes UI
// ---------------------------------------------------------------------

const COLORS = [
  { name: 'Graphite', hex: '#2A2620' },
  { name: 'Rouille', hex: '#A6432E' },
  { name: 'Sarcelle', hex: '#1F6F63' },
  { name: 'Indigo', hex: '#2C3E66' },
  { name: 'Mousse', hex: '#4B6A45' },
];
const WIDTHS = [
  { label: 'Fin', value: 2.5 },
  { label: 'Moyen', value: 5 },
  { label: 'Épais', value: 9 },
];
export default function DrawingAssistant() {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const strokesRef = useRef([]);
  const currentPointsRef = useRef([]);
  const isDrawingRef = useRef(false);
  const dismissTimerRef = useRef(null);

  const [strokes, setStrokes] = useState([]);
  const [redoStack, setRedoStack] = useState([]);
  const [color, setColor] = useState(COLORS[0].hex);
  const [width, setWidth] = useState(WIDTHS[1].value);
  const [autoCorrect, setAutoCorrect] = useState(true);
  const [pendingSuggestion, setPendingSuggestion] = useState(null);
  const [containerSize, setContainerSize] = useState({ w: 800, h: 500 });

  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, rect.width, rect.height);
    drawPaper(ctx, rect.width, rect.height);
    strokesRef.current.forEach((s) => renderStroke(ctx, s));
    if (isDrawingRef.current && currentPointsRef.current.length > 1) {
      renderStroke(ctx, { color, width, type: 'freehand', points: currentPointsRef.current });
    }
  }, [color, width]);

  useEffect(() => {
    strokesRef.current = strokes;
    redraw();
  }, [strokes, redraw]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    function resize() {
      const rect = container.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + 'px';
      canvas.style.height = rect.height + 'px';
      const ctx = canvas.getContext('2d');
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      setContainerSize({ w: rect.width, h: rect.height });
      redraw();
    }
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(container);
    return () => ro.disconnect();
  }, [redraw]);

  function getPos(e) {
    const rect = canvasRef.current.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function clearPendingSuggestion() {
    if (dismissTimerRef.current) {
      clearTimeout(dismissTimerRef.current);
      dismissTimerRef.current = null;
    }
    setPendingSuggestion(null);
  }

  function handlePointerDown(e) {
    e.preventDefault();
    canvasRef.current.setPointerCapture(e.pointerId);
    clearPendingSuggestion();
    isDrawingRef.current = true;
    currentPointsRef.current = [getPos(e)];
    redraw();
  }
  function handlePointerMove(e) {
    if (!isDrawingRef.current) return;
    currentPointsRef.current.push(getPos(e));
    redraw();
  }
  function handlePointerUp() {
    if (!isDrawingRef.current) return;
    isDrawingRef.current = false;
    const points = currentPointsRef.current;
    currentPointsRef.current = [];
    if (points.length < 2) { redraw(); return; }

    const stroke = {
      id: Date.now() + Math.random().toString(36).slice(2),
      color, width, type: 'freehand', shape: null, points,
    };
    setStrokes((prev) => [...prev, stroke]);
    setRedoStack([]);

    if (autoCorrect) {
      const shape = classifyShape(points);
      if (shape) {
        const bbox = getBBox(points);
        setPendingSuggestion({ strokeId: stroke.id, shape, anchor: { x: bbox.maxX, y: bbox.minY } });
      }
    }
  }

  useEffect(() => {
    if (!pendingSuggestion) return;
    dismissTimerRef.current = setTimeout(() => setPendingSuggestion(null), 4500);
    return () => clearTimeout(dismissTimerRef.current);
  }, [pendingSuggestion]);

  function acceptSuggestion() {
    if (!pendingSuggestion) return;
    setStrokes((prev) =>
      prev.map((s) => (s.id === pendingSuggestion.strokeId ? { ...s, type: 'corrected', shape: pendingSuggestion.shape } : s))
    );
    clearPendingSuggestion();
  }

  function undo() {
    if (strokesRef.current.length === 0) return;
    clearPendingSuggestion();
    const last = strokesRef.current[strokesRef.current.length - 1];
    setStrokes((prev) => prev.slice(0, -1));
    setRedoStack((prev) => [...prev, last]);
  }
  function redo() {
    if (redoStack.length === 0) return;
    clearPendingSuggestion();
    const item = redoStack[redoStack.length - 1];
    setRedoStack((prev) => prev.slice(0, -1));
    setStrokes((prev) => [...prev, item]);
  }
  function clearAll() {
    clearPendingSuggestion();
    setStrokes([]);
    setRedoStack([]);
  }

  const popupLeft = pendingSuggestion ? Math.min(pendingSuggestion.anchor.x + 14, containerSize.w - 200) : 0;
  const popupTop = pendingSuggestion ? Math.max(pendingSuggestion.anchor.y - 56, 8) : 0;

  return (
    <div className="w-full h-screen flex flex-col" style={{ background: '#F3EFE6', color: '#2A2620', fontFamily: 'ui-sans-serif, system-ui, sans-serif' }}>
      {/* Barre d'outils */}
      <div className="flex flex-wrap items-center gap-4 px-4 py-3 border-b" style={{ borderColor: '#E3DCC9', background: '#FBF9F3' }}>
        <div className="flex items-center gap-2 pr-3 mr-1 border-r" style={{ borderColor: '#E3DCC9' }}>
          <PenLine size={18} style={{ color: '#A6432E' }} />
          <span className="text-sm font-semibold tracking-wide" style={{ fontFamily: 'ui-serif, Georgia, serif' }}>Atelier</span>
        </div>

        <div className="flex items-center gap-1.5">
          {COLORS.map((c) => (
            <button
              key={c.hex}
              onClick={() => setColor(c.hex)}
              title={c.name}
              className="w-6 h-6 rounded-full transition-transform"
              style={{
                background: c.hex,
                transform: color === c.hex ? 'scale(1.15)' : 'scale(1)',
                boxShadow: color === c.hex ? `0 0 0 2px #FBF9F3, 0 0 0 4px ${c.hex}` : 'none',
              }}
            />
          ))}
        </div>

        <div className="flex items-center gap-1 pl-2 border-l" style={{ borderColor: '#E3DCC9' }}>
          {WIDTHS.map((wOpt) => (
            <button
              key={wOpt.value}
              onClick={() => setWidth(wOpt.value)}
              title={wOpt.label}
              className="w-8 h-8 rounded-md flex items-center justify-center"
              style={{ background: width === wOpt.value ? '#EAE3D1' : 'transparent' }}
            >
              <span className="rounded-full" style={{ width: wOpt.value + 3, height: wOpt.value + 3, background: '#2A2620' }} />
            </button>
          ))}
        </div>

        <button
          onClick={() => setAutoCorrect((v) => !v)}
          className="flex items-center gap-2 pl-2 pr-1 border-l text-sm"
          style={{ borderColor: '#E3DCC9' }}
        >
          <Sparkles size={16} style={{ color: autoCorrect ? '#1F6F63' : '#A19A85' }} />
          <span style={{ color: autoCorrect ? '#2A2620' : '#A19A85' }}>Correction</span>
          <span
            className="w-9 h-5 rounded-full relative transition-colors"
            style={{ background: autoCorrect ? '#1F6F63' : '#D8D0BC' }}
          >
            <span
              className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all"
              style={{ left: autoCorrect ? 18 : 2 }}
            />
          </span>
        </button>

        <div className="flex items-center gap-1 ml-auto pl-2 border-l" style={{ borderColor: '#E3DCC9' }}>
          <button onClick={undo} disabled={strokes.length === 0} className="p-2 rounded-md disabled:opacity-30" style={{ background: '#FBF9F3' }}>
            <Undo2 size={17} />
          </button>
          <button onClick={redo} disabled={redoStack.length === 0} className="p-2 rounded-md disabled:opacity-30" style={{ background: '#FBF9F3' }}>
            <Redo2 size={17} />
          </button>
          <button onClick={clearAll} disabled={strokes.length === 0} className="p-2 rounded-md disabled:opacity-30" style={{ background: '#FBF9F3' }}>
            <Trash2 size={17} style={{ color: '#A6432E' }} />
          </button>
        </div>
      </div>

      {/* Zone de dessin */}
      <div ref={containerRef} className="flex-1 relative overflow-hidden touch-none">
        <canvas
          ref={canvasRef}
          className="absolute inset-0 cursor-crosshair touch-none"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
        />

        {pendingSuggestion && (
          <div
            className="absolute z-10 flex items-center gap-2 px-3 py-2 rounded-lg shadow-lg"
            style={{ left: popupLeft, top: popupTop, background: '#FFFFFF', border: '1px solid #E3DCC9' }}
          >
            <span className="text-sm whitespace-nowrap">
              On dirait <b>{pendingSuggestion.shape.label}</b>
            </span>
            <button onClick={acceptSuggestion} className="p-1.5 rounded-md" style={{ background: '#1F6F63' }} title="Remplacer par la forme nette">
              <Check size={15} color="#FFFFFF" />
            </button>
            <button onClick={clearPendingSuggestion} className="p-1.5 rounded-md" style={{ background: '#EAE3D1' }} title="Garder le tracé original">
              <X size={15} color="#2A2620" />
            </button>
          </div>
        )}

        {strokes.length === 0 && !pendingSuggestion && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <p className="text-sm text-center max-w-xs" style={{ color: '#A19A85' }}>
              Dessinez un trait droit ou une forme fermée (cercle, carré, rectangle,
              losange, triangle, pentagone, hexagone, étoile…) — une version nette
              sera proposée.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
