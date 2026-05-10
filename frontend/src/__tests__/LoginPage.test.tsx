import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as authApi from "@/api/auth";
import { AuthProvider } from "@/context/AuthContext";
import LoginPage from "@/pages/LoginPage";

function renderLoginPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.spyOn(authApi, "getMe").mockRejectedValue(new Error("No token"));
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("renders email and password fields", () => {
    renderLoginPage();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/mot de passe/i)).toBeInTheDocument();
  });

  it("shows validation error on empty submit", async () => {
    renderLoginPage();
    await userEvent.click(screen.getByRole("button", { name: /se connecter/i }));
    await waitFor(() => {
      expect(screen.getByText(/email invalide/i)).toBeInTheDocument();
    });
  });

  it("shows server error on invalid credentials", async () => {
    vi.spyOn(authApi, "login").mockRejectedValue({
      response: { data: { detail: "Identifiants invalides." } },
    });
    renderLoginPage();
    await userEvent.type(screen.getByLabelText(/email/i), "bad@test.fr");
    await userEvent.type(screen.getByLabelText(/mot de passe/i), "wrongpass");
    await userEvent.click(screen.getByRole("button", { name: /se connecter/i }));
    await waitFor(() => {
      expect(screen.getByText(/identifiants invalides/i)).toBeInTheDocument();
    });
  });
});
