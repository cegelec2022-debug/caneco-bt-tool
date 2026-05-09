/**
 * Constantes de couleur VINCI Energies / Cegelec — PRD section 7.1
 * Utiliser ces constantes pour les styles dynamiques (charts, PDF, génération).
 * Pour les classes Tailwind, utiliser les noms définis dans tailwind.config.ts.
 */
export const COLORS = {
  vinciRed: "#C8102E",
  vinciBlue: "#001E50",
  textPrimary: "#1A1A1A",
  textSecondary: "#374151",
  textTertiary: "#6B7280",
  bgLight: "#FAFAFA",
  bgCell: "#F5F5F5",
  borderStd: "#BFBFBF",
  statusOk: "#16A34A",
  statusWarn: "#EA580C",
  statusInfo: "#FEF3C7",
} as const;

export type ColorKey = keyof typeof COLORS;

/** Mapping criticité → couleur pour les badges d'écarts */
export const GAP_SEVERITY_COLORS: Record<string, string> = {
  BLOQUANT: COLORS.vinciRed,
  A_CORRIGER: COLORS.statusWarn,
  A_SIGNALER: "#CA8A04",
  INFORMATION: COLORS.textTertiary,
  INFO: COLORS.textTertiary,
};
