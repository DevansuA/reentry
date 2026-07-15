import { NextRequest, NextResponse } from "next/server";
import { getBeforeEntropy, getAfterEntropy } from "@/lib/demo-data";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const state = req.nextUrl.searchParams.get("state");
  const ent = state === "after" ? getAfterEntropy() : getBeforeEntropy();
  return NextResponse.json(ent);
}
