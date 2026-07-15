import type { Capsule, LedgerEvent, PendingAction, Project } from "./types";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`/api${path}`, options);
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore parse error
    }
    throw new ApiError(resp.status, detail);
  }
  return resp.json() as Promise<T>;
}

export async function getCapsule(projectId?: string): Promise<Capsule> {
  const q = projectId
    ? `?project_id=${encodeURIComponent(projectId)}`
    : "";
  return request<Capsule>(`/capsule${q}`);
}

export async function getEvidence(eventId: string): Promise<LedgerEvent> {
  return request<LedgerEvent>(`/evidence/${eventId}`);
}

export async function approveAction(
  actionId: string,
  run = true,
): Promise<PendingAction> {
  return request<PendingAction>(
    `/actions/${actionId}/approve?run=${run}`,
    { method: "POST" },
  );
}

export async function rejectAction(actionId: string): Promise<PendingAction> {
  return request<PendingAction>(`/actions/${actionId}/reject`, {
    method: "POST",
  });
}

export async function listProjects(): Promise<Project[]> {
  return request<Project[]>("/projects");
}
