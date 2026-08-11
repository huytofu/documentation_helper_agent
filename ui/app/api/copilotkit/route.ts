import { NextRequest } from "next/server";
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { LangGraphHttpAgent } from "@copilotkit/runtime/langgraph";
import { API_ENDPOINT, BACKEND_ENDPOINT, AGENT_NAME } from "@/constants";

// This Next route is a Vercel Function that fetch-streams Cloud Run (not a
// vercel.json external rewrite). Bound by Function maxDuration, not the 120s
// "proxied request" rewrite limit. Hobby plan max is 60s.
export const maxDuration = 60;
export const dynamic = "force-dynamic";

const serviceAdapter = new ExperimentalEmptyAdapter();

const runtime = new CopilotRuntime({
  agents: {
    [AGENT_NAME]: new LangGraphHttpAgent({
      url: BACKEND_ENDPOINT,
    }),
  },
});

export const POST = async (req: NextRequest) => {
  try {
    const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
      runtime,
      serviceAdapter,
      endpoint: API_ENDPOINT,
    });

    const response = await handleRequest(req);

    if (response.status === 400) {
      const errorData = await response.json();
      return new Response(
        JSON.stringify({
          error: "security",
          message: errorData.detail,
          display_in_chat: true,
        }),
        {
          status: 400,
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
    }
    return response;
  } catch (error: any) {
    if (error.status === 400 && error.detail) {
      return new Response(
        JSON.stringify({
          error: "security",
          message: error.detail,
          display_in_chat: true,
        }),
        {
          status: 400,
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
    }

    return new Response(
      JSON.stringify({
        error: "internal",
        message: "An unexpected error occurred. Please try again later.",
        display_in_chat: true,
      }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
  }
};
