# GCE Deployment Guide

## Prerequisites

1. Google Cloud SDK installed and configured
2. Docker installed
3. kubectl installed
4. GCP project with billing enabled

## Quick Deploy

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"

# Run the deployment script
./build-gce.sh $PROJECT_ID us-central1 activcv-cluster
```

## Manual Deployment Steps

### 1. Enable Required APIs

```bash
gcloud services enable container.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 2. Build and Push Image

```bash
cd agent
gcloud builds submit --tag gcr.io/$PROJECT_ID/activcv-backend:latest .
```

### 3. Create GKE Cluster

```bash
gcloud container clusters create activcv-cluster \
    --region=us-central1 \
    --num-nodes=2 \
    --machine-type=e2-medium \
    --enable-autoscaling \
    --min-nodes=1 \
    --max-nodes=5
```

### 4. Deploy Application

```bash
# Get cluster credentials
gcloud container clusters get-credentials activcv-cluster --region=us-central1

# Update deployment configuration
sed "s/PROJECT_ID/$PROJECT_ID/g" gce-deploy.yaml > gce-deploy-configured.yaml

# Deploy
kubectl apply -f gce-deploy-configured.yaml
```

### 5. Get External IP

```bash
kubectl get service activcv-backend-service
```

## Environment Variables

Copy `agent/.env.production` to `agent/.env` and configure:

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anon key
- `GOOGLE_API_KEY`: Your Google Gemini API key
- `JWT_SECRET`: Random secret for JWT signing

## Monitoring

```bash
# Check deployment status
kubectl get deployments

# View logs
kubectl logs -l app=activcv-backend

# Scale deployment
kubectl scale deployment activcv-backend --replicas=3
```

## Cleanup

```bash
# Delete deployment
kubectl delete -f gce-deploy-configured.yaml

# Delete cluster
gcloud container clusters delete activcv-cluster --region=us-central1
```
