#!/bin/bash

echo "Deploying to STAGING environment..."

docker stop rci-staging || true
docker rm rci-staging || true

docker build -t rci-streamlit:staging .

docker run -d --name rci-staging -p 8501:8501 rci-streamlit:staging

echo "Staging deployed at http://localhost:8501"