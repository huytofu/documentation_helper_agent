@echo off
echo Building and pushing Docker image... && ^
gcloud builds submit --tag gcr.io/documentation-helper-agent/documentation-helper-agent && ^
echo Deploying to Cloud Run... && ^
gcloud beta run deploy documentation-helper-agent ^
  --image gcr.io/documentation-helper-agent/documentation-helper-agent ^
  --platform managed ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --cpu 1 ^
  --memory 2Gi ^
  --env-vars-file=env.yaml && ^
echo Deployment complete! 