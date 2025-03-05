import { NextRequest } from "next/server";
import {
  CopilotRuntime,
  LangChainAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { ChatOllama } from "@langchain/ollama";
import { AIMessage } from "@langchain/core/messages";

console.log("Initializing CopilotKit runtime...");

const model = new ChatOllama({
  model: "llama3.3:70b",
  temperature: 0
});

const serviceAdapter = new LangChainAdapter({
  chainFn: async ({ messages }) => {
    console.log("Processing messages:", messages);
    const formattedMessages = messages.map(msg => ({
      content: msg.content,
      role: msg instanceof AIMessage ? "assistant" : "user",
      metadata: {
        requiresBackend: true,
        timestamp: new Date().toISOString()
      }
    }));
    const result = await model.generate([formattedMessages]);
    const content = result.generations[0][0].text;
    return new AIMessage({ 
      content,
      additional_kwargs: {
        processed_by_backend: true
      }
    });
  }
});

const runtime = new CopilotRuntime({
  remoteEndpoints: [
    {
      url: process.env.REMOTE_ACTION_URL || "http://localhost:8000/copilotkit",
    },
  ],
});

export const POST = async (req: NextRequest) => {
  console.log("Received request at /api/copilotkit");
  try {
    const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
      runtime,
      serviceAdapter,
      endpoint: "/api/copilotkit",
    });

    console.log("Forwarding request to runtime...");
    const response = await handleRequest(req);
    console.log("Received response from runtime");
    return response;
  } catch (error) {
    console.error("Error in /api/copilotkit:", error);
    throw error;
  }
}; 