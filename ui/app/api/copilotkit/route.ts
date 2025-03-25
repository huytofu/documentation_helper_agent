import { NextRequest } from "next/server";
import {
  CopilotRuntime,
  LangChainAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { ChatTogetherAI } from "@langchain/community/chat_models/togetherai";
import { AIMessage, HumanMessage, BaseMessage } from "@langchain/core/messages";
import { ChainValues } from "@langchain/core/utils/types";
import { API_ENDPOINT, BACKEND_ENDPOINT } from "@/constants";

// Get TogetherAI API key from environment
const TOGETHER_API_KEY = process.env.INFERENCE_API_KEY || "";

// Create TogetherAI chat model
const model = new ChatTogetherAI({
  apiKey: TOGETHER_API_KEY,
  modelName: "meta-llama/Llama-3-70b-chat-hf",
  temperature: 0
});

interface ChainFnParameters {
  messages: BaseMessage[];
  state?: ChainValues;
}

// Security error response handler
const handleSecurityError = (error: any) => {
  // Check if it's a security error response from the backend
  if (error.status === 400 && error.detail) {
    return new AIMessage({
      content: `⚠️ Security Alert: ${error.detail}\n\nI cannot process this request due to security concerns. Please modify your input and try again.`,
      additional_kwargs: {
        display_in_chat: true,
        error_type: "security",
        error_message: error.detail
      }
    });
  }
  throw error;
};

const serviceAdapter = new LangChainAdapter({
  chainFn: async ({ messages, state }: ChainFnParameters) => {
    try {
      // For direct model responses
      const formattedMessages = messages.map((msg: BaseMessage) => ({
        role: msg instanceof HumanMessage ? 'user' : 'assistant',
        content: msg.content
      }));

      const result = await model.generate([formattedMessages]);
      return new AIMessage({
        content: result.generations[0][0].text,
        additional_kwargs: {
          display_in_chat: true
        }
      });
    } catch (error: any) {
      return handleSecurityError(error);
    }
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
  try {
    const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
      runtime,
      serviceAdapter,
      endpoint: API_ENDPOINT,
    });

    const response = await handleRequest(req);
    
    // Check if the response is a security error
    if (response.status === 400) {
      const errorData = await response.json();
      return new Response(
        JSON.stringify({
          error: "security",
          message: errorData.detail,
          display_in_chat: true
        }),
        {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
          }
        }
      );
    }
    
    return response;
  } catch (error: any) {
    // Handle security errors
    if (error.status === 400 && error.detail) {
      return new Response(
        JSON.stringify({
          error: "security",
          message: error.detail,
          display_in_chat: true
        }),
        {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
          }
        }
      );
    }
    
    // Handle other errors
    return new Response(
      JSON.stringify({
        error: "internal",
        message: "An unexpected error occurred. Please try again later.",
        display_in_chat: true
      }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
        }
      }
    );
  }
};