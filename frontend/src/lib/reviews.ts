export type Cell = { text: string; rowspan: string; colspan: string };
export type ParsedDocument = {
  sections: {
    title: string;
    paragraphs: { text: string; location: string; page: number | null }[];
  }[];
  references: { text: string; location: string; doi: string | null }[];
  tables: {
    caption: string;
    location: string;
    header: string[][];
    rows: Cell[][];
    needs_review: boolean;
  }[];
};
export type Review = {
  id: string;
  original_doi: string;
  original_title: string;
  original_authors: {
    fullName?: string;
    first_name?: string;
    last_name?: string;
  }[];
  journal: string | null;
  year: number | null;
  license: string | null;
  status: string;
  progress: number;
  stage: string;
  error_message: string | null;
  warnings: string[];
  document?: ParsedDocument | null;
  duplicate?: boolean;
};
export const stateLabel: Record<string, string> = {
  queued: "Esperando lectura",
  resolving: "Comprobando acceso abierto",
  parsing: "Leyendo el documento",
  license_review: "Licencia por confirmar",
  parsed: "Documento leído",
  failed: "Necesita atención",
};
