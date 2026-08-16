import { smoothPathD, shapeHandlePoints, arrowHeadPoints, bboxFromPoints } from './geometry';

// ---------------------------------------------------------------------
// Composants SVG de rendu — un tracé (StrokeView), ses poignées d'édition
// (EditHandles), le papier réglé (Paper), la sélection au lasso (Marquee)
// et l'aperçu en direct d'un outil de forme (DraftShape).
// ---------------------------------------------------------------------

function ShapeGeometry({ shape, stroke, hitWidth, pointerEvents, grabProps }) {
  if (shape.type === 'line' || shape.type === 'arrow') {
    const [p0, p1] = shape.points;
    const head = shape.type === 'arrow' ? arrowHeadPoints(p0, p1, Math.max(14, stroke.width * 2.6)) : null;
    const shaftEnd = head ? { x: (p1.x + head[1].x + head[2].x) / 3, y: (p1.y + head[1].y + head[2].y) / 3 } : p1;
    return (
      <g>
        <line x1={p0.x} y1={p0.y} x2={shaftEnd.x} y2={shaftEnd.y}
          stroke={stroke.color} strokeWidth={stroke.width} strokeLinecap="round" pointerEvents="none" />
        {head && <polygon points={head.map((p) => `${p.x},${p.y}`).join(' ')} fill={stroke.color} pointerEvents="none" />}
        <line x1={p0.x} y1={p0.y} x2={p1.x} y2={p1.y}
          stroke="transparent" strokeWidth={hitWidth} pointerEvents={pointerEvents} {...grabProps} />
      </g>
    );
  }
  if (shape.type === 'ellipse') {
    const rx = Math.max(shape.bbox.w / 2, 1), ry = Math.max(shape.bbox.h / 2, 1);
    return (
      <g>
        <ellipse cx={shape.bbox.cx} cy={shape.bbox.cy} rx={rx} ry={ry} fill="none"
          stroke={stroke.color} strokeWidth={stroke.width} pointerEvents="none" />
        <ellipse cx={shape.bbox.cx} cy={shape.bbox.cy} rx={rx} ry={ry} fill="transparent"
          stroke="transparent" strokeWidth={hitWidth} pointerEvents={pointerEvents} {...grabProps} />
      </g>
    );
  }
  if (shape.type === 'rect') {
    const { minX, minY, w, h } = shape.bbox;
    return (
      <g>
        <rect x={minX} y={minY} width={Math.max(w, 0.01)} height={Math.max(h, 0.01)} fill="none"
          stroke={stroke.color} strokeWidth={stroke.width} strokeLinejoin="round" pointerEvents="none" />
        <rect x={minX} y={minY} width={Math.max(w, 0.01)} height={Math.max(h, 0.01)} fill="transparent"
          stroke="transparent" strokeWidth={hitWidth} pointerEvents={pointerEvents} {...grabProps} />
      </g>
    );
  }
  // polygon
  const pts = shape.points.map((p) => `${p.x},${p.y}`).join(' ');
  return (
    <g>
      <polygon points={pts} fill="none" stroke={stroke.color} strokeWidth={stroke.width} strokeLinejoin="round" pointerEvents="none" />
      <polygon points={pts} fill="transparent" stroke="transparent" strokeWidth={hitWidth} pointerEvents={pointerEvents} {...grabProps} />
    </g>
  );
}

export function StrokeView({ stroke, interactive, onGrab }) {
  const grabProps = interactive ? { onPointerDown: (e) => onGrab(e, stroke), style: { cursor: 'move' } } : {};
  const hitPointerEvents = interactive ? 'auto' : 'none';
  const hitWidth = Math.max(stroke.width, 18);

  if (stroke.shape) {
    return (
      <g data-stroke-id={stroke.id}>
        <ShapeGeometry shape={stroke.shape} stroke={stroke} hitWidth={hitWidth} pointerEvents={hitPointerEvents} grabProps={grabProps} />
      </g>
    );
  }

  const d = smoothPathD(stroke.points);
  return (
    <g data-stroke-id={stroke.id}>
      <path d={d} fill="none" stroke={stroke.color} strokeWidth={stroke.width} strokeLinecap="round" strokeLinejoin="round" pointerEvents="none" />
      <path d={d} fill="none" stroke="transparent" strokeWidth={hitWidth} pointerEvents={hitPointerEvents} {...grabProps} />
    </g>
  );
}

