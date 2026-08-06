# experimental-agent

## Deployment

There are two targets, each with its own secrets: a local [k3d](https://k3d.io/) cluster and a
[k3s](https://k3s.io/) server.

Locally `deploy/local.sh` applies everything in one go. On the server the work is split — Ansible
provisions Postgres and the secrets once, GitHub Actions applies the bot manifests on every push.

### Local

**1. Create the secrets**

```bash
mkdir -p deploy/k8s/local-secrets
cp deploy/k8s/postgres-credentials.yaml.example deploy/k8s/local-secrets/postgres-credentials.yaml
cp deploy/k8s/telegram-bot-credentials.yaml.example deploy/k8s/local-secrets/telegram-bot-credentials.yaml
```

Fill both in. Generate the Postgres password with `openssl rand -base64 24`.

**2. Deploy**

```bash
./deploy/local.sh
```

### Server

**1. Create an SSH key for GitHub Actions**

```bash
ssh-keygen -t ed25519 -f deploy/ansible/github -N ""
```

**2. Add the repo secrets**

Settings → Secrets and variables → Actions:

- `SSH_KEY` — contents of `deploy/ansible/github`
- `SERVER_IP` — the server's IP address

**3. Create the production secrets**

```bash
mkdir -p deploy/k8s/prod-secrets
cp deploy/k8s/postgres-credentials.yaml.example deploy/k8s/prod-secrets/postgres-credentials.yaml
cp deploy/k8s/telegram-bot-credentials.yaml.example deploy/k8s/prod-secrets/telegram-bot-credentials.yaml
```

The cluster pulls the image from a private registry, so it needs a token. Under Settings →
Developer settings → Personal access tokens → Tokens (classic), generate a new token with only the
`read:packages` scope. Then:

```bash
kubectl create secret docker-registry ghcr \
  --docker-server=ghcr.io \
  --docker-username=<github-user> \
  --docker-password=<token> \
  --dry-run=client -o yaml > deploy/k8s/prod-secrets/ghcr-credentials.yaml
```

**4. Create the Ansible inventory**

```bash
cp deploy/ansible/inventory.yml.example deploy/ansible/inventory.yml
```

Fill in the server IP and the path to the SSH key you use for root access.

**5. Provision the server**

```bash
cd deploy/ansible && ansible-playbook -i inventory.yml setup.yml
```

**6. Deploy**

Push to `main`. The workflow in `.github/workflows/deploy.yml` builds the image, pushes it to
ghcr.io tagged with both `latest` and the commit SHA, pipes the bot manifests over SSH into
`kubectl apply` and waits for the rollout.
