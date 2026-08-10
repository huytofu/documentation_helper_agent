import { InferenceClient } from "@huggingface/inference";
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

  private async callTogetherDirectAPI(prompt: string): Promise<string> {
    try {
      console.log("Making API call using Together client");
      const completion = await this.togetherClient.chat.completions.create({
        model: TOGETHER_DIRECT_CONFIG.model,
        messages: [{ role: "user", content: prompt }],
        temperature: TOGETHER_DIRECT_CONFIG.temperature,
        max_tokens: TOGETHER_DIRECT_CONFIG.max_tokens,
        top_p: TOGETHER_DIRECT_CONFIG.top_p,
        top_k: TOGETHER_DIRECT_CONFIG.top_k,
        stop: TOGETHER_DIRECT_CONFIG.stop,
      });

      return completion.choices?.[0]?.message?.content || "";
    } catch (error: any) {
      console.error("Error calling Together AI client:", error);
      throw new Error(`Failed to get response from both providers: ${error.message}`);
    }
  }

  async stream(_prompt: string): Promise<AsyncIterable<string>> {
    throw new Error("Streaming not implemented for InferenceClient");
  }
}

export function getModel() {
  if (USE_OLLAMA) {
    throw new Error(
      "USE_OLLAMA is no longer supported in the AG-UI CopilotKit path; enable USE_INFERENCE_CLIENT or use the LangGraph agent backend"
    );
  }
  if (USE_INFERENCE_CLIENT) {
    return new HFInferenceClientWrapper(INFERENCE_CLIENT_CONFIG);
  }
  throw new Error("No model provider enabled. Please set USE_INFERENCE_CLIENT to true");
}
