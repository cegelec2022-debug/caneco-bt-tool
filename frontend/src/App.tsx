import { Route, Routes } from "react-router-dom";

function HomePage() {
  return (
    <div className="min-h-screen bg-bg-light flex flex-col">
      <header className="bg-vinci-blue text-white px-6 py-4 flex items-center gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">
            Valorisation des données CANECO BT
          </h1>
          <p className="text-xs text-white/70">Actemium Cegelec — VINCI Energies</p>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-lg text-center">
          <div className="w-12 h-1 bg-vinci-red mx-auto mb-6" />
          <h2 className="text-2xl font-semibold text-text-primary mb-3">
            Mise en place du squelette technique
          </h2>
          <p className="text-text-secondary text-sm leading-relaxed">
            Le squelette technique est en place. Coller le Bloc 2 du fichier{" "}
            <code className="bg-bg-cell px-1 rounded text-xs">PROMPT_CLAUDE_CODE.md</code> pour
            démarrer le développement des fonctionnalités V1.
          </p>
          <div className="mt-6 text-xs text-text-tertiary">
            Challenge Innovation VEAO 2026 — Version 0.1.0-dev
          </div>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
    </Routes>
  );
}
