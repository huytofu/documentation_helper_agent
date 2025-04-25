# Documentation Helper Agent: Graph Architecture

This folder contains the LangGraph-based agent implementation and various deployment entry points.

## Application Architecture

The application follows a modular architecture with a central `app.py` that contains the core FastAPI application and several entry point files for different deployment scenarios.

### Core Component
- **app.py**: Contains the FastAPI application definition, routes, and core logic

## Deployment Options

### 1. Serverless Deployment (AWS Lambda, Vercel)

In serverless deployments, the platform imports a handler from `serverless.py` that wraps the FastAPI application.

```
Serverless Platform → serverless.py → app.py
```

#### Files used:
- `app.py` - Core application
- `serverless.py` - Creates appropriate handler for the serverless platform
- Environment variables (including `SERVER_TYPE=aws lambda` or `SERVER_TYPE=vercel`)

#### Files not used:
- `server.py` - Not used in serverless deployments
- `asgi.py` - Not used in serverless deployments
- `wsgi.py` - Not used in serverless deployments

### 2. Local Development

For local development, `server.py` is run directly, which imports and runs the app with uvicorn.

```
python -m agent.graph.server → server.py → app.py
```

#### Files used:
- `app.py` - Core application
- `server.py` - Development server with environment checks and logging configuration
- Environment variables (with `SERVER_TYPE=local` or unset)

#### Files not used:
- `serverless.py` - Not used in local development
- `asgi.py` - Not used in local development
- `wsgi.py` - Not used in local development

### 3. Traditional Server Deployment

For traditional server deployments, use ASGI or WSGI servers that import the application from their respective entry points.

```
ASGI Server (Uvicorn/Daphne) → asgi.py → app.py
WSGI Server (Gunicorn/uWSGI) → wsgi.py → app.py
```

#### Files used:
- `app.py` - Core application
- `asgi.py` - For ASGI servers (Uvicorn, Hypercorn, Daphne)
  OR
- `wsgi.py` - For WSGI servers (Gunicorn, uWSGI)

#### Files not used:
- `server.py` - Not used in traditional server deployments
- `serverless.py` - Not used in traditional server deployments

## Quick Start

### Local Development
```bash
# Set environment variables
export SERVER_TYPE=local

# Run development server
python -m agent.graph.server
```

### Serverless Deployment (AWS Lambda)
```bash
# Set environment variables
export SERVER_TYPE="aws lambda"

# Deploy with Serverless Framework
serverless deploy
```

### Traditional Server Deployment
```bash
# ASGI server (Uvicorn)
uvicorn agent.graph.asgi:application

# WSGI server (Gunicorn)
gunicorn agent.graph.wsgi:application
``` 