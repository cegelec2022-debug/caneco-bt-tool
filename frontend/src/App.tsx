import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "@/components/Layout";
import ProtectedRoute from "@/components/ProtectedRoute";
import { AuthProvider } from "@/context/AuthContext";
import FicheTableauPublic from "@/pages/FicheTableauPublic";
import LoginPage from "@/pages/LoginPage";
import ProjectPage from "@/pages/ProjectPage";
import ProjectsPage from "@/pages/ProjectsPage";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Route PUBLIQUE — fiche tableau par scan QR, sans authentification */}
        <Route path="/t/:token" element={<FicheTableauPublic />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/projects" replace />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="projects/:id" element={<ProjectPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
