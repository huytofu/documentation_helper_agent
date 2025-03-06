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
    console.log("Processing messages through LangGraph agent:", messages);
    const lastMessage = messages[messages.length - 1];
    const messageContent = typeof lastMessage.content === 'string' ? lastMessage.content : '';
    
    // Extract language from system message
    const systemMessage = messages.find(msg => 
      typeof msg.content === 'string' && 
      msg.content.includes('The selected programming language is:')
    );
    const systemContent = typeof systemMessage?.content === 'string' ? systemMessage.content : '';
    const languageMatch = systemContent.match(/The selected programming language is: (.*?)\./);
    const selectedLanguage = languageMatch ? languageMatch[1].toLowerCase() : 'python';
    
    const state = {
      language: selectedLanguage,
      query: messageContent,
      documents: [],
      framework: "default",
      generation: "",
      comments: "",
      retry_count: 0
    };
    const result = await model.invoke([
      {
        role: "user",
        content: JSON.stringify(state)
      }
    ]);
    const content = result.content;
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