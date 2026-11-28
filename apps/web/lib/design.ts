// Types for the editable base design model (ARCH-003). Numbers are metres on the parcel's
// local plane (X right, Y up). The API validates every edit and owns all state.

export type DesignElement = {
  id: string;
  type: "space" | "wall" | "door" | "window" | "opening" | "vertical";
  floor: number;
  locked: boolean;
  label?: string;
  // space
  kind?: string;
  name?: string;
  schedule_space_id?: string;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  rotation_deg?: number;
  floors?: number[];
  copied_from?: string;
  // wall
  x1?: number;
  y1?: number;
  x2?: number;
  y2?: number;
  thickness_m?: number;
  // door / window / opening
  wall_id?: string;
  offset_m?: number;
  width_m?: number;
  height_m?: number;
  sill_m?: number;
};

export type DesignModel = {
  schema: number;
  units: string;
  next_id: number;
  source: { kind: string; layout_version: number; alternative_id: string; strategy: string } | null;
  elements: DesignElement[];
};

export type DesignState = {
  exists: boolean;
  data: DesignModel | null;
  version: number;
  layout_changed: boolean;
  updated_at: string | null;
  can_undo?: boolean;
  can_redo?: boolean;
  history_position?: number;
  history_length?: number;
};

export type DesignHistoryEntry = {
  seq: number;
  summary: { action: string; operations?: { op: string; id?: string }[]; unit?: string; snap?: { grid: number; unit?: string } | null };
  actor: string;
  created_at: string | null;
  current: boolean;
};

export type DesignHistory = { position: number; entries: DesignHistoryEntry[] };

export type LengthUnit = "m" | "cm" | "mm";

// Display factor from metres (the stored unit) to the unit chosen in the panel.
export const unitFactors: Record<LengthUnit, number> = { m: 1, cm: 100, mm: 1000 };
export const unitNames: Record<LengthUnit, string> = { m: "متر", cm: "سانتی‌متر", mm: "میلی‌متر" };
export const snapChoices: Record<LengthUnit, number[]> = { m: [0.1, 0.25, 0.5, 1], cm: [1, 5, 10, 25, 50], mm: [1, 5, 10, 50, 100] };

export const operationLabels: Record<string, string> = {
  add: "افزودن", move: "جابه‌جایی", resize: "تغییر اندازه", rotate: "چرخش", delete: "حذف", copy_floor: "کپی طبقه", set_floors: "طبقه‌های ارتباط", lock: "قفل", unlock: "باز کردن قفل", set: "تنظیم",
};

export type DesignOperation = Record<string, unknown>;

export const typeLabels: Record<DesignElement["type"], string> = {
  space: "فضا",
  wall: "دیوار",
  door: "در",
  window: "پنجره",
  opening: "بازشو",
  vertical: "ارتباط عمودی",
};

export const verticalKinds: Record<string, string> = { stair: "پله", elevator: "آسانسور", shaft: "شفت" };

export function wallLength(wall: DesignElement): number {
  return Math.hypot((wall.x2 ?? 0) - (wall.x1 ?? 0), (wall.y2 ?? 0) - (wall.y1 ?? 0));
}

export type AiStatus = { enabled: boolean; model: string | null };

export type AiProposal = {
  base_version: number;
  model: string;
  summary: string;
  operations: DesignOperation[];
  valid: boolean;
  error: { code: string; operation_index: number | null; element_id: string | null } | null;
  attempts: number;
};
