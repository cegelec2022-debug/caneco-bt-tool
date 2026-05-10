import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { login } from "@/api/auth";
import { useAuth } from "@/context/AuthContext";

const schema = z.object({
  email: z.string().email("Email invalide"),
  password: z.string().min(1, "Mot de passe requis"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const { setToken } = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);

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
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Erreur de connexion.";
      setServerError(msg);
    }
  }

  return (
    <div className="min-h-screen bg-bg-light flex flex-col">
      <header className="bg-vinci-blue text-white px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Valorisation des données CANECO BT</h1>
          <p className="text-xs text-white/70">Actemium Cegelec — VINCI Energies</p>
        </div>
        <img src="/logo-vinci.png" alt="VINCI Energies" className="h-10 object-contain" />
      </header>

      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="w-8 h-1 bg-vinci-red mb-6" />
          <h2 className="text-xl font-semibold text-text-primary mb-6">Connexion</h2>

          <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
            <div>
              <label className="block text-sm text-text-secondary mb-1" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                {...register("email")}
                className="w-full border border-border-std rounded px-3 py-2 text-sm focus:outline-none focus:border-vinci-blue"
              />
              {errors.email && (
                <p className="text-xs text-status-warn mt-1">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm text-text-secondary mb-1" htmlFor="password">
                Mot de passe
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register("password")}
                className="w-full border border-border-std rounded px-3 py-2 text-sm focus:outline-none focus:border-vinci-blue"
              />
              {errors.password && (
                <p className="text-xs text-status-warn mt-1">{errors.password.message}</p>
              )}
            </div>

            {serverError && (
              <p className="text-xs text-status-warn bg-red-50 border border-red-200 rounded px-3 py-2">
                {serverError}
              </p>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-vinci-blue text-white py-2 rounded text-sm font-medium hover:bg-vinci-blue/90 transition-colors disabled:opacity-50"
            >
              {isSubmitting ? "Connexion..." : "Se connecter"}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
