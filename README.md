# Documentation Helper Agent

A LangGraph-based agent that helps with code documentation and answering coding-related questions.

## Features

- Multi-stage processing pipeline for accurate responses
- Support for multiple model providers (Inference API, Ollama, RunPod)
- Efficient resource management and caching
- Parallel processing capabilities
- Comprehensive error handling and logging

## Model Configuration

The agent uses a combination of specialized models for different tasks. You can choose between Ollama (local) and Inference API (cloud) model providers.

### Default Model Combination
- **Embeddings**: `BAAI/bge-large-en-v1.5`
  - High-quality embeddings for semantic search
  - Optimized for code and documentation
- **Router**: `meta-llama/Meta-Llama-3.1-8B-Instruct`
  - Efficient model for routing decisions
- **Graders**: Multiple specialized graders
  - Sentiment: `mistralai/Mistral-7B-Instruct-v0.3`
  - Answer: `mistralai/Mistral-7B-Instruct-v0.3`
  - Retrieval: `meta-llama/Meta-Llama-3.1-8B-Instruct`
  - Hallucination: `Qwen/Qwen2.5-14B-Instruct`
- **Summarizer**: `Qwen/Qwen2.5-14B-Instruct`
- **Generator**: `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct`
  - Specialized for code generation
  - Optimized for documentation tasks

### Deployment Options

There are two main deployment configurations:

#### 1. Local Deployment with Ollama
- Set `USE_OLLAMA=true` and `USE_INFERENCE_CLIENT=false`
- Requires Ollama running locally
- Uses local models specified in `OLLAMA_MODELS` configuration
- Best for development and testing

#### 2. Cloud Deployment with Inference API
- Set `USE_OLLAMA=false` and `USE_INFERENCE_CLIENT=true`
- Connect to cloud-based model providers like Together AI, Perplexity, etc.
- Optional: Set `USE_RUNPOD=true` to use RunPod for the generator model
- Best for production deployments

## Environment Variables

Configure the agent using the following environment variables:

```bash
# Model Provider Selection (choose one option)
# Option 1: Local deployment with Ollama
USE_OLLAMA=true
USE_INFERENCE_CLIENT=false
USE_RUNPOD=false
OLLAMA_BASE_URL=http://localhost:11434

# Option 2: Cloud deployment with Inference API
USE_OLLAMA=false
USE_INFERENCE_CLIENT=true
USE_RUNPOD=false  # Can be true to offload generator to RunPod

# Server configuration
PORT=8080
SERVER_TYPE=gcp  # Options: local, aws lambda, vercel, gcp
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

# Inference API Configuration (required if USE_INFERENCE_CLIENT=true)
INFERENCE_PROVIDER=together  # Options: together, perplexity, anyscale, etc.
INFERENCE_API_KEY=inference_provider_api_key
INFERENCE_DIRECT_API_KEY=inference_provider_direct_api_key
INFERENCE_MAX_TOKENS=2048

# RunPod Configuration (required if USE_RUNPOD=true)
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
curl -X POST "http://localhost:8080/api/chat" \
     -H "Content-Type: application/json" \
     -d '{"query": "How do I implement a binary search tree?"}'
```

## Deployment

This application is designed to be deployed as a split architecture:

1. **Frontend UI**: Deployed on Vercel
2. **Backend Agent**: Deployed on Google Cloud Run

### Frontend Deployment (Vercel)

PLEASE READ VERCEL_DEPLOYMENT.md

### Backend Deployment (Google Cloud Run)

1. Install Google Cloud CLI:
```bash
# For Linux/Mac
curl https://sdk.cloud.google.com | bash

# For Windows, download from https://cloud.google.com/sdk/docs/install
```

2. Authenticate and set project:
```bash
gcloud auth login
gcloud config set project your-project-id
```

3. Enable required services:
```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
```

4. Build and deploy with Cloud Build:
```bash
# Build the Docker image
gcloud builds submit --tag gcr.io/documentation-helper-agent/documentation-helper-agent

# Deploy to Cloud Run
powershell -Command "(Get-Content .env | Where-Object {$_ -notmatch '^#'} | ForEach-Object {$_.Trim()}) -join ',' | Out-File -Encoding ASCII env_vars.txt"

gcloud beta run deploy documentation-helper-agent ^
  --image gcr.io/documentation-helper-agent/documentation-helper-agent ^
  --platform managed ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --cpu 1 ^
  --memory 2Gi ^
  --env-vars-file=env.yaml

#see error logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=documentation-helper-agent AND resource.labels.revision_name=YOUR_REVISION_NAME" --format="table(textPayload)"
```

5. Set up CI/CD (optional):
   - Connect your GitHub repo to Google Cloud Build
   - Create a build trigger for automatic deployments

### Alternative: Quick Deploy with Dockerfile

You can also deploy directly from your local machine:

```bash
# Build the Docker image locally
docker build -t documentation-helper-agent .

# Deploy directly to Cloud Run
gcloud run deploy documentation-helper-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### RunPod Integration (Optional)

If you want to use RunPod for the generator model while deploying on Google Cloud Run:

1. Set up RunPod:
   - Create a RunPod account
   - Deploy DeepSeek Coder V2 on RunPod serverless
   - Get your API key and endpoint ID

2. Configure environment variables in Cloud Run:
   ```
   USE_OLLAMA=false
   USE_INFERENCE_CLIENT=true
   USE_RUNPOD=true
   RUNPOD_API_KEY=your_runpod_api_key
   RUNPOD_ENDPOINT_ID=your_runpod_endpoint_id
   RUNPOD_MODEL_ID=deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct
   RUNPOD_USE_VLLM=true
   ```

3. Benefits of RunPod integration:
   - Reduces Cloud Run memory requirements
   - Pay-per-request pricing
   - Automatic scaling
   - High availability
   - Low latency

### Firebase Configuration

If using Firebase for authentication and storage:

```bash
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_firebase_auth_domain
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_firebase_project_id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your_firebase_storage_bucket
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_firebase_messaging_sender_id
NEXT_PUBLIC_FIREBASE_APP_ID=your_firebase_app_id
NEXT_PUBLIC_FIREBASE_API_KEY=your_firebase_api_key
FIREBASE_SERVICE_ACCOUNT=your_firebase_service_account
FIREBASE_CLIENT_EMAIL=your_client_email_here
FIREBASE_PRIVATE_KEY=your_private_key_here
FIREBASE_PROJECT_ID=your_project_id
```

### Performance Optimization

For optimal performance:

1. **Cold Start Optimization**:
   - Increase minimum instances on Cloud Run to avoid cold starts
   - Use the warm-up endpoint for Vercel functions
   - Optimize container build for faster startup

2. **Resource Management**:
   - Monitor memory usage on Cloud Run
   - Adjust CPU and memory allocation as needed
   - Use appropriate timeout settings

3. **Cost Optimization**:
   - Set maximum instances on Cloud Run to control costs
   - Monitor function execution times
   - Implement caching where possible

4. **Monitoring**:
   - Set up Cloud Monitoring for backend
   - Set up Vercel Analytics for frontend
   - Monitor error rates
   - Track performance metrics