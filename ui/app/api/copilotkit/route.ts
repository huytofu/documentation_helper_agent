import { NextRequest } from "next/server";
import {
  CopilotRuntime,
  LangChainAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { AIMessage, HumanMessage, BaseMessage } from "@langchain/core/messages";
import { ChainValues } from "@langchain/core/utils/types";
import { API_ENDPOINT, BACKEND_ENDPOINT } from "@/constants";
import { getModel } from "@/lib/modelConfig";
import { AuthService } from "@/lib/auth";

// Get the configured model
const model = getModel();

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
      // Extract the last user message for generation
      const lastUserMessage = [...messages].reverse().find(msg => msg instanceof HumanMessage);
      
      if (!lastUserMessage) {
        return new AIMessage({
          content: "I'm not sure what to respond to. Could you please ask a question?",
          additional_kwargs: {
            display_in_chat: true
          }
        });
      }
      
      // For ChatOllama models, convert message content to string if needed
      const messageText = typeof lastUserMessage.content === 'string' 
        ? lastUserMessage.content 
        : JSON.stringify(lastUserMessage.content);
      
      // Use the message directly - HumanMessage is already properly formatted
      console.log("messageText", messageText);
      console.log("Awaiting model.invoke from serviceAdapter");
      const response = await model.invoke(messageText);
      console.log("model.invoke completed");
      
      // Convert response to string if it's an AIMessageChunk
      const responseContent = typeof response === 'string' 
        ? response 
        : response.content;
      
      return new AIMessage({
        content: responseContent,
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

// Track chat usage after a successful response
async function trackChatUsage(isAuthenticated: boolean): Promise<void> {
  try {
    // Get auth service instance
    const authService = AuthService.getInstance();
    
    // Check if there's an authenticated user
    if (!isAuthenticated) {
      console.log("No authenticated user, skipping chat usage tracking");
      return;
    }
    
    // Increment chat usage count
    await authService.incrementChatUsage();
    
    // Get and log remaining chats (optional)
    const remaining = await authService.getRemainingChats();
    console.log(`Chat usage tracked successfully. Remaining chats: ${remaining}`);
  } catch (error) {
    // Log but don't fail the request
    console.error("Failed to track chat usage:", error);
  }
}

export const POST = async (req: NextRequest) => {
  try {
    // Extract authentication cookies/headers to check auth state
    const authSession = req.cookies.get('auth_session')?.value;
    const loggedIn = req.cookies.get('logged_in')?.value;
    const firebaseAuth = req.cookies.get('firebase:authUser')?.value;
    
    // Check authentication state
    const isAuthenticated = !!(authSession || loggedIn || firebaseAuth);
    
    // Only modify request body if we have auth session
    if (authSession) {
      try {
        const body = req.body ? await req.json() : {};
        console.log("Original request body:", body);
        body.auth_session = authSession;
        console.log("Modified request body:", body);
        req = new NextRequest(req.url, {
          method: req.method,
          headers: req.headers,
          body: JSON.stringify(body)
        });
      } catch (error) {
        console.error("Error parsing request body:", error);
        return new Response(
          JSON.stringify({
            error: "invalid_request",
            message: "Invalid request body format",
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
    }
    
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
    
    // Track usage only after successful responses and if authenticated
    if (response.status === 200 && isAuthenticated) {
      console.log("User is authenticated, tracking chat usage");
      // Track usage in the background without blocking the response
      trackChatUsage(isAuthenticated).catch(err => 
        console.error("Background chat tracking failed:", err)
      );
    } else if (response.status === 200) {
      console.log("User appears not authenticated based on cookies, auth tracking skipped");
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