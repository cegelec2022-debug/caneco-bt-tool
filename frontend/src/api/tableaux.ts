import type { FichePublic, Tableau, TableauxGenerateResult } from "@/types";
import api from "./client";

export async function listTableaux(projectId: string): Promise<Tableau[]> {
  const { data } = await api.get<Tableau[]>(`/projects/${projectId}/tableaux`);
  return data;
}

export async function generateTableaux(
  projectId: string,
  canecoExportId: string
): Promise<TableauxGenerateResult> {
  const { data } = await api.post<TableauxGenerateResult>(
    `/projects/${projectId}/tableaux/generate`,
    null,
    { params: { caneco_export_id: canecoExportId } }
  );
  return data;
}

/** Origine publique a encoder dans le QR (URL ngrok en demo, localhost en dev). */
export function publicOrigin(): string {
  return window.location.origin;
}

/** URL publique de la fiche (a afficher / copier / coller dans un QR). */
export function publicFicheUrl(token: string): string {
  return `${publicOrigin()}/t/${token}`;
}

/** Recupere le QR PNG (endpoint authentifie) sous forme d'objectURL affichable. */
export async function fetchTableauQrObjectUrl(
  projectId: string,
  tableauId: string
): Promise<string> {
  const { data } = await api.get(
    `/projects/${projectId}/tableaux/${tableauId}/qr.png`,
    { params: { base_url: publicOrigin() }, responseType: "blob" }
  );
  return URL.createObjectURL(data as Blob);
}

async function downloadBlob(url: string, params: Record<string, string>, fallback: string) {
  const response = await api.get(url, { params, responseType: "blob" });
  const cd = response.headers["content-disposition"] as string | undefined;
  let filename = fallback;
  if (cd) {
    const m = cd.match(/filename="([^"]+)"/);
    if (m) filename = m[1];
  }
  const objectUrl = URL.createObjectURL(response.data as Blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(objectUrl);
}

export async function downloadLabelsPdf(projectId: string): Promise<void> {
  await downloadBlob(
    `/projects/${projectId}/tableaux/labels.pdf`,
    { base_url: publicOrigin() },
    "etiquettes-tableaux.pdf"
  );
}

export async function downloadFichePdf(
  projectId: string,
  tableauId: string
): Promise<void> {
  await downloadBlob(
    `/projects/${projectId}/tableaux/${tableauId}/fiche.pdf`,
    {},
    "fiche-tableau.pdf"
  );
}

/**
 * Fiche publique : appel SANS authentification (fetch direct, pas le client
 * axios qui ajoute le token et redirige vers /login sur 401).
 */
export async function getPublicFiche(token: string): Promise<FichePublic> {
  const resp = await fetch(`/api/t/${encodeURIComponent(token)}`, {
    headers: { Accept: "application/json" },
  });
  if (!resp.ok) {
    throw new Error(resp.status === 404 ? "introuvable" : "erreur");
  }
  return (await resp.json()) as FichePublic;
}

export function publicFichePdfUrl(token: string): string {
  return `/api/t/${encodeURIComponent(token)}/fiche.pdf`;
}
