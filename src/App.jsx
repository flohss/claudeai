import React, { useEffect, useReducer, useRef, useState } from 'react';
import {
  Undo2, Redo2, Trash2, Check, X, Sparkles, PenLine, Pencil, MousePointer2,
  Download, Save, FolderOpen, Layers, Sun, Moon, FileCode2, Minus, Plus,
  Hand, Square, Circle, Slash, ArrowRight, ChevronUp, ChevronDown, Eye, EyeOff,
  FilePlus2,
} from 'lucide-react';
import {
  dist, classifyShape, getBBox, smoothPathD, strokeBBox, shapeHandlePoints,
  updateShapeHandle, translateStroke, bboxesIntersect, bboxFromPoints,
  unionBBox, shapeFromDrag,
} from './geometry';
import { StrokeView, EditHandles, SelectionOutline, Marquee, DraftShape, Paper } from './canvasElements';
import { useTheme } from './theme';

/**
 * ATELIER — studio de dessin assisté par IA
 * ------------------------------------------------------------------------
 * Un crayon à main levée avec correction de traits (façon Autodraw) : un
 * classifieur géométrique heuristique reconnaît les formes simples et
 * propose une version nette. À côté, des outils de tracé direct (ligne,
 * flèche, rectangle, ellipse) pour un résultat propre du premier coup, un
 * mode Sélection avec multi-sélection au lasso, déplacement/redimension-
 * nement/suppression, un système de calques, le zoom/pan, un historique
 * annuler/rétablir complet, le mode sombre, et l'export PNG/SVG ou la
 * sauvegarde du projet en fichier.
 *
 * Le rendu est vectoriel (SVG) — voir geometry.js pour la géométrie pure
 * et canvasElements.jsx pour les sous-composants de rendu.
 *
 * Points d'extension prévus :
 * 1. classifyShape() (geometry.js) — remplacer/compléter l'heuristique par
 *    un vrai modèle pour reconnaître plus de formes (icônes, écriture).
 * 2. Bibliothèque de formes — associer un contour détecté à des icônes
 *    prédessinées plutôt qu'à une forme géométrique pure.
 * 3. Collaboration — le state {strokes, layers} est un JSON simple,
 *    sérialisable vers un canal temps réel pour du dessin partagé.
 */

const WIDTHS = [
  { label: 'Fin', value: 2.5 },
  { label: 'Moyen', value: 5 },
  { label: 'Épais', value: 9 },
];

const TOOLS = [
  { id: 'draw', label: 'Crayon (P)', icon: Pencil },
  { id: 'select', label: 'Sélection (V)', icon: MousePointer2 },
  { id: 'line', label: 'Ligne (L)', icon: Slash },
  { id: 'arrow', label: 'Flèche (A)', icon: ArrowRight },
  { id: 'rect', label: 'Rectangle (R)', icon: Square },
  { id: 'ellipse', label: 'Ellipse (O)', icon: Circle },
  { id: 'pan', label: 'Main (H)', icon: Hand },
];
const TOOL_SHORTCUTS = { p: 'draw', v: 'select', l: 'line', a: 'arrow', r: 'rect', o: 'ellipse', h: 'pan' };

const BACKGROUNDS = [
  { id: 'ruled', label: 'Ligné' },
  { id: 'grid', label: 'Quadrillé' },
  { id: 'dot', label: 'Pointillé' },
  { id: 'blank', label: 'Blanc' },
];
const DEFAULT_BACKGROUND = 'ruled';

const STORAGE_KEY = 'atelier-drawing-v1';
const DEFAULT_LAYERS = [{ id: 'layer-1', name: 'Calque 1', visible: true }];
const MAX_HISTORY = 100;

function newId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function loadProject() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { strokes: [], layers: DEFAULT_LAYERS, background: DEFAULT_BACKGROUND };
    const data = JSON.parse(raw);
    const layers = Array.isArray(data?.layers) && data.layers.length > 0 ? data.layers : DEFAULT_LAYERS;
    const fallbackLayerId = layers[0].id;
    const rawStrokes = Array.isArray(data) ? data : Array.isArray(data?.strokes) ? data.strokes : [];
    const strokes = rawStrokes.map((s) => ({ ...s, layerId: s.layerId || fallbackLayerId }));
    const background = BACKGROUNDS.some((b) => b.id === data?.background) ? data.background : DEFAULT_BACKGROUND;
    return { strokes, layers, background };
  } catch {
    return { strokes: [], layers: DEFAULT_LAYERS, background: DEFAULT_BACKGROUND };
  }
}

// -- Historique annuler/rétablir -------------------------------------------
// 'commit' = une action ponctuelle (ajout, suppression, forme validée…) :
// un pas d'historique. 'begin-drag' capture l'état AVANT un geste continu
// (déplacer/redimensionner) ; les 'update' qui suivent pendant le glisser
// ne créent pas de pas supplémentaires — tout le geste s'annule en un clic.
function historyReducer(state, action) {
  switch (action.type) {
    case 'commit': {
      const strokes = action.updater(state.strokes);
      const past = [...state.past, state.strokes];
      if (past.length > MAX_HISTORY) past.shift();
      return { strokes, past, future: [] };
    }
    case 'begin-drag': {
      const past = [...state.past, state.strokes];
      if (past.length > MAX_HISTORY) past.shift();
      return { ...state, past, future: [] };
    }
    case 'update':
      return { ...state, strokes: action.updater(state.strokes) };
    case 'undo': {
      if (state.past.length === 0) return state;
      const strokes = state.past[state.past.length - 1];
      return { strokes, past: state.past.slice(0, -1), future: [state.strokes, ...state.future] };
    }
    case 'redo': {
      if (state.future.length === 0) return state;
      const strokes = state.future[0];
      return { strokes, past: [...state.past, state.strokes], future: state.future.slice(1) };
    }
    case 'set':
      return { strokes: action.strokes, past: [], future: [] };
    default:
      return state;
  }
}

