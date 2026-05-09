import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Charte VINCI Energies / Cegelec — PRD section 7.1
        "vinci-red": "#C8102E",
        "vinci-blue": "#001E50",
        "text-primary": "#1A1A1A",
        "text-secondary": "#374151",
        "text-tertiary": "#6B7280",
        "bg-light": "#FAFAFA",
        "bg-cell": "#F5F5F5",
        "border-std": "#BFBFBF",
        "status-ok": "#16A34A",
        "status-warn": "#EA580C",
        "status-info": "#FEF3C7",
      },
      fontFamily: {
        sans: ["Inter", "Calibri", "Arial", "sans-serif"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
