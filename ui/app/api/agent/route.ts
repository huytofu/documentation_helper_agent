import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const { language, request } = await req.json();

    // Call your Python agent here
    const response = await fetch("http://localhost:8000/agent", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        language,
        request,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to process request");
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error:", error);
    return NextResponse.json(
      { error: "Failed to process request" },
      { status: 500 }
    );
  }
} 