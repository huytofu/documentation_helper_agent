import { NextResponse } from "next/server";
import { BACKEND_ENDPOINT } from "@/constants";

const DOCUMENTATION_HELPER_API_KEY = process.env.DOCUMENTATION_HELPER_API_KEY;

// Hobby max. Warm-up is parallel Together pings; keep under plan limit.
export const maxDuration = 60;
export const dynamic = "force-dynamic";

function backendWarmupUrl(): string {
  const base = BACKEND_ENDPOINT.split("copilotkitagent")[0];
  return `${base}warmup-models`;
}

export async function POST() {
  try {
    const url = backendWarmupUrl();
    console.log("Warming models via backend:", url);

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": DOCUMENTATION_HELPER_API_KEY || "",
      },
      body: JSON.stringify({}),
    });

    const data = await response.json().catch(() => ({
      ok: false,
      status: "failed",
      error: "Invalid JSON from warmup backend",
    }));

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("Warm-up proxy failed:", error);
    return NextResponse.json(
      {
        ok: false,
        status: "failed",
        error: "Failed to warm models",
      },
      { status: 500 }
    );
  }
}
