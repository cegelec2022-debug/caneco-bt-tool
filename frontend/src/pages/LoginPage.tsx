import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronDown, Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { login } from "@/api/auth";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

const schema = z.object({
  email: z.string().email("Adresse email invalide"),
  password: z.string().min(1, "Mot de passe requis"),
});

type FormData = z.infer<typeof schema>;

const DEMO_ACCOUNTS = [
  {
    label: "Administrateur",
    name: "Administrateur Actemium",
    email: "admin@actemium.fr",
    role: "Accès complet",
    color: "bg-vinci-blue text-white",
  },
  {
    label: "Bureau d'Etudes",
    name: "Mouhcine Zekraoui",
    email: "be@actemium.fr",
    role: "Ses propres projets",
    color: "bg-blue-50 text-blue-700",
  },
  {
    label: "Chef de Chantier",
    name: "Mouad",
    email: "chef@actemium.fr",
    role: "Ses propres projets",
    color: "bg-orange-50 text-orange-700",
  },
  {
    label: "Responsable Affaires",
    name: "Mariam Jibrane",
    email: "ra@actemium.fr",
    role: "Tous les projets + tableau de bord",
    color: "bg-green-50 text-green-700",
  },
] as const;

export default function LoginPage() {
  const { setToken } = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showDemo, setShowDemo] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(data: FormData) {
    setServerError(null);
    try {
      const resp = await login(data);
      setToken(resp.access_token);
      navigate("/projects");
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 401) {
        setServerError("Email ou mot de passe incorrect.");
      } else if (status === 403) {
        setServerError("Votre compte est désactivé. Contactez l'administrateur.");
      } else {
        setServerError("Impossible de joindre le serveur. Vérifiez votre connexion réseau.");
      }
    }
  }

  function fillAccount(email: string) {
    reset(
      { email, password: "Demo2026!" },
      { keepErrors: false, keepDirty: false }
    );
  }

  return (
    <div className="min-h-screen bg-bg-light flex flex-col">
      {/* Header */}
      <header className="bg-vinci-blue text-white px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">
            Valorisation des données CANECO BT
          </h1>
          <p className="text-xs text-white/70">Actemium Cegelec — VINCI Energies</p>
        </div>
        <img src="/logo-vinci.png" alt="VINCI Energies" className="h-10 object-contain" />
      </header>

      <main
        className="relative flex-1 flex items-center justify-center bg-vinci-blue bg-cover bg-center p-6"
        style={{ backgroundImage: "url('/vinci-login-bg.webp')" }}
      >
        {/* Voile sombre VINCI pour garder le formulaire lisible par-dessus la photo */}
        <div className="absolute inset-0 bg-vinci-blue/40" aria-hidden="true" />

        <div className="relative w-full max-w-sm rounded-lg border border-border-std bg-white p-8 shadow-2xl">
          <div className="w-8 h-1 bg-vinci-red mb-6" />
          <h2 className="text-xl font-semibold text-text-primary mb-1">Connexion</h2>
          <p className="text-sm text-text-tertiary mb-6">
            Entrez vos identifiants pour accéder à l'outil.
          </p>

          {/* Formulaire */}
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
            {/* Email */}
            <div>
              <label
                className="block text-sm font-medium text-text-secondary mb-1"
                htmlFor="email"
              >
                Email professionnel
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                autoFocus
                placeholder="prenom.nom@actemium.fr"
                {...register("email")}
                aria-invalid={!!errors.email}
                aria-describedby={errors.email ? "email-error" : undefined}
                className={cn(
                  "w-full border rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-vinci-blue/30 transition-colors",
                  errors.email
                    ? "border-status-warn focus:border-status-warn"
                    : "border-border-std focus:border-vinci-blue"
                )}
              />
              {errors.email && (
                <p id="email-error" role="alert" className="text-xs text-status-warn mt-1">
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Mot de passe */}
            <div>
              <label
                className="block text-sm font-medium text-text-secondary mb-1"
                htmlFor="password"
              >
                Mot de passe
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  {...register("password")}
                  aria-invalid={!!errors.password}
                  aria-describedby={errors.password ? "password-error" : undefined}
                  className={cn(
                    "w-full border rounded px-3 py-2 pr-10 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-vinci-blue/30 transition-colors",
                    errors.password
                      ? "border-status-warn focus:border-status-warn"
                      : "border-border-std focus:border-vinci-blue"
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                  className="absolute inset-y-0 right-0 flex items-center px-3 text-text-tertiary hover:text-text-secondary transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.password && (
                <p id="password-error" role="alert" className="text-xs text-status-warn mt-1">
                  {errors.password.message}
                </p>
              )}
            </div>

            {/* Erreur serveur */}
            {serverError && (
              <div
                role="alert"
                className="flex items-start gap-2 text-xs text-status-warn bg-red-50 border border-red-200 rounded px-3 py-2"
              >
                <span className="mt-0.5 shrink-0">&#9888;</span>
                <span>{serverError}</span>
              </div>
            )}

            {/* Bouton connexion */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-vinci-blue text-white py-2.5 rounded text-sm font-medium hover:bg-vinci-blue/90 active:scale-[0.99] transition-all disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Connexion en cours...
                </>
              ) : (
                "Se connecter"
              )}
            </button>
          </form>

          {/* Section démo */}
          <div className="mt-8 border border-border-std rounded overflow-hidden">
            <button
              type="button"
              onClick={() => setShowDemo((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-3 text-xs font-medium text-text-secondary bg-bg-cell hover:bg-bg-cell/80 transition-colors"
            >
              <span>Comptes de démonstration</span>
              <ChevronDown
                size={14}
                className={cn("transition-transform", showDemo && "rotate-180")}
              />
            </button>

            {showDemo && (
              <div className="divide-y divide-border-std">
                {DEMO_ACCOUNTS.map((account) => (
                  <button
                    key={account.email}
                    type="button"
                    onClick={() => fillAccount(account.email)}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-bg-light transition-colors group"
                  >
                    <span
                      className={cn(
                        "text-xs font-medium px-2 py-0.5 rounded shrink-0",
                        account.color
                      )}
                    >
                      {account.label}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-text-primary truncate">
                        {account.name}
                      </p>
                      <p className="text-xs text-text-tertiary truncate">{account.email}</p>
                    </div>
                    <span className="text-xs text-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      Remplir
                    </span>
                  </button>
                ))}
                <div className="px-4 py-2 bg-status-info">
                  <p className="text-xs text-yellow-700">
                    Mot de passe commun : <span className="font-mono font-semibold">Demo2026!</span>
                  </p>
                </div>
              </div>
            )}
          </div>

          <p className="mt-6 text-center text-xs text-text-tertiary">
            Challenge Innovation VEAO 2026
          </p>
        </div>
      </main>
    </div>
  );
}
