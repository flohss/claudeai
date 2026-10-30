import { useEffect, useRef } from 'react';
import { SceneRenderer, type ViewOptions } from '../render/SceneRenderer';
import type { Simulation } from '../sim/Simulation';

interface Props {
  sim: Simulation;
  selectedId: string | null;
  options: ViewOptions;
  onPick: (id: string | null) => void;
  onReady: (renderer: SceneRenderer | null) => void;
}

/** Monte le rendu Three.js et fait tourner la boucle simulation + affichage. */
export function SceneView({ sim, selectedId, options, onPick, onReady }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Les valeurs lues dans la boucle d'animation passent par des refs pour éviter de la recréer.
  const live = useRef({ selectedId, options, onPick });
  live.current = { selectedId, options, onPick };

  useEffect(() => {
    const renderer = new SceneRenderer(containerRef.current!, (id) => live.current.onPick(id));
    renderer.frameSystem(sim.bodies);
    onReady(renderer);
    let frame = 0;
    let last = performance.now();
    const loop = (now: number) => {
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      sim.advance(dt);
      renderer.update(sim.bodies, live.current.selectedId, live.current.options, sim.events, sim.epoch);
      renderer.render();
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(frame);
      onReady(null);
      renderer.dispose();
    };
  }, [sim, onReady]);

  return <div className="scene" ref={containerRef} />;
}
