import { NextRequest } from "next/server";
import {
  CopilotRuntime,
  LangChainAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { ChatOllama } from "@langchain/ollama";
import { AIMessage, HumanMessage, BaseMessage } from "@langchain/core/messages";
import { ChainValues } from "@langchain/core/utils/types";
import { API_ENDPOINT, BACKEND_ENDPOINT } from "@/constants";

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
    // console.log("Chain Function Called");
    // console.log("Service Adapter State:", state);
    // console.log("Service Adapter Messages:", messages);
    
    // If we have a final generation, return it with state
    // if (state?.final_generation) {
    //   return new AIMessage({
    //     content: state.final_generation as string,
    //     additional_kwargs: {
    //       state_update: {
    //         current_node: state.current_node,
    //         final_generation: state.final_generation
    //       },
    //       display_in_chat: false // Show final generation in chat
    //     }
    //   });
    // }

    // // If we have a state update but no final generation, send state update
    // if (state?.current_node) {
    //   return new AIMessage({
    //     content: "", // Empty content for state updates
    //     additional_kwargs: {
    //       state_update: {
    //         current_node: state.current_node,
    //         final_generation: ""
    //       },
    //       display_in_chat: false // Don't show intermediate updates in chat
    //     }
    //   });
    // }
    
    // For direct model responses
    const formattedMessages = messages.map((msg: BaseMessage) => ({
      role: msg instanceof HumanMessage ? 'user' : 'assistant',
      content: msg.content
    }));

    const result = await model.generate([formattedMessages]);
    return new AIMessage({
      content: result.generations[0][0].text,
      additional_kwargs: {
        display_in_chat: true // Show direct responses in chat
      }
    });
  }
});

const runtime = new CopilotRuntime({
  remoteEndpoints: [
    {
      url: BACKEND_ENDPOINT
    }
  ]
});

export const POST = async (req: NextRequest) => {
  // console.log("\n=== Frontend Request Processing ===");
  // console.log("Received request at /api/copilotkit");
  // console.log("Request URL:", req.url);
  // console.log("Request method:", req.method);
  // console.log("Request headers:", Object.fromEntries(req.headers));
  
  try {
    // Skip cloning and logging the request body
    // const clonedReq = req.clone();
    // const body = await clonedReq.json();
    // console.log("\nOriginal request body:", JSON.stringify(body, null, 2));
    
    // Use the original request directly instead of creating a new one
    // const formattedReq = new NextRequest(req.url, {
    //   method: req.method,
    //   headers: req.headers,
    //   body: JSON.stringify(body)
    // });
    
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: API_ENDPOINT,
  });

    // console.log("\nForwarding formatted request to runtime...");
    const response = await handleRequest(req);
    // console.log("Response status:", response.status);
    // console.log("Response headers:", Object.fromEntries(response.headers));
    
    // Skip cloning and logging the response body
    // const clonedResponse = response.clone();
    // const responseBody = await clonedResponse.text();
    // console.log("Response body:", responseBody);
    
    // console.log("=== End Frontend Request Processing ===\n");
    return response;
  } catch (error) {
    // console.error("\n=== Error in /api/copilotkit ===");
    // console.error("Error details:", error);
    // if (error instanceof Error) {
    //   console.error("Error stack:", error.stack);
    // }
    throw error;
  }
};