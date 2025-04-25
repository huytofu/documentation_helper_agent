# Documentation Helper Agent

A LangGraph-based agent that helps with code documentation and answering coding-related questions.

## Features

- Multi-stage processing pipeline for accurate responses
- Support for multiple model providers (Hugging Face, Ollama, RunPod)
- Efficient resource management and caching
- Parallel processing capabilities
- Comprehensive error handling and logging

## Model Configuration

The agent uses a combination of specialized models for different tasks:

### Default Model Combination
- **Embeddings**: `BAAI/bge-large-en-v1.5` (Hugging Face)
  - High-quality embeddings for semantic search
  - Optimized for code and documentation
- **Router**: `meta-llama/Meta-Llama-3.1-8B-Instruct` (Hugging Face)
  - Efficient model for routing decisions
- **Graders**: Multiple specialized graders
  - Sentiment: `mistralai/Mistral-7B-Instruct-v0.3`
  - Answer: `mistralai/Mistral-7B-Instruct-v0.3`
  - Retrieval: `meta-llama/Meta-Llama-3.1-8B-Instruct`
  - Hallucination: `Qwen/Qwen2.5-14B-Instruct`
- **Summarizer**: `Qwen/Qwen2.5-14B-Instruct`
- **Generator**: `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct` (Inference API or RunPod with vLLM)
  - Specialized for code generation
  - Optimized for documentation tasks
  - Can be served using vLLM framework for improved performance

### Alternative Model Options
- **Ollama Models**:
  - Set `USE_OLLAMA=true` and configure Ollama Base URL
- **Inference API**:
  - Set `USE_INFERENCE_CLIENT=true` and `INFERENCE_PROVIDER=together` (or other providers)
- **Hugging Face Only**:
  - Set `USE_RUNPOD=false` and `USE_HUGGINGFACE=true`

## Environment Variables

Configure the agent using the following environment variables:

