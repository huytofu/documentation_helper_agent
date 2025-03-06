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
        agent: "frontend_agent"
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
    
    // Extract language from system message
    const messages = body.messages || [];
    const systemMessage = messages.find((msg: { content: string }) => 
      typeof msg.content === 'string' && 
      msg.content.includes('The selected programming language is:')
    );
    const systemContent = typeof systemMessage?.content === 'string' ? systemMessage.content : '';
    const languageMatch = systemContent.match(/The selected programming language is: (.*?)\./);
    const selectedLanguage = languageMatch ? languageMatch[1].toLowerCase() : 'python';
    
    // Get the last user message
    const lastMessage = messages[messages.length - 1];
    const messageContent = typeof lastMessage?.content === 'string' ? lastMessage.content : '';
    
    // Format the request body according to backend expectations
    const formattedBody = {
      name: "coding_agent",
      state: {
        language: selectedLanguage,
        query: messageContent,
        framework: "default",
        documents: [],
        generation: "",
        comments: "",
        retry_count: 0
      },
    };
    
    console.log("\nFormatted request body:", JSON.stringify(formattedBody, null, 2));
    
    // Create a new request with the formatted body
    const formattedReq = new NextRequest(req.url, {
      method: req.method,
      headers: req.headers,
      body: JSON.stringify(formattedBody)
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
    
    const responseBody = await response.text();
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