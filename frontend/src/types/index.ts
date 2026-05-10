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

export interface CanecoExport {
  id: string;
  project_id: string;
  indice: string;
  file_name: string;
  status: "parsing" | "parsed" | "error";
  line_count: number | null;
  uploaded_by: string | null;
  uploaded_at: string;
}

export interface CanecoLine {
  id: string;
  export_id: string;
  row_index: number;
  repere: string | null;
  designation: string | null;
  style: string | null;
  nb_recepteurs: number | null;
  consommation: number | null;
  ib: number | null;
  longueur: number | null;
  type_cable: string | null;
  cable: string | null;
  neutre: string | null;
  pe: string | null;
  ame: string | null;
  calibre: number | null;
  bloc_coupure: string | null;
  bloc_declencheur: string | null;
  bloc_differentiel: string | null;
  ir_th_in: number | null;
  ir_mg_in: number | null;
  icu: number | null;
  extra_data: string | null;
}

export interface CanecoExportDetail {
  export: CanecoExport;
  lines: CanecoLine[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
