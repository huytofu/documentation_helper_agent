# Vercel Deployment Guide

This guide outlines how to deploy the Documentation Helper Agent using a split architecture:
- **Frontend UI**: Deployed on Vercel
- **Backend Agent**: Deployed on Google Cloud Run

This approach solves the 50MB size limit issue with Vercel serverless functions while maintaining a responsive user interface.

## Architecture Overview

```
┌───────────────┐     ┌────────────────┐     ┌─────────────────┐
│  User Browser │────▶│  Vercel (UI)   │────▶│  Cloud Run (API) │
└───────────────┘     └────────────────┘     └─────────────────┘
                            │                        │
                            │                        ▼
                            │                ┌─────────────────┐
                            └───────────────▶│ RunPod (Optional)│
                                             └─────────────────┘
```

## Frontend Deployment (Vercel)

The Vercel deployment includes:
- Next.js UI application
- Minimal API routes that proxy requests to the backend
- Authentication handling via Firebase

### Prerequisites

1. A Vercel account
2. The Vercel CLI installed (`npm i -g vercel`)
3. Firebase project (for authentication)

### Steps

1. Create a UI-specific requirements file:
   - A minimal `ui/requirements.txt` is included in the repository

2. Configure environment variables in Vercel:
   ```bash
   # UI Configuration
   NEXT_PUBLIC_API_URL=your_backend_service_on_serverless
   FRONTEND_URL=your_vercel_domain
   BACKEND_URL=your_cloud_run_url
   
   # Firebase Configuration
   NEXT_PUBLIC_FIREBASE_API_KEY=xxx
   NEXT_PUBLIC_FIREBASE_PROJECT_ID=xxx
   FIREBASE_CLIENT_EMAIL=xxx
   FIREBASE_PRIVATE_KEY=xxx
   
   # API Security
   DOCUMENTATION_HELPER_API_KEY=your_api_key
   
   # Model Configuration
   USE_INFERENCE_CLIENT=true
   INFERENCE_API_KEY=your_inference_api_key
   INFERENCE_PROVIDER=together
   ```

3. Deploy to Vercel:
   ```bash
   vercel
   ```

4. Update API proxy configuration:
   - In `ui/app/api/copilotkit/route.ts`, ensure your backend URL is correctly set

## Backend Deployment (Google Cloud Run)

The Google Cloud Run deployment includes:
- FastAPI backend with LangGraph agent
- Model inference handling
- Vector database connections

See `README.md` for detailed Google Cloud Run deployment instructions.

## Testing the Deployment

1. Check that the UI loads properly on your Vercel domain
2. Test authentication flow
3. Send a test query and ensure it's routed to your Cloud Run backend
4. Check logs on both Vercel and Cloud Run for any errors

## Common Issues

### CORS Configuration

If you encounter CORS issues, ensure your Cloud Run service has the appropriate headers:

```python
# In your FastAPI app.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Environment Variables

- Double-check Firebase configuration in Vercel
- Ensure API keys are set in both environments
- Verify the `BACKEND_URL` is correctly set and accessible

### Authentication Issues

- Firebase admin SDK requires properly formatted private key
- Use environment secret for storing `FIREBASE_PRIVATE_KEY`
- Replace newlines with `\n` in the private key if necessary

## Monitoring

- Set up Vercel Analytics for frontend
- Configure Google Cloud Monitoring for backend
- Set up error alerting for both platforms 