// Types match the FastAPI response models (backend/app/schemas).

export type Role = "ADJUSTER" | "SUPERVISOR" | "VIEWER";
export type ClaimStatus = "RECEIVED" | "IN_REVIEW" | "APPROVED" | "DENIED" | "APPEALED" | "CLOSED";
export type ClaimType = "STD" | "LIFE";
export type LeaveStatus = "REQUESTED" | "APPROVED" | "DENIED" | "CANCELLED";

export interface Session {
  access_token: string;
  username: string;
  role: Role;
  full_name: string;
  expires_at: number;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Employer {
  employer_id: number;
  name: string;
  created_at: string;
}

export interface Policy {
  policy_id: number;
  policy_number: string;
  employer_id: number;
  product_type: ClaimType;
  benefit_pct: string | null;
  max_weekly_benefit: string | null;
  elimination_days: number | null;
  max_benefit_weeks: number | null;
  face_amount: string | null;
  effective_date: string;
}

export interface Claimant {
  claimant_id: number;
  employer_id: number;
  employee_number: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  hire_date: string;
  weekly_salary: string;
  email: string | null;
  created_at: string;
}

export interface ClaimSummary {
  claim_id: number;
  claim_number: string;
  claim_type: ClaimType;
  status: ClaimStatus;
  claimant_id: number;
  policy_id: number;
  received_date: string;
  assigned_to: string | null;
  version: number;
  updated_at: string;
}

export interface Payment {
  payment_id: number;
  beneficiary_id: number | null;
  period_start: string | null;
  period_end: string | null;
  amount: string;
  status: string;
  created_at: string;
}

export interface ClaimDetail extends ClaimSummary {
  closed_date: string | null;
  created_by: string;
  created_at: string;
  std_detail: {
    disability_start_date: string;
    condition_category: string;
    elimination_days: number;
    weekly_benefit: string | null;
    benefit_start_date: string | null;
    return_to_work_date: string | null;
  } | null;
  life_detail: { date_of_death: string; cause_category: string; payout_amount: string } | null;
  beneficiaries: { beneficiary_id: number; full_name: string; relationship: string; share_pct: string }[];
  history: { from_status: string | null; to_status: string; reason: string | null; changed_by: string; changed_at: string }[];
  payments: Payment[];
}

export interface ClaimStats {
  by_status: Partial<Record<ClaimStatus, number>>;
  by_type: Partial<Record<ClaimType, number>>;
  total: number;
}

export interface Leave {
  leave_id: number;
  claimant_id: number;
  leave_type: "FMLA" | "MEDICAL" | "PERSONAL";
  start_date: string;
  end_date: string | null;
  status: LeaveStatus;
  linked_claim_id: number | null;
  reason: string | null;
  created_by: string;
  created_at: string;
  version: number;
}
