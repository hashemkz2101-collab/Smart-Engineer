// Types for the editable base design model (ARCH-003). Numbers are metres on the parcel's
// local plane (X right, Y up). The API validates every edit and owns all state.

export type DesignElement = {
  id: string;
  type: "space" | "wall" | "door" | "window" | "opening";
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
};

export type DesignOperation = Record<string, unknown>;

export const typeLabels: Record<DesignElement["type"], string> = {
  space: "فضا",
  wall: "دیوار",
  door: "در",
  window: "پنجره",
  opening: "بازشو",
};

export function wallLength(wall: DesignElement): number {
  return Math.hypot((wall.x2 ?? 0) - (wall.x1 ?? 0), (wall.y2 ?? 0) - (wall.y1 ?? 0));
}
