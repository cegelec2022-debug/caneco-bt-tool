import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getPublicFiche, publicFichePdfUrl } from "@/api/tableaux";
import type { FichePublic } from "@/types";

type State =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "ok"; fiche: FichePublic };

/**
 * Fiche tableau accessible par scan QR — page PUBLIQUE (sans authentification).
 * Optimisee mobile (consultation sur chantier), lecture seule.
 */
export default function FicheTableauPublic() {
  const { token } = useParams<{ token: string }>();
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    if (!token) {
      setState({ kind: "error" });
      return;
    }
    getPublicFiche(token)
      .then((fiche) => active && setState({ kind: "ok", fiche }))
      .catch(() => active && setState({ kind: "error" }));
    return () => {
      active = false;
    };
  }, [token]);

  return (
    <div className="min-h-screen bg-bg-light flex flex-col">
      {/* En-tete rouge VINCI / Cegelec */}
      <header
        className="px-5 py-4 text-white flex items-center justify-between"
        style={{ backgroundColor: "#C8102E" }}
      >
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide text-white/80">
            Cegelec — VINCI Energies
          </p>
          <h1 className="text-lg font-semibold truncate">
            Fiche tableau electrique
          </h1>
        </div>
        <img
          src="/logo-vinci.png"
          alt="VINCI Energies"
          className="h-9 object-contain shrink-0 ml-3 bg-white/95 rounded px-2 py-1"
        />
      </header>

      <main className="flex-1 p-4 sm:p-6 max-w-5xl w-full mx-auto">
        {state.kind === "loading" && (
          <p className="text-sm text-text-tertiary">Chargement de la fiche…</p>
        )}

        {state.kind === "error" && (
          <div className="border border-border-std rounded-lg bg-white p-8 text-center mt-8">
            <p className="text-sm font-medium text-text-primary mb-1">
              Lien invalide ou expire
            </p>
            <p className="text-xs text-text-tertiary">
              Ce QR code ne correspond a aucune fiche tableau. Contactez le
              bureau d'etudes.
            </p>
          </div>
        )}

        {state.kind === "ok" && <FicheContent fiche={state.fiche} token={token!} />}
      </main>

      <footer className="px-5 py-3 text-center text-xs text-text-tertiary border-t border-border-std">
        Valorisation des donnees CANECO BT — Document en lecture seule
      </footer>
    </div>
  );
}

function FicheContent({ fiche, token }: { fiche: FichePublic; token: string }) {
  return (
    <div className="space-y-5">
      {/* Identite du tableau */}
      <div className="bg-white border border-border-std rounded-lg p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-wide text-text-tertiary">
              Tableau
            </p>
            <h2
              className="text-2xl font-bold"
              style={{ color: "#001E50" }}
            >
              {fiche.repere}
            </h2>
            {fiche.designation && (
              <p className="text-sm text-text-secondary mt-0.5">
                {fiche.designation}
              </p>
            )}
          </div>
          <a
            href={publicFichePdfUrl(token)}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 inline-flex items-center gap-2 text-sm font-medium text-white px-4 py-2 rounded transition-colors"
            style={{ backgroundColor: "#001E50" }}
          >
            Voir le PDF
          </a>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 mt-4 text-xs text-text-tertiary">
          <span>
            Projet : <span className="text-text-secondary">{fiche.project_name}</span>
          </span>
          <span>
            Indice CANECO : <span className="text-text-secondary">{fiche.indice}</span>
          </span>
          <span>
            Departs : <span className="text-text-secondary">{fiche.nb_departs}</span>
          </span>
        </div>
      </div>

      {/* Fiche : sections thematiques (vertical, lecture client) */}
      {fiche.sections.length === 0 ? (
        <div className="bg-white border border-border-std rounded-lg px-4 py-8 text-center text-sm text-text-tertiary">
          Donnees indisponibles pour ce tableau dans l'export CANECO courant.
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {fiche.sections.map((section) => (
            <div
              key={section.title}
              className="bg-white border border-border-std rounded-lg overflow-hidden self-start"
            >
              <div
                className="px-4 py-2 text-white text-xs font-semibold uppercase tracking-wide"
                style={{ backgroundColor: "#001E50" }}
              >
                {section.title}
              </div>
              <dl className="divide-y divide-border-std">
                {section.rows.map((r) => (
                  <div
                    key={r.label}
                    className="flex items-start gap-3 px-4 py-2"
                  >
                    <dt className="text-xs text-text-tertiary w-1/2 shrink-0">
                      {r.label}
                    </dt>
                    <dd className="text-xs font-medium text-text-primary w-1/2 text-right break-words">
                      {r.value && r.value.trim() !== "" ? r.value : "—"}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
