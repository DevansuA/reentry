/** TypeScript types mirroring the Python data structures returned by the API. */

export interface CapsuleItem {
  text: string;
  evidence_ids: string[];
  inference: "observed" | "inferred" | "user_corrected";
  confidence: number;
  rationale?: string;
  classification?: string;
  due_at?: string;
  observed_at?: string;
  /** Set only on next_action items. */
  action_id?: string;
  command?: string;
  risk?: string;
}

export interface EntropyFactor {
  factor: string;
  value: number;
  points: number;
  how_to_reduce: string;
}

export interface EntropyResult {
  score: number;
  label: "low" | "moderate" | "high";
  breakdown: EntropyFactor[];
}

export interface PendingAction {
  id: string;
  title: string;
  command: string;
  risk: string;
  status: string;
  resolves_claim: string | null;
  result: string | null;
}

export interface Capsule {
  project: string;
  generated_at: string;
  objective: CapsuleItem | null;
  where_things_stand: CapsuleItem[];
  what_changed: CapsuleItem[];
  decisions: CapsuleItem[];
  blockers: CapsuleItem[];
  contradictions: CapsuleItem[];
  deadlines: CapsuleItem[];
  next_action: CapsuleItem | null;
  pending_actions: PendingAction[];
  entropy: EntropyResult;
}

export interface LedgerEvent {
  id: string;
  project_id: string;
  source: string;
  event_type: string;
  occurred_at: string;
  ingested_at: string;
  actor: string | null;
  payload: string;
  sensitivity: string;
}

export interface Project {
  id: string;
  name: string;
  root_path: string;
  created_at: string;
}
