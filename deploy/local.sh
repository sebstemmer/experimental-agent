#!/usr/bin/env bash
set -euo pipefail

CLUSTER=exp-agent-dev
IMAGE=ghcr.io/sebstemmer/experimental-agent:latest

cd "$(dirname "$0")/.."

if k3d cluster list "$CLUSTER" >/dev/null 2>&1; then
  k3d cluster start "$CLUSTER"
else
  k3d cluster create "$CLUSTER" -p "30432:30432@server:0"
fi
kubectl config use-context "k3d-$CLUSTER"

docker build -t "$IMAGE" .
k3d image import "$IMAGE" -c "$CLUSTER"

kubectl apply -f deploy/k8s/ -f deploy/k8s/local-secrets/

kubectl rollout restart deployment/telegram-bot
kubectl rollout status deployment/telegram-bot --timeout=180s
