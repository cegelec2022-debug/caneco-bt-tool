import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { login } from "@/api/auth";
import { useAuth } from "@/context/AuthContext";

const schema = z.object({
  email: z.string().email("Adresse email invalide"),
  password: z.string().min(1, "Mot de passe requis"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const { setToken } = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

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
        setServerError("Impossible de joindre le serveur. Vérifiez votre connexion.");
      }
    }
  }

  return (
    <div className="min-h-screen bg-bg-light flex flex-col">
      <header className="bg-vinci-blue text-white px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">
            Valorisation des données CANECO BT
          </h1>
          <p className="text-xs text-white/70">Actemium Cegelec — VINCI Energies</p>
        </div>
        <img src="/logo-vinci.png" alt="VINCI Energies" className="h-10 object-contain" />
      </header>

      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="w-8 h-1 bg-vinci-red mb-6" />
          <h2 className="text-xl font-semibold text-text-primary mb-1">Connexion</h2>
          <p className="text-sm text-text-tertiary mb-6">
            Entrez vos identifiants pour accéder à l'outil.
          </p>

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
                className={`w-full border rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-vinci-blue/30 transition-colors ${
                  errors.email
                    ? "border-status-warn focus:border-status-warn"
                    : "border-border-std focus:border-vinci-blue"
                }`}
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
                  className={`w-full border rounded px-3 py-2 pr-10 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-vinci-blue/30 transition-colors ${
                    errors.password
                      ? "border-status-warn focus:border-status-warn"
                      : "border-border-std focus:border-vinci-blue"
                  }`}
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

            {/* Bouton */}
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

          <p className="mt-8 text-center text-xs text-text-tertiary">
            Challenge Innovation VEAO 2026
          </p>
        </div>
      </main>
    </div>
  );
}
