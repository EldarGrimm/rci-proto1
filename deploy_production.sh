#!/bin/bash

echo "Deploying to PRODUCTION..."

docker stop rci-production || true
docker rm rci-production || true

docker build -t rci-streamlit:prod .

docker run -d --name rci-production -p 9001:8501 rci-streamlit:prod

echo "Production deployed at http://localhost:9001"
