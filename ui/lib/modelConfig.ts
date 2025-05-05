import { InferenceClient } from "@huggingface/inference";
import { ChatOllama } from "@langchain/ollama";
import Together from "together-ai";

// Environment flags
const USE_OLLAMA = process.env.USE_OLLAMA === "true";
const USE_INFERENCE_CLIENT = process.env.USE_INFERENCE_CLIENT === "true";
const INFERENCE_PROVIDER = process.env.INFERENCE_PROVIDER || "nebius";
const INFERENCE_API_KEY = process.env.INFERENCE_API_KEY || "";
const INFERENCE_DIRECT_API_KEY = process.env.INFERENCE_DIRECT_API_KEY || "";

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
  stop: ["</s>", "Human:", "Assistant:"],
};

const TOGETHER_DIRECT_CONFIG = {
  model: "arcee-ai/coder-large",
  temperature: 0,
  max_tokens: 2048,
  top_p: 0.95,
  top_k: 50,
  stop: ["</s>", "Human:", "Assistant:"],
};

// Create a client wrapper that provides a compatible interface with ChatOllama
class HFInferenceClientWrapper {
  private client: InferenceClient;
  private togetherClient: Together;
  private config: any;
  private hfApiKey: string;
  private togetherApiKey: string;

  constructor(config: any) {
    this.hfApiKey = INFERENCE_API_KEY;
    this.togetherApiKey = INFERENCE_DIRECT_API_KEY;
    this.client = new InferenceClient(this.hfApiKey);
    this.togetherClient = new Together({ apiKey: this.togetherApiKey });
    this.config = config;
  }

  // Add invoke method for compatibility with the route.ts usage
  async invoke(prompt: string): Promise<string> {
    return this.call(prompt);
  }

  async call(prompt: string): Promise<string> {
    try {
      console.log(`Attempting to call HuggingFace with ${this.config.provider} provider`);
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
        stop: this.config.stop,
      });

      return chatCompletion.choices[0].message.content || "";
    } catch (error) {
      console.error("Error calling HuggingFace inference client:", error);
      console.log("Falling back to Together AI client");
      return this.callTogetherDirectAPI(prompt);
    }
  }

  // Direct API call to Together AI using client library
  private async callTogetherDirectAPI(prompt: string): Promise<string> {
    try {
      console.log("Making API call using Together client");
      const completion = await this.togetherClient.chat.completions.create({
        model: TOGETHER_DIRECT_CONFIG.model,
        messages: [{ role: 'user', content: prompt }],
        temperature: TOGETHER_DIRECT_CONFIG.temperature,
        max_tokens: TOGETHER_DIRECT_CONFIG.max_tokens,
        top_p: TOGETHER_DIRECT_CONFIG.top_p,
        top_k: TOGETHER_DIRECT_CONFIG.top_k,
        stop: TOGETHER_DIRECT_CONFIG.stop
      });

      return completion.choices?.[0]?.message?.content || "";
    } catch (error: any) {
      console.error("Error calling Together AI client:", error);
      throw new Error(`Failed to get response from both providers: ${error.message}`);
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