#!/bin/bash
# Deploy PDF generation Lambda via AWS SAM (container image)
#
# Prerequisites:
#   brew install awscli aws-sam-cli docker
#   aws configure  (enter your IAM access key + secret)
#   Docker must be running (SAM builds the container image locally)
#
# Usage:
#   cd cloud-function/deploy
#   ./deploy.sh
#
# First run uses --guided for interactive setup.
# Subsequent runs reuse saved config in samconfig.toml.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Building SAM application (container image)..."
sam build --template-file template.yaml --use-container

if [ -f samconfig.toml ]; then
    echo "Deploying (using saved config)..."
    sam deploy --image-repository ""
    echo ""
    echo "NOTE: If deploy fails with 'image repository not found', run:"
    echo "  sam deploy --guided"
    echo "and accept the ECR repo creation prompt."
else
    echo "First deployment — running guided setup..."
    echo "  Stack name suggestion: endurance-pdf-generator"
    echo "  Region suggestion: us-east-1"
    echo "  Say YES when asked to create an ECR repository"
    echo ""
    sam deploy --guided
fi

echo ""
echo "Deployment complete!"
echo "Copy the ApiUrl from the outputs above and update CLOUD_FUNCTION_URL in crew.html"
