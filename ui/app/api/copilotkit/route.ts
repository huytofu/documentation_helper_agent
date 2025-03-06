import { NextRequest } from "next/server";
import {
  CopilotRuntime,
  LangChainAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { ChatOllama } from "@langchain/ollama";
import { AIMessage, HumanMessage } from "@langchain/core/messages";

console.log("Initializing CopilotKit runtime...");

const model = new ChatOllama({
  model: "llama3.3:70b",
  temperature: 0
});

const serviceAdapter = new LangChainAdapter({
  chainFn: async ({ messages }) => {
    console.log("Processing messages through LangGraph agent:", messages);
    
    // Format messages for the model
    const formattedMessages = messages.map(msg => ({
      role: msg instanceof HumanMessage ? 'user' : 'assistant',
      content: typeof msg.content === 'string' ? msg.content : ''
    }));

    const result = await model.generate([formattedMessages]);
    const content = result.generations[0][0].text;
    
    return new AIMessage({ 
      content,
      additional_kwargs: {
        processed_by_backend: true,
        processed_by_langgraph: true,
        agent: "coding_agent"
      }
    });
  }
});

const runtime = new CopilotRuntime({
  remoteEndpoints: [
    {
      url: process.env.REMOTE_ACTION_URL || "http://localhost:8000/copilotkitagent"
    }
  ]
});

export const POST = async (req: NextRequest) => {
  console.log("Received request at /api/copilotkit");
  console.log("Request URL:", req.url);
  console.log("Request method:", req.method);
  console.log("Request headers:", Object.fromEntries(req.headers));
  
  try {
    const body = await req.json();
    console.log("Request body:", JSON.stringify(body, null, 2));
    
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