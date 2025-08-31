#!/bin/bash

# Cloud Run Deployment Script for ActivCV MVP
set -e

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}

echo "Deploying ActivCV to Cloud Run..."
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"

# Enable required APIs
echo "Enabling Cloud Run API..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Build and deploy backend
echo "Building and deploying backend..."
cd agent
gcloud run deploy activcv-backend \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 10 \
    --project $PROJECT_ID

# Get backend URL
BACKEND_URL=$(gcloud run services describe activcv-backend --region=$REGION --format="value(status.url)")
echo "Backend deployed at: $BACKEND_URL"

cd ../web

# Update frontend environment for backend URL
echo "NEXT_PUBLIC_API_URL=$BACKEND_URL" > .env.production

# Build and deploy frontend
echo "Building and deploying frontend..."
gcloud run deploy activcv-frontend \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 256Mi \
    --cpu 0.5 \
    --max-instances 5 \
    --project $PROJECT_ID

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe activcv-frontend --region=$REGION --format="value(status.url)")

echo ""
echo "🚀 Deployment Complete!"
echo "Frontend: $FRONTEND_URL"
echo "Backend: $BACKEND_URL"
echo ""
echo "💰 Cost: Pay-per-request (scales to zero when not used)"
