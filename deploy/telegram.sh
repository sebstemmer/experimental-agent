#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source deploy/cluster.sh

IMAGE=ghcr.io/sebstemmer/experimental-agent:latest

docker build -t "$IMAGE" .
k3d image import "$IMAGE" -c "$CLUSTER"

kubectl apply -f deploy/k8s/telegram-bot-config.yaml -f deploy/k8s/telegram-bot.yaml

kubectl rollout restart deployment/telegram-bot
kubectl rollout status deployment/telegram-bot --timeout=180s
