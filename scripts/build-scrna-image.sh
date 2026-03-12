#!/bin/bash
# Build and push the bioaf-scrna Docker image to Artifact Registry.
#
# Usage: ./scripts/build-scrna-image.sh <registry_url>
# Example: ./scripts/build-scrna-image.sh us-central1-docker.pkg.dev/bioaf-489516/bioaf-images

set -euo pipefail

REGISTRY_URL="${1:-}"
IMAGE_NAME="bioaf-scrna"
TAG="latest"

if [ -z "$REGISTRY_URL" ]; then
  echo "Usage: $0 <registry_url>"
  echo "Example: $0 us-central1-docker.pkg.dev/my-project/bioaf-images"
  exit 1
fi

# Authenticate Docker to Artifact Registry
REGISTRY_HOST=$(echo "$REGISTRY_URL" | cut -d'/' -f1)
echo "Authenticating Docker to ${REGISTRY_HOST}..."
gcloud auth configure-docker "$REGISTRY_HOST"

# Build
echo "Building ${IMAGE_NAME}:${TAG}..."
docker build -t "${REGISTRY_URL}/${IMAGE_NAME}:${TAG}" -f docker/Dockerfile.bioaf-scrna .

# Push
echo "Pushing to ${REGISTRY_URL}/${IMAGE_NAME}:${TAG}..."
docker push "${REGISTRY_URL}/${IMAGE_NAME}:${TAG}"

echo ""
echo "Image pushed to ${REGISTRY_URL}/${IMAGE_NAME}:${TAG}"
echo "Update platform_config.bioaf_scrna_image with this URI."
