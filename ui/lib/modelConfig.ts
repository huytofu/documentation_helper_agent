import { InferenceClient } from "@huggingface/inference";
import { ChatOllama } from "@langchain/ollama";

// Environment flags
const USE_OLLAMA = process.env.USE_OLLAMA === "true";
const USE_INFERENCE_CLIENT = process.env.USE_INFERENCE_CLIENT === "true";
const INFERENCE_PROVIDER = process.env.INFERENCE_PROVIDER || "together";
const INFERENCE_API_KEY = process.env.INFERENCE_API_KEY || "";

// Validate environment configuration
if (USE_OLLAMA && USE_INFERENCE_CLIENT) {
  throw new Error("USE_OLLAMA and USE_INFERENCE_CLIENT cannot be enabled simultaneously");
}

// Model configurations
const OLLAMA_CONFIG = {
  model: "deepseek-coder:33b",
  temperature: 0,
  maxTokens: 2048,
  topP: 0.95,
  topK: 50,
  repetitionPenalty: 1.1,
  stop: ["</s>", "Human:", "Assistant:"],
  streaming: true
};

const INFERENCE_CLIENT_CONFIG = {
  provider: INFERENCE_PROVIDER,
  model: "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
  temperature: 0,
  max_tokens: 2048,
  top_p: 0.95,
  top_k: 50,
  repetition_penalty: 1.1,
  stop: ["</s>", "Human:", "Assistant:"],
};

// Create a client wrapper that provides a compatible interface with ChatOllama
class HFInferenceClientWrapper {
  private client: InferenceClient;
  private config: any;

  constructor(config: any) {
    this.client = new InferenceClient(INFERENCE_API_KEY);
    this.config = config;
  }

  // Add invoke method for compatibility with the route.ts usage
  async invoke(prompt: string): Promise<string> {
    return this.call(prompt);
  }

  async call(prompt: string): Promise<string> {
    try {
      const chatCompletion = await this.client.chatCompletion({
        provider: this.config.provider,
        model: this.config.model,
        messages: [
          {
            role: "user",
            content: prompt,
          },
        ],
        temperature: this.config.temperature,
        max_tokens: this.config.max_tokens,
        top_p: this.config.top_p,
        top_k: this.config.top_k,
        repetition_penalty: this.config.repetition_penalty,
        stop: this.config.stop,
      });

      return chatCompletion.choices[0].message.content || "";
    } catch (error) {
      console.error("Error calling inference client:", error);
      throw error;
    }
  }

  // Add streaming method if needed
  async stream(prompt: string): Promise<AsyncIterable<string>> {
    // Implementation depends on if the InferenceClient supports streaming
    throw new Error("Streaming not implemented for InferenceClient");
  }
}

// Get the appropriate model based on environment configuration
export function getModel() {
  if (USE_OLLAMA) {
    return new ChatOllama(OLLAMA_CONFIG);
  } else if (USE_INFERENCE_CLIENT) {
    return new HFInferenceClientWrapper(INFERENCE_CLIENT_CONFIG);
  } else {
    throw new Error("No model provider enabled. Please set either USE_OLLAMA or USE_INFERENCE_CLIENT to true");
  }
} 