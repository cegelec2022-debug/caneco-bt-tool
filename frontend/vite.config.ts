import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Domaines de tunnel temporaire (ngrok / Pinggy) autorises pour les
// demonstrations. L'API passe par le proxy ci-dessous, donc une seule URL
// suffit. Partage entre le serveur de dev et le serveur de preview (build).
const tunnelAllowedHosts = [
  ".trycloudflare.com",
  ".ngrok-free.app",
  ".ngrok-free.dev",
  ".ngrok.app",
  ".ngrok.io",
  ".loca.lt",
  ".pinggy.link",
  ".pinggy.online",
  ".pinggy.io",
  ".pinggy-free.link",
];

// Proxy de l'API vers le backend (memes regles en dev et en preview).
const apiProxy = {
  "/api": {
    target: "http://backend:8000",
    changeOrigin: true,
  },
};

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    allowedHosts: tunnelAllowedHosts,
    watch: {
      usePolling: true,
      interval: 1000,
    },
    proxy: apiProxy,
  },
  // Mode "preview" : sert le build de production (rapide a distance, ideal
  // pour le pitch via tunnel). Vite preview n'herite pas du bloc server,
  // d'ou la duplication explicite du host / proxy / allowedHosts.
  preview: {
    host: "0.0.0.0",
    port: 5173,
    allowedHosts: tunnelAllowedHosts,
    proxy: apiProxy,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/__tests__/setup.ts"],
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
