#!/bin/bash

# GCE Deployment Script for ActivCV
set -e

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
CLUSTER_NAME=${3:-"activcv-cluster"}

echo "Building and deploying ActivCV to GCE..."
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Cluster: $CLUSTER_NAME"

# Build and push backend image
echo "Building backend image..."
cd agent
gcloud builds submit --tag gcr.io/$PROJECT_ID/activcv-backend:latest .
cd ..

# Build and push frontend image
echo "Building frontend image..."
cd web
gcloud builds submit --tag gcr.io/$PROJECT_ID/activcv-frontend:latest .
cd ..

# Create GKE cluster if it doesn't exist
echo "Checking for GKE cluster..."
if ! gcloud container clusters describe $CLUSTER_NAME --region=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo "Creating GKE cluster..."
    gcloud container clusters create $CLUSTER_NAME \
        --region=$REGION \
        --num-nodes=2 \
        --machine-type=e2-medium \
        --enable-autoscaling \
        --min-nodes=1 \
        --max-nodes=5 \
        --project=$PROJECT_ID
fi

# Get cluster credentials
echo "Getting cluster credentials..."
gcloud container clusters get-credentials $CLUSTER_NAME --region=$REGION --project=$PROJECT_ID

# Update deployment with project ID
sed "s/PROJECT_ID/$PROJECT_ID/g" gce-deploy.yaml > gce-deploy-configured.yaml

# Deploy to GKE
echo "Deploying to GKE..."
kubectl apply -f gce-deploy-configured.yaml

# Wait for deployments
echo "Waiting for deployments to be ready..."
kubectl rollout status deployment/activcv-backend
kubectl rollout status deployment/activcv-frontend

# Get service IPs
echo "Getting service external IPs..."
kubectl get services

echo "Deployment complete!"
echo "Frontend URL: http://$(kubectl get service activcv-frontend-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
echo "Backend URL: http://$(kubectl get service activcv-backend-service -o jsonpath='{.spec.clusterIP}')"
