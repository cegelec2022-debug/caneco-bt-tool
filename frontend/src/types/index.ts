export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "BE" | "chef_chantier" | "RA" | "admin";
  is_active: boolean;
  created_at: string;
}

export interface Project {
  id: string;
  code: string;
  name: string;
  client: string | null;
  agency: string | null;
  description: string | null;
  status: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface ProjectCreate {
  code: string;
  name: string;
  client?: string;
  agency?: string;
  description?: string;
  status?: string;
}

export interface ProjectUpdate {
  name?: string;
  client?: string;
  agency?: string;
  description?: string;
  status?: string;
}
