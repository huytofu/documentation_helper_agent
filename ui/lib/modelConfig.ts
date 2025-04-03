import { HuggingFaceInference } from "@langchain/community/llms/hf";
import { ChatOllama } from "@langchain/ollama";

// Environment flags
const USE_OLLAMA = process.env.USE_OLLAMA === "true";
const USE_HUGGINGFACE = process.env.USE_HUGGINGFACE === "true";

// Validate environment configuration
if (USE_OLLAMA && USE_HUGGINGFACE) {
  throw new Error("USE_OLLAMA and USE_HUGGINGFACE cannot be enabled simultaneously");
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

const HUGGINGFACE_CONFIG = {
  model: "deepseek-ai/deepseek-coder-33b-instruct",
  temperature: 0,
  maxTokens: 2048,
  topP: 0.95,
  topK: 50,
  repetitionPenalty: 1.1,
  stop: ["</s>", "Human:", "Assistant:"],
  streaming: true
};

// Get the appropriate model based on environment configuration
export function getModel() {
  if (USE_OLLAMA) {
    return new ChatOllama(OLLAMA_CONFIG);
  } else if (USE_HUGGINGFACE) {
    return new HuggingFaceInference({
      ...HUGGINGFACE_CONFIG,
      apiKey: process.env.HUGGINGFACE_API_KEY || ""
    });
  } else {
    throw new Error("No model provider enabled. Please set either USE_OLLAMA or USE_HUGGINGFACE to true");
  }
} 