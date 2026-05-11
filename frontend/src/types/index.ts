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
  lines_read: number | null;
  columns_detected: number | null;
  columns_mapped: number | null;
  extra_columns_count: number | null;
  uploaded_by: string | null;
  uploaded_at: string;
}

export interface CanecoLine {
  id: string;
  export_id: string;
  excel_row_number: number | null;
  row_index: number;
  // 23 colonnes standard CANECO BT
  amont: string | null;
  repere_aval: string | null;
  repere: string | null;
  designation: string | null;
  style: string | null;
  nb_recepteurs: number | null;
  consommation: string | null;
  ib: number | null;
  longueur: number | null;
  type_cable: string | null;
  nb_cables_multi: number | null;
  cable: string | null;
  neutre: string | null;
  pe: string | null;
  calibre: number | null;
  bloc_coupure: string | null;
  bloc_declencheur: string | null;
  bloc_differentiel: string | null;
  ir_th_in: number | null;
  ir_mg_in: number | null;
  icu: number | null;
  contacteur: string | null;
  ame: string | null;
  // Valeurs brutes : { nom_champ: valeur_brute_excel }
  raw_data: Record<string, string> | null;
  // Colonnes supplementaires non standard
  extra_columns: Record<string, string> | null;
}

export interface CanecoExportDetail {
  export: CanecoExport;
  lines: CanecoLine[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface BordereauImport {
  id: string;
  project_id: string;
  file_name: string;
  indice: string | null;
  status: "uploaded" | "parsing" | "parsed" | "error";
  total_lines: number | null;
  total_articles: number | null;
  sections_count: number | null;
  error_message: string | null;
  created_at: string;
  created_by_id: string | null;
}

export interface BordereauSection {
  id: string;
  bordereau_import_id: string;
  code: string;
  title: string | null;
  excel_row_number: number | null;
  order_index: number;
}

export interface BordereauLine {
  id: string;
  bordereau_import_id: string;
  section_id: string | null;
  excel_row_number: number | null;
  num_prix: string | null;
  designation: string | null;
  unite: string | null;
  quantite: number | null;
  quantite_raw: string | null;
  sous_famille: string | null;
  detected_section_mm2: string | null;
  detected_material: string | null;
  detected_cable_type: string | null;
  detected_kind: string | null;
}

export interface BordereauDetail {
  imp: BordereauImport;
  sections: BordereauSection[];
  lines: BordereauLine[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
