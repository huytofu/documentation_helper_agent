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
    // Format messages to ensure they have the correct structure
    const formattedMessages = messages.map(msg => ({
      role: msg instanceof HumanMessage ? 'user' : 'assistant',
      content: msg.content
    }));

    // Generate response using the model
    const result = await model.generate([formattedMessages]);
    const content = result.generations[0][0].text;
    
    return new AIMessage({ 
      content
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
  console.log("\n=== Frontend Request Processing ===");
  console.log("Received request at /api/copilotkit");
  console.log("Request URL:", req.url);
  console.log("Request method:", req.method);
  console.log("Request headers:", Object.fromEntries(req.headers));
  
  try {
    // Clone the request before reading its body
    const clonedReq = req.clone();
    const body = await clonedReq.json();
    console.log("\nOriginal request body:", JSON.stringify(body, null, 2));
    
    // Create a new request with the original body
    const formattedReq = new NextRequest(req.url, {
      method: req.method,
      headers: req.headers,
      body: JSON.stringify(body)
    });
    
    const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
      runtime,
      serviceAdapter,
      endpoint: "/api/copilotkit",
    });

    console.log("\nForwarding formatted request to runtime...");
    const response = await handleRequest(formattedReq);
    console.log("Response status:", response.status);
    console.log("Response headers:", Object.fromEntries(response.headers));
    
    // Clone the response before reading it for logging
    const clonedResponse = response.clone();
    const responseBody = await clonedResponse.text();
    console.log("Response body:", responseBody);
    
    console.log("=== End Frontend Request Processing ===\n");
    return response;
  } catch (error) {
    console.error("\n=== Error in /api/copilotkit ===");
    console.error("Error details:", error);
    if (error instanceof Error) {
      console.error("Error stack:", error.stack);
    }
    throw error;
  }
}; 