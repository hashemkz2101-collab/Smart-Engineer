// Saved design versions, comparison and comments (ARCH-006). The API owns all state.

import type { DesignElement } from "./design";

export type VersionMeta = {
  number: number;
  label: string;
  model_version: number;
  element_count: number;
  author: string | null;
  created_at: string | null;
  comment_count: number;
};

export type VersionList = { versions: VersionMeta[] };

export type DesignComment = {
  id: string;
  element_id: string | null;
  body: string;
  author: string | null;
  version_number: number;
  created_at: string | null;
};

export type VersionDetail = VersionMeta & {
  data: { elements: DesignElement[] };
  comments: DesignComment[];
};

export type FieldChange = { field: string; before: unknown; after: unknown };

export type Comparison = {
  from: { number: number | null; label: string | null; model_version: number };
  to: { number: number | null; label: string | null; model_version: number };
  added: DesignElement[];
  removed: DesignElement[];
  changed: { id: string; type: DesignElement["type"]; floor: number; fields: FieldChange[] }[];
  unchanged: number;
  summary: { added: number; removed: number; changed: number };
};

export function sideLabel(side: Comparison["from"]): string {
  return side.number === null ? "طرح فعلی" : `نسخهٔ ${side.number.toLocaleString("fa-IR")} — ${side.label ?? ""}`;
}

export function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "بله" : "خیر";
  if (typeof value === "number") return value.toLocaleString("fa-IR", { maximumFractionDigits: 3 });
  return typeof value === "string" ? value : JSON.stringify(value);
}