export function EditHandles({ stroke, onHandleGrab, scale, accent }) {
  if (!stroke.shape) return null;
  const points = shapeHandlePoints(stroke.shape);
  const resizeHandle = stroke.shape.type === 'ellipse' || stroke.shape.type === 'rect';
  const r = 6 / scale;
  return (
    <>
      {points.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r={r}
          fill="#FFFFFF"
          stroke={accent}
          strokeWidth={2 / scale}
          style={{ cursor: resizeHandle ? 'nwse-resize' : 'grab' }}
          onPointerDown={(e) => onHandleGrab(e, stroke, i)}
        />
      ))}
    </>
  );
}

export function SelectionOutline({ bbox, scale, accent }) {
  return (
    <rect
      x={bbox.minX - 6} y={bbox.minY - 6}
      width={bbox.w + 12} height={bbox.h + 12}
      fill="none" stroke={accent} strokeWidth={1.5 / scale} strokeDasharray={`${4 / scale} ${3 / scale}`}
      pointerEvents="none"
    />
  );
}

export function Marquee({ start, end, colors }) {
  const b = bboxFromPoints(start, end);
  return (
    <rect x={b.minX} y={b.minY} width={b.w} height={b.h}
      fill={colors.marqueeFill} stroke={colors.marqueeStroke} strokeWidth={1} vectorEffect="non-scaling-stroke"
      pointerEvents="none" />
  );
}

export function DraftShape({ tool, start, end, color, width }) {
  const stroke = { color, width };
  if (tool === 'ellipse') {
    const bbox = bboxFromPoints(start, end);
    return <ShapeGeometry shape={{ type: 'ellipse', bbox }} stroke={stroke} hitWidth={0} pointerEvents="none" grabProps={{}} />;
  }
  if (tool === 'rect') {
    const bbox = bboxFromPoints(start, end);
    return <ShapeGeometry shape={{ type: 'rect', bbox }} stroke={stroke} hitWidth={0} pointerEvents="none" grabProps={{}} />;
  }
  return <ShapeGeometry shape={{ type: tool, points: [start, end] }} stroke={stroke} hitWidth={0} pointerEvents="none" grabProps={{}} />;
}

const PAPER_STEP = 32;

export function Paper({ bounds, colors, style = 'ruled' }) {
  if (style === 'blank') return null;

  if (style === 'grid') {
    const hLines = [];
    const vStart = Math.floor(bounds.minY / PAPER_STEP) * PAPER_STEP;
    for (let y = vStart; y < bounds.maxY; y += PAPER_STEP) hLines.push(y);
    const vLines = [];
    const hStart = Math.floor(bounds.minX / PAPER_STEP) * PAPER_STEP;
    for (let x = hStart; x < bounds.maxX; x += PAPER_STEP) vLines.push(x);
    return (
      <g pointerEvents="none">
        {hLines.map((y) => (
          <line key={`h${y}`} x1={bounds.minX} y1={y} x2={bounds.maxX} y2={y} stroke={colors.paperLine} strokeWidth={1} vectorEffect="non-scaling-stroke" />
        ))}
        {vLines.map((x) => (
          <line key={`v${x}`} x1={x} y1={bounds.minY} x2={x} y2={bounds.maxY} stroke={colors.paperLine} strokeWidth={1} vectorEffect="non-scaling-stroke" />
        ))}
      </g>
    );
  }

  if (style === 'dot') {
    const startY = Math.floor(bounds.minY / PAPER_STEP) * PAPER_STEP;
    const startX = Math.floor(bounds.minX / PAPER_STEP) * PAPER_STEP;
    const dots = [];
    for (let y = startY; y < bounds.maxY; y += PAPER_STEP) {
      for (let x = startX; x < bounds.maxX; x += PAPER_STEP) dots.push({ x, y });
    }
    return (
      <g pointerEvents="none">
        {dots.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r={1.4} fill={colors.paperLine} />)}
      </g>
    );
  }

  // 'ruled' (par défaut) : lignes horizontales + marge, façon cahier.
  const lines = [];
  const start = Math.floor((bounds.minY - 34) / PAPER_STEP) * PAPER_STEP + 34;
  for (let y = start; y < bounds.maxY; y += PAPER_STEP) lines.push(y);
  return (
    <g pointerEvents="none">
      {lines.map((y) => (
        <line key={y} x1={bounds.minX} y1={y} x2={bounds.maxX} y2={y} stroke={colors.paperLine} strokeWidth={1} vectorEffect="non-scaling-stroke" />
      ))}
      <line x1={46.5} y1={bounds.minY} x2={46.5} y2={bounds.maxY} stroke={colors.paperMargin} strokeWidth={1} vectorEffect="non-scaling-stroke" />
    </g>
  );
}
