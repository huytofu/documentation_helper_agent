# documentation_helper_agent

# This Repo is coding an agent that can help you code by referring to packages/frameworks' documentation
## List of supported packages/frameworks:
1. LangChain
2. LangGraph
3. CopilotKit

### Built with LangChain + LangGraph + CopilotKit
   
## Server Configuration

The application has been refactored to support both traditional and serverless deployments:

### File Structure

- `agent/graph/app.py`: Contains the FastAPI application definition
- `agent/graph/server.py`: Contains the server startup code for local development
- `agent/graph/wsgi.py`: Exports the app for WSGI servers (e.g., Gunicorn)
- `agent/graph/asgi.py`: Exports the app for ASGI servers (e.g., Uvicorn, Hypercorn)
- `agent/graph/serverless.py`: Provides handlers for serverless platforms

### Running Locally

```bash
# Run with the development server
python -m agent.graph.server

# Run with Uvicorn directly
uvicorn agent.graph.app:app --host 0.0.0.0 --port 8000

# Run with Gunicorn (WSGI)
gunicorn agent.graph.wsgi:application

# Run with Uvicorn as an ASGI server
uvicorn agent.graph.asgi:application
```

### Serverless Deployment

The application supports multiple serverless platforms through the `SERVER_TYPE` environment variable:

#### AWS Lambda

```bash
# Set the environment variable
export SERVER_TYPE="aws lambda"

# Deploy using your preferred method (e.g., AWS SAM, Serverless Framework)
# Example serverless.yml
functions:
  app:
    handler: agent.graph.serverless.handler
    events:
      - http:
          path: /{proxy+}
          method: any
```

#### Azure Functions

```bash
# Set the environment variable
export SERVER_TYPE="azure functions"

# In your function.json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "authLevel": "anonymous",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": ["get", "post", "put", "delete", "options", "head", "patch"],
      "route": "{*route}"
    },
    {
      "type": "http",
      "direction": "out",
      "name": "$return"
    }
  ]
}

# In your __init__.py
from agent.graph.serverless import main
```

#### Google Cloud Functions

```bash
# Set the environment variable
export SERVER_TYPE="google cloud functions"

# In your main.py
from agent.graph.serverless import gcp_handler

# Export the handler
def handle_request(request):
    return gcp_handler(request)
```

#### Vercel

```bash
# Set the environment variable
export SERVER_TYPE="vercel"

# In your vercel.json
{
  "version": 2,
  "builds": [
    {
      "src": "agent/graph/serverless.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "agent/graph/serverless.py"
    }
  ]
}
```
   
## Persistent State Management

The application supports multiple state persistence options through the `CHECKPOINTER_TYPE` environment variable:

### Checkpointer Types

#### Memory (Default)

```bash
# Set the environment variable
export CHECKPOINTER_TYPE=memory
```

This is the default option and stores state in memory. State is lost when the server restarts or between serverless function invocations.

#### Vercel KV (Redis)

```bash
# Set the environment variable
export CHECKPOINTER_TYPE=vercel_kv

# Required Vercel KV environment variables
export KV_URL=your_kv_url
export KV_REST_API_URL=your_kv_rest_api_url
export KV_REST_API_TOKEN=your_kv_rest_api_token
export KV_REST_API_READ_ONLY_TOKEN=your_kv_rest_api_read_only_token
```

This option stores state in Vercel KV (Redis), providing persistence across serverless function invocations. It's ideal for Vercel deployments.

To set up Vercel KV:
1. Add the Vercel KV integration to your Vercel project
2. Copy the KV environment variables from your Vercel project settings
3. Add them to your `.env` file or environment

#### PostgreSQL

```bash
# Set the environment variable
export CHECKPOINTER_TYPE=postgres

# Required PostgreSQL environment variable
export DATABASE_URL=postgresql://username:password@hostname:port/database
```

This option stores state in a PostgreSQL database, providing persistence across serverless function invocations. It works with any cloud provider's PostgreSQL service:
- AWS RDS
- Google Cloud SQL
- Azure Database for PostgreSQL
- Digital Ocean Managed PostgreSQL

To set up PostgreSQL:
1. Create a PostgreSQL database in your cloud provider
2. Get the connection string for your database
3. Add it to your `.env` file or environment as `DATABASE_URL`
   
## Vector Store Configuration

The application supports multiple vector store options through the `VECTOR_STORE_TYPE` environment variable:

### Vector Store Types

#### Chroma (Default)

```bash
# Set the environment variable
export VECTOR_STORE_TYPE=chroma
```

This is the default option and stores vectors in a local Chroma database. It's ideal for local development and testing.

#### Pinecone

```bash
# Set the environment variable
export VECTOR_STORE_TYPE=pinecone

# Required Pinecone environment variables
export PINECONE_API_KEY=your_pinecone_api_key
export PINECONE_ENVIRONMENT=your_pinecone_environment
export PINECONE_INDEX_NAME=your_pinecone_index_name
```

This option stores vectors in Pinecone, providing persistence and scalability for serverless deployments.

To set up Pinecone:
1. Create a Pinecone account at https://www.pinecone.io/
2. Create a new index with the appropriate dimensions (1536 for most embedding models)
3. Get your API key and environment from the Pinecone console
4. Add them to your `.env` file or environment
   
