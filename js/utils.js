export function rand(min, max) {
  return Math.random() * (max - min) + min;
}

export function randInt(min, max) {
  return Math.floor(rand(min, max + 1));
}

export function choice(arr) {
  return arr[randInt(0, arr.length - 1)];
}

export function dist(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

export function lerp(a, b, t) {
  return a + (b - a) * t;
}

export function lerpPoint(a, b, t) {
  return { x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t) };
}

export function clamp(v, min, max) {
  return Math.min(max, Math.max(min, v));
}

export function pathForShape(ctx, shape, x, y, r) {
  ctx.beginPath();
  switch (shape) {
    case "circle":
      ctx.arc(x, y, r, 0, Math.PI * 2);
      break;
    case "square": {
      const s = r * 1.5;
      ctx.rect(x - s / 2, y - s / 2, s, s);
      break;
    }
    case "triangle": {
      const h = r * 1.6;
      ctx.moveTo(x, y - h * 0.62);
      ctx.lineTo(x + h * 0.62, y + h * 0.5);
      ctx.lineTo(x - h * 0.62, y + h * 0.5);
      ctx.closePath();
      break;
    }
    case "pentagon": {
      const n = 5;
      for (let i = 0; i < n; i++) {
        const a = -Math.PI / 2 + (i * 2 * Math.PI) / n;
        const px = x + r * 1.15 * Math.cos(a);
        const py = y + r * 1.15 * Math.sin(a);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      break;
    }
    case "diamond": {
      const s = r * 1.25;
      ctx.moveTo(x, y - s);
      ctx.lineTo(x + s, y);
      ctx.lineTo(x, y + s);
      ctx.lineTo(x - s, y);
      ctx.closePath();
      break;
    }
    default:
      ctx.arc(x, y, r, 0, Math.PI * 2);
  }
}
