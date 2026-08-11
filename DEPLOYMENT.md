# Deployment & local setup

Operator guide for running and deploying the Documentation Helper Agent. For a product overview and the hosted demo, see [README.md](README.md).

## Architecture

Split deployment:

1. **Frontend UI** — Next.js on Vercel (auth, chat UI, API proxies)
2. **Backend agent** — FastAPI / LangGraph on Google Cloud Run

Optional: RunPod for the generator model while the API stays on Cloud Run.

Frontend deep-dive: [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md).

## Model configuration

The agent uses specialized models for different tasks. Choose Ollama (local) or an Inference API provider (cloud).

### Default model combination

- **Embeddings**: `BAAI/bge-large-en-v1.5`
- **Router**: `meta-llama/Meta-Llama-3.1-8B-Instruct`
- **Graders**:
  - Sentiment: `mistralai/Mistral-7B-Instruct-v0.3`
  - Answer: `mistralai/Mistral-7B-Instruct-v0.3`
  - Retrieval: `meta-llama/Meta-Llama-3.1-8B-Instruct`
  - Hallucination: `Qwen/Qwen2.5-14B-Instruct`
- **Summarizer**: `Qwen/Qwen2.5-14B-Instruct`
- **Generator**: `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct`

### Provider options

#### Local with Ollama

- Set `USE_OLLAMA=true` and `USE_INFERENCE_CLIENT=false`
- Requires Ollama running locally
- Uses models from `OLLAMA_MODELS`
- Best for development and testing

#### Cloud with Inference API

- Set `USE_OLLAMA=false` and `USE_INFERENCE_CLIENT=true`
- Providers such as Together AI, Perplexity, etc.
- Optional: `USE_RUNPOD=true` to offload the generator to RunPod
- Best for production

## Environment variables

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

# LangGraph long-term Store (app-level memory; chub package catalog for routing)
# Uses REDIS_URL when set. Set STORE_TYPE=memory to force InMemoryStore.
STORE_TYPE=redis  # Options: redis, memory (default: redis if REDIS_URL set, else memory)

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

### Firebase (UI auth)

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

## Installation & local run

1. Clone the repository:

```bash
git clone https://github.com/yourusername/documentation_helper_agent.git
cd documentation_helper_agent
```

2. Install dependencies:

```bash
pip install -r requirements.txt
npm install   # provides the chub CLI (@nrl-ai/chub)
```

3. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start the FastAPI server:

```bash
uvicorn agent.graph.app:app --reload
```

5. Send a request (example):

```bash
curl -X POST "http://localhost:8080/api/chat" \
     -H "Content-Type: application/json" \
     -d '{"query": "How do I implement a binary search tree?"}'
```

## Knowledge base ingestion

Docs are indexed into Pinecone via **Firecrawl** (site URLs) and/or **chub** (curated package guides). See [docs/ingestion.md](docs/ingestion.md).

```bash
python -m ingestion --source chub          # curated pins → Pinecone
python -m ingestion --source firecrawl     # scrape URL lists (needs FIRECRAWL_API_KEY)
python -m mcp_servers.chub_docs            # MCP: search / get / ingest for user packages
```

Related: [docs/chub-mcp-graph-integration.md](docs/chub-mcp-graph-integration.md).

## Backend deployment (Google Cloud Run)

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
# Build the Docker image (uses cloudbuild.yaml for layer caching via --cache-from)
gcloud builds submit --config cloudbuild.yaml

# Generate env.yaml from .env (required by --env-vars-file below).
# Note: env.yaml contains secrets - do not commit it. Also, --env-vars-file
# replaces ALL env vars on the service, so it must contain the complete set.
# Cloud Run expects a single JSON object with quoted keys and values, e.g.
# { "KEY": "value", "ANOTHER_KEY": "another_value" }
python scripts/env_to_yaml.py .env env.yaml

gcloud beta run deploy documentation-helper-agent \
  --image gcr.io/documentation-helper-agent/documentation-helper-agent:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --cpu 1 \
  --memory 2Gi \
  --env-vars-file=env.yaml

# see error logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=documentation-helper-agent AND resource.labels.revision_name=YOUR_REVISION_NAME" --format="table(textPayload)"
```

5. Set up CI/CD (optional):

- Connect your GitHub repo to Google Cloud Build
- Create a build trigger for automatic deployments

### Alternative: quick deploy with Dockerfile

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

## Frontend deployment (Vercel)

See [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md) for UI deployment, Vercel env vars, and the split-architecture proxy setup.

## RunPod integration (optional)

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

3. Benefits:
   - Reduces Cloud Run memory requirements
   - Pay-per-request pricing
   - Automatic scaling
   - High availability
   - Low latency

## Performance optimization

1. **Cold start**
   - Increase minimum instances on Cloud Run
   - Use the warm-up endpoint for Vercel functions
   - Optimize the container build for faster startup

2. **Resources**
   - Monitor memory usage on Cloud Run
   - Adjust CPU and memory as needed
   - Use appropriate timeout settings

3. **Cost**
   - Set maximum instances on Cloud Run
   - Monitor function execution times
   - Cache where possible

4. **Monitoring**
   - Cloud Monitoring for the backend
   - Vercel Analytics for the frontend
   - Watch error rates and latency
