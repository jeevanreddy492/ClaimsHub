import type { ClaimStatus, LeaveStatus, Role } from "./types";

// Mirrors backend/app/domain/claim_rules.py so the UI only offers valid actions.
// The server still checks everything; this is only for a better screen.
export const CLAIM_TRANSITIONS: Record<ClaimStatus, ClaimStatus[]> = {
  RECEIVED: ["IN_REVIEW"],
  IN_REVIEW: ["APPROVED", "DENIED"],
  APPROVED: ["CLOSED"],
  DENIED: ["APPEALED", "CLOSED"],
  APPEALED: ["IN_REVIEW"],
  CLOSED: [],
};

const SUPERVISOR_ONLY: ClaimStatus[] = ["APPROVED", "DENIED"];

export function allowedClaimMoves(current: ClaimStatus, role: Role): ClaimStatus[] {
  if (role === "VIEWER") return [];
  return CLAIM_TRANSITIONS[current].filter((s) => role === "SUPERVISOR" || !SUPERVISOR_ONLY.includes(s));
}

export const LEAVE_TRANSITIONS: Record<LeaveStatus, LeaveStatus[]> = {
  REQUESTED: ["APPROVED", "DENIED", "CANCELLED"],
  APPROVED: ["CANCELLED"],
  DENIED: [],
  CANCELLED: [],
};

export const canWrite = (role: Role | undefined): boolean => role === "ADJUSTER" || role === "SUPERVISOR";

export function sharesTotal(shares: string[]): number {
  // Work in cents to avoid floating point surprises (33.33 + 33.33 + 33.34 = 100).
  return shares.reduce((sum, s) => sum + Math.round((parseFloat(s) || 0) * 100), 0) / 100;
}

export function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  return Number(value).toLocaleString("en-US", { style: "currency", currency: "USD" });
}

export function label(value: string): string {
  return value.replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
}
