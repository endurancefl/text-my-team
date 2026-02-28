#!/bin/bash
# Redeploy PDF Lambda container image (after initial guided setup is done)
#
# Use this for routine redeployments when you've changed:
#   - lambda_function.py, pdf_generator.py, main.py
#   - templates/, assets/
#   - Dockerfile, requirements.txt
#
# Prerequisites:
#   - Docker Desktop running (whale icon in menu bar)
#   - samconfig.toml already populated (from initial `sam deploy --guided`)
#
# Usage:
#   cd cloud-function/deploy
#   ./deploy-docker.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Verify Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running. Open Docker Desktop first."
    exit 1
fi

# Verify samconfig.toml has ECR repo
if ! grep -q "image_repositories" samconfig.toml 2>/dev/null; then
    echo "ERROR: samconfig.toml missing image_repositories."
    echo "Run 'sam deploy --guided' first to create the ECR repo."
    exit 1
fi

echo "Building Docker image..."
sam build --template-file template.yaml

echo ""
echo "Deploying to AWS..."
sam deploy --no-confirm-changeset

echo ""
echo "Deployment complete!"
echo "Endpoint: https://ibjyxrp542.execute-api.us-east-1.amazonaws.com/prod/generate_site_report"