```bash
# Model Provider Selection
USE_OLLAMA=false
USE_HUGGINGFACE=true
USE_INFERENCE_CLIENT=false
USE_RUNPOD=false

# Ollama settings (if using Ollama)
OLLAMA_BASE_URL=http://localhost:11434

# Server configuration
PORT=8000
SERVER_TYPE=vercel  # Options: local, aws lambda, vercel
PROVISIONED_CONCURRENCY=1
CONCURRENCY_LIMIT=5

# LangGraph configuration
FLOW=real  # Options: real, test, simple
LOG_LEVEL=INFO

# LangGraph Checkpointer Configuration
CHECKPOINTER_TYPE=redis  # Options: memory, vercel_kv, postgres, redis
REDIS_URL=your_redis_url

# Vector store configuration
VECTOR_STORE_TYPE=pinecone  # Options: chroma, pinecone
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=documentation-helper-agent
PINECONE_DIMENSION=1024
PINECONE_INDEX_TYPE=dense
PINECONE_METRIC=cosine

# Inference API Configuration (if USE_INFERENCE_CLIENT=true)
INFERENCE_PROVIDER=together  # Options: together, perplexity, anyscale, etc.
INFERENCE_API_KEY=inference_provider_api_key
INFERENCE_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
INFERENCE_ROUTER_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
INFERENCE_SENTIMENT_GRADER_MODEL=mistralai/Mistral-7B-Instruct-v0.3
INFERENCE_ANSWER_GRADER_MODEL=mistralai/Mistral-7B-Instruct-v0.3
INFERENCE_RETRIEVAL_GRADER_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
INFERENCE_HALLUCINATE_GRADER_MODEL=Qwen/Qwen2.5-14B-Instruct
INFERENCE_SUMMARIZER_MODEL=Qwen/Qwen2.5-14B-Instruct
INFERENCE_GENERATOR_MODEL=deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct

# RunPod Configuration (if USE_RUNPOD=true)
RUNPOD_API_KEY=your_runpod_api_key
RUNPOD_ENDPOINT_ID=your_runpod_endpoint_id
RUNPOD_MODEL_ID=deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct
RUNPOD_MAX_TOKENS=2048
RUNPOD_TEMPERATURE=0.2
RUNPOD_TOP_P=0.9
RUNPOD_TOP_K=40
RUNPOD_PRESENCE_PENALTY=0.1
RUNPOD_FREQUENCY_PENALTY=0.1
RUNPOD_USE_VLLM=true
RUNPOD_TRUST_REMOTE_CODE=true

# Hugging Face Configuration (if USE_HUGGINGFACE=true)
HUGGINGFACE_API_KEY=your_huggingface_api_key
HUGGINGFACE_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
HUGGINGFACE_ROUTER_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
HUGGINGFACE_SENTIMENT_GRADER_MODEL=mistralai/Mistral-7B-Instruct-v0.3
HUGGINGFACE_ANSWER_GRADER_MODEL=mistralai/Mistral-7B-Instruct-v0.3
HUGGINGFACE_RETRIEVAL_GRADER_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
HUGGINGFACE_HALLUCINATE_GRADER_MODEL=Qwen/Qwen2.5-14B-Instruct
HUGGINGFACE_SUMMARIZER_MODEL=Qwen/Qwen2.5-14B-Instruct
HUGGINGFACE_GENERATOR_MODEL=deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct
HUGGINGFACE_MAX_TOKENS=2048
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/documentation_helper_agent.git
cd documentation_helper_agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Usage

1. Start the FastAPI server:
```bash
uvicorn agent.graph.app:app --reload
```

2. Send requests to the API:
```bash
curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{"query": "How do I implement a binary search tree?"}'
```

## Deployment

### Vercel Serverless Deployment

1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Configure environment variables in Vercel:
   - Go to your project settings in Vercel
   - Add the required environment variables from .env.example, especially:
     ```
     HUGGINGFACE_API_KEY=your_huggingface_api_key
     SERVER_TYPE=vercel
     DOCUMENTATION_HELPER_API_KEY=your_api_key
     FRONTEND_URL=your_frontend_url
     ```

3. Deploy to Vercel:
```bash
vercel
```

4. Set up warm-up endpoint:
   - Create a cron job in Vercel to call `/api/warmup` every 5 minutes
   - This helps keep the serverless functions warm

5. Monitor deployment:
   - Check Vercel dashboard for deployment status
   - Monitor function execution times
   - Watch for any errors in the logs

### RunPod Serverless Deployment

1. Set up RunPod:
   - Create a RunPod account
   - Deploy DeepSeek Coder V2 on RunPod serverless
   - Get your API key and endpoint ID

2. Configure environment variables:
   ```bash
   USE_RUNPOD=true
   RUNPOD_API_KEY=your_runpod_api_key
   RUNPOD_ENDPOINT_ID=your_runpod_endpoint_id
   RUNPOD_MODEL_ID=deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct
   RUNPOD_USE_VLLM=true
   ```

3. Benefits of RunPod serverless:
   - Pay-per-request pricing
   - Automatic scaling
   - Cold start optimization
   - High availability
   - Low latency

4. Monitoring:
   - Use RunPod dashboard to monitor:
     - Request volume
     - Response times
     - Error rates
     - Cost per request

### Firebase Configuration

If using Firebase for authentication and storage:

```bash
NEXT_PUBLIC_FIREBASE_API_KEY=your_firebase_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_firebase_auth_domain
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_firebase_project_id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your_firebase_storage_bucket
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_firebase_messaging_sender_id
NEXT_PUBLIC_FIREBASE_APP_ID=your_firebase_app_id
FIREBASE_SERVICE_ACCOUNT=your_firebase_service_account
FIREBASE_CLIENT_EMAIL=your_client_email_here
FIREBASE_PRIVATE_KEY=your_private_key_here
```

### Performance Optimization

For optimal performance:

1. **Cold Start Optimization**:
   - Use the warm-up endpoint
   - Keep functions warm with provisioned concurrency
   - Optimize function size

2. **Resource Management**:
   - Monitor memory usage
   - Optimize response times
   - Use appropriate timeout settings

3. **Cost Optimization**:
   - Monitor function execution times
   - Use appropriate concurrency limits
   - Implement caching where possible

4. **Monitoring**:
   - Set up analytics and logging
   - Monitor error rates
   - Track performance metrics