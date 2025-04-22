# Vercel Deployment Guide

This guide explains how to deploy the documentation helper agent project to Vercel as a monorepo.

## Prerequisites

- A Vercel account
- Git repository with your code
- Vercel CLI installed (optional, for local testing)

## Deployment Steps

### 1. Prepare Your Repository

Ensure your repository has the following structure:
- UI code in the `ui/` directory
- Backend code in the main directory
- `vercel.json` in the root directory
- `.env.example` file with required environment variables

**Important**: Both frontend and backend will use the same `.env` file located at the root directory. During deployment, our build script will automatically create a symbolic link to ensure the UI also has access to these environment variables.

### 2. Connect to Vercel

#### Using Vercel Dashboard:

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "Add New" > "Project"
3. Import your Git repository
4. Configure project:
   - Framework Preset: "Next.js"
   - Root Directory: "./documentation_helper_agent" (if needed)
   - Build Command: `./build.sh` (uses our custom build script)
   - Output Directory: `ui/.next`
   - Install Command: No need to change, handled in build.sh

#### Using Vercel CLI:

```bash
# Navigate to your project
cd documentation_helper_agent

# Login to Vercel
vercel login

# Deploy to Vercel
vercel
```

### 3. Configure Environment Variables

After initial deployment, you need to set up your environment variables:

1. In the Vercel dashboard, go to your project
2. Navigate to "Settings" > "Environment Variables"
3. Add all required variables from your `.env.example` file
4. Click "Save"

Critical environment variables include:
- `OPENAI_API_KEY`
- `PYTHONPATH`
- `NEXT_PUBLIC_API_URL=/api`

**Note**: Vercel will automatically make these environment variables available to both the frontend and backend due to our monorepo configuration. The `NEXT_PUBLIC_` prefix is required for variables that need to be accessible in the browser.

### 4. Local Development

For local development, create a `.env` file in the root directory by copying `.env.example`:

```bash
cp .env.example .env
```

Then edit the `.env` file to include your actual API keys and configuration.

### 5. Verify Deployment

1. Check the deployment logs for any errors
2. Test your application at the provided Vercel URL
3. Verify API endpoints are working correctly

### 6. Custom Domain (Optional)

1. In Vercel dashboard, go to your project
2. Click "Settings" > "Domains"
3. Add your custom domain and follow the verification steps

## Troubleshooting

If you encounter issues:

1. Check Vercel build logs for errors
2. Ensure all environment variables are correctly set
3. Verify the `vercel.json` configuration is correct
4. Check that Python and Node.js dependencies are installed correctly
5. If environment variables aren't being shared correctly, check that the symbolic link was created during build

## Local Testing

Test your Vercel configuration locally before deploying:

```bash
# Install Vercel CLI
npm install -g vercel

# Link your project
vercel link

# Test builds locally
vercel build

# Run locally
vercel dev
``` 