import { NextRequest, NextResponse } from "next/server";
import { getBeforeCapsule, getAfterCapsule } from "@/lib/demo-data";

export const dynamic = "force-dynamic";

/**
 * In demo mode this route serves the pre-generated snapshot.
 * Pass ?state=after to get the post-approval capsule.
 */
export async function GET(req: NextRequest) {
  const state = req.nextUrl.searchParams.get("state");
  const cap = state === "after" ? getAfterCapsule() : getBeforeCapsule();
  return NextResponse.json(cap);
}
