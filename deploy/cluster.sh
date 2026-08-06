#!/usr/bin/env bash

CLUSTER=exp-agent-dev

if k3d cluster list "$CLUSTER" >/dev/null 2>&1; then
  k3d cluster start "$CLUSTER"
else
  k3d cluster create "$CLUSTER" -p "30432:30432@server:0"
fi

kubectl config use-context "k3d-$CLUSTER"

kubectl apply \
  -f deploy/k8s/postgres-config.yaml \
  -f deploy/k8s/postgres-pvc.yaml \
  -f deploy/k8s/postgres.yaml \
  -f deploy/k8s/local-secrets/
