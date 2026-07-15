import { NextRequest, NextResponse } from "next/server";
import { getEvidence } from "@/lib/demo-data";

export const dynamic = "force-dynamic";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const ev = getEvidence(id);
  if (!ev) {
    return NextResponse.json({ detail: "Evidence not found." }, { status: 404 });
  }
  return NextResponse.json(ev);
}
