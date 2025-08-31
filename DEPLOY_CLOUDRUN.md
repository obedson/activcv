# Cloud Run Deployment Guide - MVP Testing

## Why Cloud Run for MVP?

- **Cost**: Pay only when requests are processed (scales to zero)
- **Free Tier**: 2M requests/month, 360,000 GB-seconds/month
- **No Infrastructure**: Fully managed, no cluster fees
- **Fast Deployment**: Deploy directly from source code

## Quick Deploy

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"

# Deploy both frontend and backend
./deploy-cloudrun.sh $PROJECT_ID
```

## Manual Deployment

### 1. Enable APIs
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### 2. Deploy Backend
```bash
cd agent
gcloud run deploy activcv-backend \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 512Mi \
    --max-instances 10
```

### 3. Deploy Frontend
```bash
cd web
gcloud run deploy activcv-frontend \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 256Mi \
    --max-instances 5
```

## Environment Setup

1. Copy `agent/.env.production` to `agent/.env`
2. Fill in your Supabase and Google API credentials
3. Frontend will automatically get backend URL during deployment

## Cost Estimation (MVP)

- **Free Tier**: Up to 2M requests/month = $0
- **Beyond Free**: ~$0.40 per 1M requests
- **Memory**: ~$0.0000025 per GB-second
- **CPU**: ~$0.0000100 per vCPU-second

**Typical MVP cost**: $0-5/month

## Monitoring

```bash
# View logs
gcloud run services logs read activcv-backend --region=us-central1

# Check service status
gcloud run services list
```

## Scaling

Cloud Run automatically scales:
- **0 instances** when no traffic (saves money)
- **Up to max instances** during traffic spikes
- **Concurrent requests** per instance: 80-100

Perfect for MVP testing with unpredictable traffic!
