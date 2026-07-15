import { NextResponse } from "next/server";
import { getProjects } from "@/lib/demo-data";

export const dynamic = "force-dynamic";

/**
 * In demo mode, sync is a no-op: the snapshot was generated at build time.
 * The frontend calls this on load and refresh; we return ok so it doesn't
 * error out.
 */
export async function POST() {
  const projects = getProjects();
  const name = projects[0]?.name ?? "demo";
  return NextResponse.json({ status: "ok", project: name });
}
