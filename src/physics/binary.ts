/**
 * Stabilité des planètes dans les systèmes doubles, d'après les ajustements
 * numériques de Holman & Wiegert (1999).
 *  - type S : la planète tourne autour d'une seule étoile ; elle est stable
 *    tant que son demi-grand axe reste sous `sTypeCriticalAu`.
 *  - type P (circumbinaire) : elle tourne autour des deux ; stable au-delà de `pTypeCriticalAu`.
 * `mu` = m₂ / (m₁ + m₂), où m₂ est la masse de l'étoile qui perturbe.
 */
export function sTypeCriticalAu(binaryA: number, binaryE: number, mu: number): number {
  const e = binaryE;
  return binaryA * (0.464 - 0.38 * mu - 0.631 * e + 0.586 * mu * e + 0.15 * e * e - 0.198 * mu * e * e);
}

export function pTypeCriticalAu(binaryA: number, binaryE: number, mu: number): number {
  const e = binaryE;
  return (
    binaryA *
    (1.6 + 5.1 * e - 2.22 * e * e + 4.12 * mu - 4.27 * e * mu - 5.09 * mu * mu + 4.61 * e * e * mu * mu)
  );
}
