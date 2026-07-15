import { NextRequest, NextResponse } from "next/server";
import { getBeforeActions } from "@/lib/demo-data";

export const dynamic = "force-dynamic";

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
  return NextResponse.json({ ...action, status: "rejected" });
}
