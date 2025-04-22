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
- **Grader & Router**: `meta-llama/Llama-3-70b-chat-hf` (Hugging Face)
  - Powerful model for decision making
  - Used for both grading and routing tasks
- **Generator**: `deepseek-ai/deepseek-coder-v2-instruct` (RunPod with vLLM)
  - Specialized for code generation
  - Optimized for documentation tasks
  - Served using vLLM framework for improved performance

### Alternative Model Options
- **Ollama Models**:
  - Embeddings: `qllama/bge-large-en-v1.5` (Quantized version of BGE-large-en-v1.5)
  - Grader & Router: `llama3.3:70b`
  - Generator: `deepseek-coder:33b`
- **Hugging Face Only**:
  - Set `USE_RUNPOD=false` to use Hugging Face for all models
  - Generator: `deepseek-ai/deepseek-coder-v2-instruct` (via Hugging Face Inference API)

## Environment Variables

Configure the agent using the following environment variables:

```bash
# Model Provider Selection (Default: Hugging Face for most models, RunPod for generator)
USE_HUGGINGFACE=true  # Use Hugging Face models (default)
USE_INFERENCE_CLIENT=false  # Use third-party inference providers
USE_RUNPOD=true  # Use RunPod serverless for generator model (default)

# RunPod Configuration (if USE_RUNPOD=true)
RUNPOD_API_KEY=your_runpod_api_key
RUNPOD_ENDPOINT_ID=your_endpoint_id
RUNPOD_MODEL_ID=deepseek-ai/deepseek-coder-v2-instruct
RUNPOD_MAX_TOKENS=2048
RUNPOD_TEMPERATURE=0.2
RUNPOD_TOP_P=0.9
RUNPOD_TOP_K=40
RUNPOD_PRESENCE_PENALTY=0.1
RUNPOD_FREQUENCY_PENALTY=0.1

# Hugging Face Configuration
HUGGINGFACE_API_KEY=your_huggingface_api_key

# Model Selection (Default Models)
HUGGINGFACE_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
HUGGINGFACE_GRADER_MODEL=meta-llama/Llama-3-70b-chat-hf
HUGGINGFACE_ROUTER_MODEL=meta-llama/Llama-3-70b-chat-hf
HUGGINGFACE_GENERATOR_MODEL=deepseek-ai/deepseek-coder-v2-instruct

# Concurrency Settings
PROVISIONED_CONCURRENCY=1  # Number of concurrent instances
CONCURRENCY_LIMIT=5  # Maximum concurrent requests per instance
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
   - Add the following environment variables:
     ```
     HUGGINGFACE_API_KEY=your_huggingface_api_key
     API_KEY=your_api_key
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
   RUNPOD_ENDPOINT_ID=your_endpoint_id
   RUNPOD_MODEL_ID=deepseek-ai/deepseek-coder-v2-instruct
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

### Environment Variables

For Vercel deployment, set these environment variables in your Vercel project settings:

```bash
# Model Provider Selection (Default: Hugging Face Inference API)
USE_HUGGINGFACE=true
USE_INFERENCE_CLIENT=false

# Hugging Face Configuration
HUGGINGFACE_API_KEY=your_huggingface_api_key

# Model Selection (Default Models)
HUGGINGFACE_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
HUGGINGFACE_GRADER_MODEL=meta-llama/Llama-3-70b-chat-hf
HUGGINGFACE_ROUTER_MODEL=meta-llama/Llama-3-70b-chat-hf
HUGGINGFACE_GENERATOR_MODEL=deepseek-ai/deepseek-coder-v2-instruct

# Concurrency Settings (Optimized for Vercel)
PROVISIONED_CONCURRENCY=1
CONCURRENCY_LIMIT=5

# Environment
ENVIRONMENT=production

# API Security
API_KEY=your_api_key

# Frontend URL (for CORS)
FRONTEND_URL=your_frontend_url

# Logging
LOG_LEVEL=INFO
```

### Performance Optimization

For optimal performance on Vercel:

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
   - Set up Vercel Analytics
   - Monitor error rates
   - Track performance metrics