#!/bin/bash
# Deploy PDF generation Lambda via AWS SAM
#
# Prerequisites:
#   brew install awscli aws-sam-cli
#   aws configure  (enter your IAM access key + secret)
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

echo "Building SAM application..."
sam build --template-file template.yaml

if [ -f samconfig.toml ]; then
    echo "Deploying (using saved config)..."
    sam deploy
else
    echo "First deployment — running guided setup..."
    echo "  Stack name suggestion: endurance-pdf-generator"
    echo "  Region suggestion: us-east-1"
    echo ""
    sam deploy --guided
fi

echo ""
echo "Deployment complete!"
echo "Copy the ApiUrl from the outputs above and update CLOUD_FUNCTION_URL in crew.html"