// -- Petits composants de présentation --------------------------------------

function ToolbarButton({ active, disabled, onClick, title, colors, children }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className="w-8 h-8 rounded-md flex items-center justify-center shrink-0 disabled:opacity-30"
      style={{ background: active ? colors.activeBg : 'transparent', color: active ? colors.text : colors.textMuted }}
    >
      {children}
    </button>
  );
}

function BackgroundThumb({ id, colors }) {
  const size = 40;
  if (id === 'grid') {
    return (
      <svg width={size} height={size} viewBox="0 0 40 40">
        <rect width="40" height="40" fill={colors.paperBg} />
        {[8, 16, 24, 32].map((v) => (
          <React.Fragment key={v}>
            <line x1={v} y1="0" x2={v} y2="40" stroke={colors.paperLine} strokeWidth="1" />
            <line x1="0" y1={v} x2="40" y2={v} stroke={colors.paperLine} strokeWidth="1" />
          </React.Fragment>
        ))}
      </svg>
    );
  }
  if (id === 'dot') {
    const pts = [];
    for (let y = 8; y <= 32; y += 8) for (let x = 8; x <= 32; x += 8) pts.push([x, y]);
    return (
      <svg width={size} height={size} viewBox="0 0 40 40">
        <rect width="40" height="40" fill={colors.paperBg} />
        {pts.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="1.3" fill={colors.paperLine} />)}
      </svg>
    );
  }
  if (id === 'blank') {
    return (
      <svg width={size} height={size} viewBox="0 0 40 40">
        <rect width="40" height="40" fill={colors.paperBg} />
      </svg>
    );
  }
  // 'ruled'
  return (
    <svg width={size} height={size} viewBox="0 0 40 40">
      <rect width="40" height="40" fill={colors.paperBg} />
      {[10, 20, 30].map((y) => <line key={y} x1="4" y1={y} x2="36" y2={y} stroke={colors.paperLine} strokeWidth="1" />)}
      <line x1="10" y1="0" x2="10" y2="40" stroke={colors.paperMargin} strokeWidth="1" />
    </svg>
  );
}

function LayerRow({ layer, active, onActivate, onToggleVisible, onRename, onDelete, onMoveUp, onMoveDown, canDelete, colors }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(layer.name);

  useEffect(() => {
    setDraft(layer.name);
  }, [layer.name]);

  function commit() {
    setEditing(false);
    const trimmed = draft.trim();
    if (trimmed && trimmed !== layer.name) onRename(trimmed);
    else setDraft(layer.name);
  }

  return (
    <div
      onClick={onActivate}
      className="flex items-center gap-1 px-2 py-1.5 cursor-pointer text-sm"
      style={{ background: active ? colors.activeBg : 'transparent' }}
    >
      <button onClick={(e) => { e.stopPropagation(); onToggleVisible(); }} className="p-0.5 rounded shrink-0" title={layer.visible ? 'Masquer' : 'Afficher'}>
        {layer.visible ? <Eye size={14} /> : <EyeOff size={14} style={{ color: colors.textMuted }} />}
      </button>
      {editing ? (
        <input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit();
            if (e.key === 'Escape') { setDraft(layer.name); setEditing(false); }
          }}
          onClick={(e) => e.stopPropagation()}
          className="flex-1 min-w-0 px-1 rounded text-sm"
          style={{ background: colors.appBg, color: colors.text, border: `1px solid ${colors.border}` }}
        />
      ) : (
        <span
          onDoubleClick={(e) => { e.stopPropagation(); setEditing(true); }}
          className="flex-1 min-w-0 truncate select-none"
          style={{ opacity: layer.visible ? 1 : 0.5 }}
        >
          {layer.name}
        </span>
      )}
      <button onClick={(e) => { e.stopPropagation(); onMoveUp(); }} className="p-0.5 rounded shrink-0" title="Monter">
        <ChevronUp size={13} />
      </button>
      <button onClick={(e) => { e.stopPropagation(); onMoveDown(); }} className="p-0.5 rounded shrink-0" title="Descendre">
        <ChevronDown size={13} />
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        disabled={!canDelete}
        className="p-0.5 rounded shrink-0 disabled:opacity-30"
        title="Supprimer le calque"
      >
        <Trash2 size={13} style={{ color: colors.danger }} />
      </button>
    </div>
  );
}

