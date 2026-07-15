import { NextRequest, NextResponse } from "next/server";
import { getBeforeActions } from "@/lib/demo-data";

export const dynamic = "force-dynamic";

/**
 * Simulated approve in demo mode.
 *
 * Returns the action with status "verified (simulated)". The frontend
 * then calls GET /api/capsule?state=after to show the post-approval state.
 * The word "simulated" appears in both the returned status and the action
 * panel UI so users understand this is a pre-recorded transition, not
 * live execution.
 */
export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const actions = getBeforeActions();
  const action = actions.find((a) => a.id === id);
  if (!action) {
    return NextResponse.json({ detail: "Action not found." }, { status: 404 });
  }
  return NextResponse.json({
    ...action,
    status: "verified (simulated)",
    approved_at: new Date().toISOString(),
    executed_at: new Date().toISOString(),
    result: JSON.stringify({
      exit_code: 0,
      stdout: "2 passed in 0.31s (simulated)",
      stderr: "",
      timed_out: false,
      simulated: true,
    }),
  });
}
