import { NextRequest } from "next/server";
import {
  CopilotRuntime,
  LangChainAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { ChatOllama } from "@langchain/ollama";
import { AIMessage, HumanMessage, BaseMessage } from "@langchain/core/messages";
import { ChainValues } from "@langchain/core/utils/types";

console.log("Initializing CopilotKit runtime...");

const model = new ChatOllama({
  model: "llama3.3:70b",
  temperature: 0
});

interface ChainFnParameters {
  messages: BaseMessage[];
  state?: ChainValues;
}

const serviceAdapter = new LangChainAdapter({
  chainFn: async ({ messages, state }: ChainFnParameters) => {
    // Log state updates for debugging
    console.log("Service Adapter State Update:", state);

    // Handle intermediate state updates (current_node changes)
    if (state?.current_node && !state?.final_generation) {
      console.log("Emitting intermediate state for node:", state.current_node);
      // Return a special AIMessage that won't be displayed in chat
      return new AIMessage({ 
        content: "__STATE_UPDATE__", // Special marker that can be filtered out by chat
        additional_kwargs: {
          _type: "state_update",
          current_node: state.current_node,
          display_in_chat: false // Flag to tell frontend not to display this message
        }
      });
    }

    // Handle final generation
    if (state?.final_generation) {
      console.log("Emitting final generation with node:", state.current_node);
      return new AIMessage({ 
        content: state.final_generation as string,
        additional_kwargs: {
          current_node: state.current_node,
          is_final: true,
          display_in_chat: true
        }
      });
    }

    // Fallback to direct model response if no state or generation
    const formattedMessages = messages.map((msg: BaseMessage) => ({
      role: msg instanceof HumanMessage ? 'user' : 'assistant',
      content: msg.content
    }));

    const result = await model.generate([formattedMessages]);
    const content = result.generations[0][0].text;
    
    return new AIMessage({ 
      content,
      additional_kwargs: {
        is_direct_response: true,
        display_in_chat: true
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