export default function DrawingAssistant() {
  const { setPref: setThemePref, resolved: themeResolved, colors } = useTheme();

  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const currentPathRef = useRef(null);
  const currentPointsRef = useRef([]);
  const isDrawingRef = useRef(false);
  const dismissTimerRef = useRef(null);
  const dragRef = useRef(null);
  const panRef = useRef(null);
  const marqueeRef = useRef(null);
  const draftRef = useRef(null);
  const openFileRef = useRef(null);

  const [history, dispatch] = useReducer(historyReducer, undefined, () => ({
    strokes: loadProject().strokes, past: [], future: [],
  }));
  const strokes = history.strokes;

  const [layers, setLayers] = useState(() => loadProject().layers);
  const [activeLayerId, setActiveLayerId] = useState(() => loadProject().layers[0]?.id ?? DEFAULT_LAYERS[0].id);
  const [layersPanelOpen, setLayersPanelOpen] = useState(false);
  const [background, setBackground] = useState(() => loadProject().background);
  const [newProjectOpen, setNewProjectOpen] = useState(false);

  const [color, setColor] = useState(colors.penColors[0].hex);
  const [width, setWidth] = useState(WIDTHS[1].value);
  const [autoCorrect, setAutoCorrect] = useState(true);
  const [pendingSuggestion, setPendingSuggestion] = useState(null);
  const [containerSize, setContainerSize] = useState({ w: 800, h: 500 });
  const [tool, setTool] = useState('draw');
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [view, setView] = useState({ x: 0, y: 0, scale: 1 });
  const [draft, setDraft] = useState(null);
  const [marquee, setMarquee] = useState(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    function resize() {
      const rect = container.getBoundingClientRect();
      setContainerSize({ w: rect.width, h: rect.height });
    }
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(container);
    return () => ro.disconnect();
  }, []);

  // Molette = zoom centré sur le curseur. Écouteur natif (non passif) pour
  // pouvoir bloquer le défilement de la page pendant qu'on zoome le canevas.
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    function onWheel(e) {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const sx = e.clientX - rect.left, sy = e.clientY - rect.top;
      const factor = Math.exp(-e.deltaY * 0.0015);
      setView((v) => {
        const newScale = Math.min(6, Math.max(0.15, v.scale * factor));
        const worldX = (sx - v.x) / v.scale, worldY = (sy - v.y) / v.scale;
        return { scale: newScale, x: sx - worldX * newScale, y: sy - worldY * newScale };
      });
    }
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  // Nettoie la sélection des tracés supprimés (undo, effacer, suppr, calque supprimé).
  useEffect(() => {
    setSelectedIds((prev) => {
      const next = new Set([...prev].filter((id) => strokes.some((s) => s.id === id)));
      return next.size === prev.size ? prev : next;
    });
  }, [strokes]);

  // Sauvegarde locale (différée) + filet de sécurité si l'onglet se ferme trop vite.
  useEffect(() => {
    const timer = setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ strokes, layers, background }));
      } catch {
        // stockage indisponible (navigation privée, quota…) — on ignore.
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [strokes, layers, background]);

  useEffect(() => {
    function flush() {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ strokes, layers, background }));
      } catch {
        // stockage indisponible — on ignore.
      }
    }
    window.addEventListener('beforeunload', flush);
    window.addEventListener('pagehide', flush);
    return () => {
      window.removeEventListener('beforeunload', flush);
      window.removeEventListener('pagehide', flush);
    };
  }, [strokes, layers, background]);

  useEffect(() => {
    if (!pendingSuggestion) return;
    dismissTimerRef.current = setTimeout(() => setPendingSuggestion(null), 4500);
    return () => clearTimeout(dismissTimerRef.current);
  }, [pendingSuggestion]);

  // -- Raccourcis clavier ---------------------------------------------------

  useEffect(() => {
    function onKeyDown(e) {
      const meta = e.ctrlKey || e.metaKey;
      if (meta && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        dispatch({ type: e.shiftKey ? 'redo' : 'undo' });
        return;
      }
      if (meta && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        dispatch({ type: 'redo' });
        return;
      }
      if ((e.key === 'Delete' || e.key === 'Backspace') && tool === 'select' && selectedIds.size > 0) {
        e.preventDefault();
        dispatch({ type: 'commit', updater: (prev) => prev.filter((s) => !selectedIds.has(s.id)) });
        setSelectedIds(new Set());
        return;
      }
      const tag = document.activeElement?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || meta || e.altKey) return;
      const next = TOOL_SHORTCUTS[e.key.toLowerCase()];
      if (next) { e.preventDefault(); switchTool(next); }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tool, selectedIds]);

  // -- Coordonnées : écran (px du conteneur) <-> monde (indépendant du zoom) --

  function getScreenPos(e) {
    const rect = svgRef.current.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }
  function getWorldPos(e) {
    const s = getScreenPos(e);
    return { x: (s.x - view.x) / view.scale, y: (s.y - view.y) / view.scale };
  }
  function worldToScreen(p) {
    return { x: p.x * view.scale + view.x, y: p.y * view.scale + view.y };
  }

  function isLayerVisible(layerId) {
    return layers.find((l) => l.id === layerId)?.visible !== false;
  }

  function clearPendingSuggestion() {
    if (dismissTimerRef.current) {
      clearTimeout(dismissTimerRef.current);
      dismissTimerRef.current = null;
    }
    setPendingSuggestion(null);
  }

  // -- Crayon (outil 'draw', à main levée + correction) ------------------------

  function handlePointerDown(e) {
    e.preventDefault();
    svgRef.current.setPointerCapture(e.pointerId);
    clearPendingSuggestion();
    isDrawingRef.current = true;
    currentPointsRef.current = [getWorldPos(e)];
  }
  function handlePointerMove(e) {
    if (!isDrawingRef.current) return;
    currentPointsRef.current.push(getWorldPos(e));
    if (currentPathRef.current) {
      currentPathRef.current.setAttribute('d', smoothPathD(currentPointsRef.current));
    }
  }
  function handlePointerUp() {
    if (!isDrawingRef.current) return;
    isDrawingRef.current = false;
    const points = currentPointsRef.current;
    currentPointsRef.current = [];
    if (currentPathRef.current) currentPathRef.current.setAttribute('d', '');
    if (points.length < 2) return;

    const stroke = { id: newId(), layerId: activeLayerId, color, width, type: 'freehand', shape: null, points };
    dispatch({ type: 'commit', updater: (prev) => [...prev, stroke] });

    if (autoCorrect) {
      const shape = classifyShape(points);
      if (shape) {
        const bbox = getBBox(points);
        setPendingSuggestion({ strokeId: stroke.id, shape, anchor: { x: bbox.maxX, y: bbox.minY } });
      }
    }
  }

  function acceptSuggestion() {
    if (!pendingSuggestion) return;
    dispatch({
      type: 'commit',
      updater: (prev) => prev.map((s) => (s.id === pendingSuggestion.strokeId ? { ...s, type: 'corrected', shape: pendingSuggestion.shape } : s)),
    });
    clearPendingSuggestion();
  }

  // -- Sélection / édition (outil 'select') ------------------------------------

  function handleStrokeGrab(e, stroke) {
    e.stopPropagation();
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    const world = getWorldPos(e);

    let nextSelected;
    if (e.shiftKey) {
      nextSelected = new Set(selectedIds);
      if (nextSelected.has(stroke.id)) nextSelected.delete(stroke.id);
      else nextSelected.add(stroke.id);
    } else if (selectedIds.has(stroke.id)) {
      nextSelected = selectedIds;
    } else {
      nextSelected = new Set([stroke.id]);
    }
    setSelectedIds(nextSelected);
    if (nextSelected.size === 0) { dragRef.current = null; return; }

    dispatch({ type: 'begin-drag' });
    const originals = new Map();
    for (const s of strokes) if (nextSelected.has(s.id)) originals.set(s.id, s);
    dragRef.current = { type: 'move', ids: nextSelected, start: world, originals };
  }

  function handleHandleGrab(e, stroke, index) {
    e.stopPropagation();
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    setSelectedIds(new Set([stroke.id]));
    dispatch({ type: 'begin-drag' });
    dragRef.current = { type: 'handle', strokeId: stroke.id, index, original: stroke };
  }

  function deleteSelected() {
    if (selectedIds.size === 0) return;
    dispatch({ type: 'commit', updater: (prev) => prev.filter((s) => !selectedIds.has(s.id)) });
    setSelectedIds(new Set());
  }

  // -- Dispatch au niveau du canevas SVG selon l'outil actif -------------------

  function handleSvgPointerDown(e) {
    if (e.button === 1 || (tool === 'pan' && e.button === 0)) {
      e.preventDefault();
      svgRef.current.setPointerCapture(e.pointerId);
      panRef.current = { startScreen: getScreenPos(e), startView: view };
      return;
    }
    if (e.button !== 0) return;

    if (tool === 'select') {
      setSelectedIds(new Set());
      svgRef.current.setPointerCapture(e.pointerId);
      const world = getWorldPos(e);
      marqueeRef.current = { start: world };
      setMarquee({ start: world, end: world });
      return;
    }
    if (tool === 'draw') {
      handlePointerDown(e);
      return;
    }
    // outils de tracé direct : ligne, flèche, rectangle, ellipse
    svgRef.current.setPointerCapture(e.pointerId);
    const world = getWorldPos(e);
    draftRef.current = { start: world };
    setDraft({ tool, start: world, end: world });
  }

  function handleSvgPointerMove(e) {
    if (panRef.current) {
      const s = getScreenPos(e);
      const dx = s.x - panRef.current.startScreen.x, dy = s.y - panRef.current.startScreen.y;
      setView({ ...panRef.current.startView, x: panRef.current.startView.x + dx, y: panRef.current.startView.y + dy });
      return;
    }
    if (marqueeRef.current) {
      setMarquee({ start: marqueeRef.current.start, end: getWorldPos(e) });
      return;
    }
    if (draftRef.current) {
      setDraft({ tool, start: draftRef.current.start, end: getWorldPos(e) });
      return;
    }
    if (dragRef.current) {
      const world = getWorldPos(e);
      const drag = dragRef.current;
      dispatch({
        type: 'update',
        updater: (prev) => prev.map((s) => {
          if (drag.type === 'move') {
            if (!drag.ids.has(s.id)) return s;
            const original = drag.originals.get(s.id);
            return translateStroke(original, world.x - drag.start.x, world.y - drag.start.y);
          }
          if (drag.type === 'handle') {
            if (s.id !== drag.strokeId) return s;
            return { ...drag.original, shape: updateShapeHandle(drag.original.shape, drag.index, world) };
          }
          return s;
        }),
      });
      return;
    }
    if (tool === 'draw') handlePointerMove(e);
  }

  function handleSvgPointerUp(e) {
    if (panRef.current) { panRef.current = null; return; }

    if (marqueeRef.current) {
      const m = marqueeRef.current;
      marqueeRef.current = null;
      setMarquee(null);
      const world = getWorldPos(e);
      if (dist(m.start, world) < 4 / view.scale) return; // simple clic : déjà désélectionné
      const box = bboxFromPoints(m.start, world);
      const hits = strokes.filter((s) => isLayerVisible(s.layerId) && bboxesIntersect(strokeBBox(s), box));
      setSelectedIds(new Set(hits.map((s) => s.id)));
      return;
    }

    if (draftRef.current) {
      const d = draftRef.current;
      draftRef.current = null;
      setDraft(null);
      const world = getWorldPos(e);
      if (dist(d.start, world) > 3 / view.scale) {
        const shape = shapeFromDrag(tool, d.start, world);
        const stroke = { id: newId(), layerId: activeLayerId, color, width, type: 'shape', shape, points: shapeHandlePoints(shape) };
        dispatch({ type: 'commit', updater: (prev) => [...prev, stroke] });
        setSelectedIds(new Set([stroke.id]));
      }
      return;
    }

    if (dragRef.current) { dragRef.current = null; return; }
    if (tool === 'draw') handlePointerUp(e);
  }

  function switchTool(next) {
    if (next === tool) { setTool(next); return; }
    clearPendingSuggestion();
    isDrawingRef.current = false;
    currentPointsRef.current = [];
    if (currentPathRef.current) currentPathRef.current.setAttribute('d', '');
    dragRef.current = null;
    marqueeRef.current = null;
    draftRef.current = null;
    setMarquee(null);
    setDraft(null);
    setSelectedIds(new Set());
    setTool(next);
  }

  function zoomBy(factor) {
    setView((v) => {
      const cx = containerSize.w / 2, cy = containerSize.h / 2;
      const newScale = Math.min(6, Math.max(0.15, v.scale * factor));
      const worldX = (cx - v.x) / v.scale, worldY = (cy - v.y) / v.scale;
      return { scale: newScale, x: cx - worldX * newScale, y: cy - worldY * newScale };
    });
  }
  function resetView() {
    setView({ x: 0, y: 0, scale: 1 });
  }

  function clearAll() {
    clearPendingSuggestion();
    setSelectedIds(new Set());
    dispatch({ type: 'commit', updater: () => [] });
  }

  function startNewProject(bgId) {
    if (strokes.length > 0 && !window.confirm('Commencer un nouveau projet ? Le dessin actuel sera perdu (pensez à l’exporter si besoin).')) {
      return;
    }
    clearPendingSuggestion();
    setSelectedIds(new Set());
    setLayers(DEFAULT_LAYERS);
    setActiveLayerId(DEFAULT_LAYERS[0].id);
    setView({ x: 0, y: 0, scale: 1 });
    setBackground(bgId);
    dispatch({ type: 'set', strokes: [] });
    setNewProjectOpen(false);
  }

  // -- Calques -----------------------------------------------------------------

  function addLayer() {
    const id = newId();
    setLayers((prev) => [...prev, { id, name: `Calque ${prev.length + 1}`, visible: true }]);
    setActiveLayerId(id);
  }
  function renameLayer(id, name) {
    setLayers((prev) => prev.map((l) => (l.id === id ? { ...l, name } : l)));
  }
  function toggleLayerVisible(id) {
    setLayers((prev) => prev.map((l) => (l.id === id ? { ...l, visible: !l.visible } : l)));
  }
  function deleteLayer(id) {
    if (layers.length <= 1) return;
    const remaining = layers.filter((l) => l.id !== id);
    setLayers(remaining);
    dispatch({ type: 'commit', updater: (prev) => prev.filter((s) => s.layerId !== id) });
    if (activeLayerId === id) setActiveLayerId(remaining[0]?.id);
  }
  function moveLayer(id, dir) {
    setLayers((prev) => {
      const idx = prev.findIndex((l) => l.id === id);
      const swapWith = idx + dir;
      if (idx === -1 || swapWith < 0 || swapWith >= prev.length) return prev;
      const next = prev.slice();
      [next[idx], next[swapWith]] = [next[swapWith], next[idx]];
      return next;
    });
  }

  // -- Export / sauvegarde -------------------------------------------------------

  function computeContentBBox() {
    const boxes = strokes.filter((s) => isLayerVisible(s.layerId)).map(strokeBBox);
    return unionBBox(boxes);
  }

  function buildExportClone(padding = 24) {
    const box = computeContentBBox();
    if (!box || !svgRef.current) return null;
    const w = box.w + padding * 2, h = box.h + padding * 2;

    const clone = svgRef.current.cloneNode(true);
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    clone.setAttribute('width', String(w));
    clone.setAttribute('height', String(h));
    clone.setAttribute('viewBox', `0 0 ${w} ${h}`);

    const g = clone.querySelector('[data-world-group]');
    if (g) g.setAttribute('transform', `translate(${padding - box.minX} ${padding - box.minY})`);
    clone.querySelectorAll('[data-ui-only]').forEach((el) => el.remove());

    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bg.setAttribute('width', String(w));
    bg.setAttribute('height', String(h));
    bg.setAttribute('fill', colors.paperBg);
    clone.insertBefore(bg, clone.firstChild);

    return { clone, w, h };
  }

  function exportPNG() {
    const built = buildExportClone();
    if (!built) return;
    const { clone, w, h } = built;
    const svgUrl = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], { type: 'image/svg+xml;charset=utf-8' }));
    const img = new Image();
    img.onload = () => {
      const scale = 2;
      const canvas = document.createElement('canvas');
      canvas.width = w * scale;
      canvas.height = h * scale;
      const ctx = canvas.getContext('2d');
      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0, w, h);
      URL.revokeObjectURL(svgUrl);
      canvas.toBlob((blob) => {
        if (!blob) return;
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = 'atelier.png';
        link.click();
        URL.revokeObjectURL(link.href);
      }, 'image/png');
    };
    img.src = svgUrl;
  }

  function exportSVGFile() {
    const built = buildExportClone();
    if (!built) return;
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(built.clone)], { type: 'image/svg+xml;charset=utf-8' }));
    link.download = 'atelier.svg';
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function saveProjectFile() {
    const data = { version: 1, strokes, layers, background };
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    link.download = 'atelier.json';
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function openProjectFile(e) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result);
        const nextLayers = Array.isArray(data.layers) && data.layers.length > 0 ? data.layers : DEFAULT_LAYERS;
        const fallbackId = nextLayers[0].id;
        const nextStrokes = Array.isArray(data.strokes) ? data.strokes.map((s) => ({ ...s, layerId: s.layerId || fallbackId })) : [];
        const nextBackground = BACKGROUNDS.some((b) => b.id === data.background) ? data.background : DEFAULT_BACKGROUND;
        setLayers(nextLayers);
        setActiveLayerId(fallbackId);
        setSelectedIds(new Set());
        setBackground(nextBackground);
        dispatch({ type: 'set', strokes: nextStrokes });
      } catch {
        window.alert("Impossible de lire ce fichier : ce n'est pas un projet Atelier valide.");
      }
    };
    reader.readAsText(file);
  }

  // -- Dérivés pour le rendu -----------------------------------------------------

  const canUndo = history.past.length > 0;
  const canRedo = history.future.length > 0;

  const visibleWorldBounds = {
    minX: (0 - view.x) / view.scale,
    minY: (0 - view.y) / view.scale,
    maxX: (containerSize.w - view.x) / view.scale,
    maxY: (containerSize.h - view.y) / view.scale,
  };

  const strokesByLayer = layers.map((layer) => ({ layer, items: strokes.filter((s) => s.layerId === layer.id) }));

  const selectedStrokes = strokes.filter((s) => selectedIds.has(s.id) && isLayerVisible(s.layerId));
  const singleSelectedStroke = selectedStrokes.length === 1 ? selectedStrokes[0] : null;
  const selUnionBBox = selectedStrokes.length > 0 ? unionBBox(selectedStrokes.map(strokeBBox)) : null;

  const popupAnchorScreen = pendingSuggestion ? worldToScreen(pendingSuggestion.anchor) : null;
  const popupLeft = popupAnchorScreen ? Math.min(popupAnchorScreen.x + 14, containerSize.w - 200) : 0;
  const popupTop = popupAnchorScreen ? Math.max(popupAnchorScreen.y - 56, 8) : 0;

  const deleteAnchorScreen = selUnionBBox ? worldToScreen({ x: selUnionBBox.maxX, y: selUnionBBox.minY }) : null;
  const deleteLeft = deleteAnchorScreen ? Math.min(deleteAnchorScreen.x + 10, containerSize.w - 40) : 0;
  const deleteTop = deleteAnchorScreen ? Math.max(deleteAnchorScreen.y - 44, 8) : 0;

  const activeLayer = layers.find((l) => l.id === activeLayerId);
  const cursor = tool === 'draw' || tool === 'line' || tool === 'arrow' || tool === 'rect' || tool === 'ellipse'
    ? 'crosshair' : tool === 'pan' ? 'grab' : 'default';

  return (
    <div
      className="w-full h-screen flex flex-col"
      style={{
        background: colors.appBg, color: colors.text, fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        transition: 'background-color 0.15s ease, color 0.15s ease',
        '--atelier-accent': colors.accent,
      }}
    >
      {/* Barre d'outils */}
      <div className="flex flex-wrap items-center gap-4 px-4 py-3 border-b" style={{ borderColor: colors.border, background: colors.toolbarBg }}>
        <div className="flex items-center gap-2 pr-3 mr-1 border-r" style={{ borderColor: colors.border }}>
          <PenLine size={18} style={{ color: colors.danger }} />
          <span className="text-sm font-semibold tracking-wide" style={{ fontFamily: 'ui-serif, Georgia, serif' }}>Atelier</span>
        </div>

        <div className="flex items-center gap-1 pr-2 border-r" style={{ borderColor: colors.border }}>
          {TOOLS.map(({ id, label, icon: Icon }) => (
            <ToolbarButton key={id} active={tool === id} onClick={() => switchTool(id)} title={label} colors={colors}>
              <Icon size={16} />
            </ToolbarButton>
          ))}
        </div>

        <div className="flex items-center gap-1.5">
          {colors.penColors.map((c) => (
            <button
              key={c.hex}
              onClick={() => setColor(c.hex)}
              title={c.name}
              className="w-6 h-6 rounded-full transition-transform shrink-0"
              style={{
                background: c.hex,
                transform: color === c.hex ? 'scale(1.15)' : 'scale(1)',
                boxShadow: color === c.hex ? `0 0 0 2px ${colors.toolbarBg}, 0 0 0 4px ${c.hex}` : `inset 0 0 0 1px ${colors.border}`,
              }}
            />
          ))}
          <label
            className="w-6 h-6 rounded-full overflow-hidden relative cursor-pointer shrink-0"
            style={{ background: color, boxShadow: `inset 0 0 0 1px ${colors.border}` }}
            title="Couleur personnalisée"
          >
            <input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
          </label>
        </div>

        <div className="flex items-center gap-1 pl-2 border-l" style={{ borderColor: colors.border }}>
          {WIDTHS.map((wOpt) => (
            <ToolbarButton key={wOpt.value} active={width === wOpt.value} onClick={() => setWidth(wOpt.value)} title={wOpt.label} colors={colors}>
              <span className="rounded-full" style={{ width: wOpt.value + 3, height: wOpt.value + 3, background: colors.text }} />
            </ToolbarButton>
          ))}
        </div>

        <button
          onClick={() => setAutoCorrect((v) => !v)}
          className="flex items-center gap-2 pl-2 pr-1 border-l text-sm"
          style={{ borderColor: colors.border }}
        >
          <Sparkles size={16} style={{ color: autoCorrect ? colors.accent : colors.textMuted }} />
          <span style={{ color: autoCorrect ? colors.text : colors.textMuted }}>Correction</span>
          <span className="w-9 h-5 rounded-full relative transition-colors" style={{ background: autoCorrect ? colors.accent : colors.border }}>
            <span className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all" style={{ left: autoCorrect ? 18 : 2 }} />
          </span>
        </button>

        <div className="flex items-center gap-1 ml-auto pl-2 border-l flex-wrap justify-end" style={{ borderColor: colors.border }}>
          <ToolbarButton active={newProjectOpen} onClick={() => setNewProjectOpen((v) => !v)} title="Nouveau projet" colors={colors}>
            <FilePlus2 size={17} />
          </ToolbarButton>
          <ToolbarButton active={layersPanelOpen} onClick={() => setLayersPanelOpen((v) => !v)} title="Calques" colors={colors}>
            <Layers size={17} />
          </ToolbarButton>
          <ToolbarButton onClick={() => dispatch({ type: 'undo' })} disabled={!canUndo} title="Annuler (Ctrl+Z)" colors={colors}>
            <Undo2 size={17} />
          </ToolbarButton>
          <ToolbarButton onClick={() => dispatch({ type: 'redo' })} disabled={!canRedo} title="Rétablir (Ctrl+Maj+Z)" colors={colors}>
            <Redo2 size={17} />
          </ToolbarButton>
          <ToolbarButton onClick={clearAll} disabled={strokes.length === 0} title="Tout effacer" colors={colors}>
            <Trash2 size={17} style={{ color: colors.danger }} />
          </ToolbarButton>
          <ToolbarButton onClick={saveProjectFile} disabled={strokes.length === 0} title="Enregistrer le projet (.json)" colors={colors}>
            <Save size={17} />
          </ToolbarButton>
          <ToolbarButton onClick={() => openFileRef.current?.click()} title="Ouvrir un projet (.json)" colors={colors}>
            <FolderOpen size={17} />
          </ToolbarButton>
          <ToolbarButton onClick={exportPNG} disabled={strokes.length === 0} title="Exporter en PNG" colors={colors}>
            <Download size={17} />
          </ToolbarButton>
          <ToolbarButton onClick={exportSVGFile} disabled={strokes.length === 0} title="Exporter en SVG" colors={colors}>
            <FileCode2 size={17} />
          </ToolbarButton>
          <ToolbarButton onClick={() => setThemePref(themeResolved === 'dark' ? 'light' : 'dark')} title={themeResolved === 'dark' ? 'Thème clair' : 'Thème sombre'} colors={colors}>
            {themeResolved === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
          </ToolbarButton>
          <input ref={openFileRef} type="file" accept=".json,application/json" onChange={openProjectFile} className="hidden" />
        </div>
      </div>

      {/* Barre de statut */}
      <div className="flex items-center gap-3 px-4 py-1 text-xs border-b" style={{ borderColor: colors.border, background: colors.toolbarBg, color: colors.textMuted }}>
        <div className="flex items-center gap-0.5">
          <button onClick={() => zoomBy(1 / 1.2)} title="Zoom arrière" className="w-5 h-5 rounded flex items-center justify-center"><Minus size={12} /></button>
          <button onClick={resetView} className="px-1 tabular-nums rounded hover:underline" title="Réinitialiser la vue">{Math.round(view.scale * 100)}%</button>
          <button onClick={() => zoomBy(1.2)} title="Zoom avant" className="w-5 h-5 rounded flex items-center justify-center"><Plus size={12} /></button>
        </div>
        <span>{strokes.length} forme{strokes.length === 1 ? '' : 's'}</span>
        {selectedIds.size > 0 && <span>· {selectedIds.size} sélectionnée{selectedIds.size === 1 ? '' : 's'}</span>}
        <span className="ml-auto truncate">{activeLayer?.name}</span>
      </div>

      {/* Zone de dessin */}
      <div ref={containerRef} className="flex-1 relative overflow-hidden touch-none">
        <svg
          ref={svgRef}
          width={containerSize.w}
          height={containerSize.h}
          className="absolute inset-0 touch-none"
          style={{ cursor }}
          onPointerDown={handleSvgPointerDown}
          onPointerMove={handleSvgPointerMove}
          onPointerUp={handleSvgPointerUp}
          onPointerLeave={handleSvgPointerUp}
          onContextMenu={(e) => { if (tool !== 'select') e.preventDefault(); }}
        >
          <g data-world-group="true" transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}>
            <Paper bounds={visibleWorldBounds} colors={colors} style={background} />

            {strokesByLayer.map(({ layer, items }) => layer.visible && items.map((s) => (
              <StrokeView key={s.id} stroke={s} interactive={tool === 'select'} onGrab={handleStrokeGrab} />
            )))}

            <path ref={currentPathRef} data-ui-only="true" fill="none" stroke={color} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round" pointerEvents="none" />

            {draft && (
              <g data-ui-only="true"><DraftShape tool={draft.tool} start={draft.start} end={draft.end} color={color} width={width} /></g>
            )}

            {selectedStrokes.map((s) => (
              <g data-ui-only="true" key={s.id}><SelectionOutline bbox={strokeBBox(s)} scale={view.scale} accent={colors.accent} /></g>
            ))}
            {singleSelectedStroke && (
              <g data-ui-only="true"><EditHandles stroke={singleSelectedStroke} onHandleGrab={handleHandleGrab} scale={view.scale} accent={colors.accent} /></g>
            )}

            {marquee && <g data-ui-only="true"><Marquee start={marquee.start} end={marquee.end} colors={colors} /></g>}
          </g>
        </svg>

        {pendingSuggestion && (
          <div
            className="absolute z-10 flex items-center gap-2 px-3 py-2 rounded-lg shadow-lg"
            style={{ left: popupLeft, top: popupTop, background: colors.panelBg, border: `1px solid ${colors.border}`, color: colors.text }}
          >
            <span className="text-sm whitespace-nowrap">
              On dirait <b>{pendingSuggestion.shape.label}</b>
            </span>
            <button onClick={acceptSuggestion} className="p-1.5 rounded-md" style={{ background: colors.accent }} title="Remplacer par la forme nette">
              <Check size={15} color={colors.accentText} />
            </button>
            <button onClick={clearPendingSuggestion} className="p-1.5 rounded-md" style={{ background: colors.activeBg }} title="Garder le tracé original">
              <X size={15} color={colors.text} />
            </button>
          </div>
        )}

        {selectedStrokes.length > 0 && (
          <div
            className="absolute z-10 flex items-center gap-1 p-1 rounded-lg shadow-lg"
            style={{ left: deleteLeft, top: deleteTop, background: colors.panelBg, border: `1px solid ${colors.border}` }}
          >
            <button onClick={deleteSelected} className="p-1.5 rounded-md" style={{ background: colors.hoverBg }} title="Supprimer (Suppr)">
              <Trash2 size={14} color={colors.danger} />
            </button>
          </div>
        )}

        {newProjectOpen && (
          <div
            className="absolute top-3 left-3 z-20 w-72 rounded-lg shadow-lg overflow-hidden"
            style={{ background: colors.panelBg, border: `1px solid ${colors.border}` }}
          >
            <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: colors.border }}>
              <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: colors.textMuted }}>Nouveau projet — arrière-plan</span>
              <button onClick={() => setNewProjectOpen(false)} className="p-1 rounded" title="Fermer"><X size={14} /></button>
            </div>
            <div className="grid grid-cols-2 gap-2 p-3">
              {BACKGROUNDS.map((b) => (
                <button
                  key={b.id}
                  onClick={() => startNewProject(b.id)}
                  className="flex flex-col items-center gap-1 p-2 rounded-md"
                  style={{ background: background === b.id ? colors.activeBg : 'transparent' }}
                >
                  <div className="rounded overflow-hidden" style={{ border: `1px solid ${colors.border}` }}>
                    <BackgroundThumb id={b.id} colors={colors} />
                  </div>
                  <span className="text-xs" style={{ color: colors.text }}>{b.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {layersPanelOpen && (
          <div
            className="absolute top-3 right-3 z-20 w-56 rounded-lg shadow-lg overflow-hidden"
            style={{ background: colors.panelBg, border: `1px solid ${colors.border}` }}
          >
            <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: colors.border }}>
              <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: colors.textMuted }}>Calques</span>
              <button onClick={addLayer} className="p-1 rounded" title="Ajouter un calque"><Plus size={14} /></button>
            </div>
            <div className="max-h-64 overflow-y-auto">
              {[...layers].reverse().map((l) => (
                <LayerRow
                  key={l.id}
                  layer={l}
                  active={l.id === activeLayerId}
                  onActivate={() => setActiveLayerId(l.id)}
                  onToggleVisible={() => toggleLayerVisible(l.id)}
                  onRename={(name) => renameLayer(l.id, name)}
                  onDelete={() => deleteLayer(l.id)}
                  onMoveUp={() => moveLayer(l.id, 1)}
                  onMoveDown={() => moveLayer(l.id, -1)}
                  canDelete={layers.length > 1}
                  colors={colors}
                />
              ))}
            </div>
          </div>
        )}

        {strokes.length === 0 && !pendingSuggestion && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <p className="text-sm text-center max-w-sm" style={{ color: colors.textMuted }}>
              Crayon : dessinez un trait droit ou une forme fermée — une version nette
              sera proposée. Ou choisissez directement un outil de forme (ligne, flèche,
              rectangle, ellipse). Molette pour zoomer, outil Main pour vous déplacer.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
