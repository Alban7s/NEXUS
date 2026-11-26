.# NEXUS — Live Data Foundation

NEXUS is an upload-first release control plane. Upload one `.zip` containing a static website or Node-built frontend; NEXUS inspects it, builds it, applies the available release gates, publishes it when a registry target exists, deploys it, and records what it could actually verify.

## Current live integrations

- Kubernetes API
- Prometheus
- GitHub Actions
- Argo CD
- AWS EKS / ECR discovery
- Deploy pipeline: upload → inspect → build → security check → publish → deploy → verify

## Explicitly not connected yet

- Loki logs
- Security findings
- AWS Cost Explorer
- Aggregated SLO/MTTR/deployment-frequency metrics

Those endpoints return `NOT CONNECTED` rather than fabricating values.

## Deploy pipeline — how it works

Upload a `.zip` from the release intake card (or `POST /api/deploy`, multipart
field `file`, optional `app_name`). When the name is blank, the server derives a
safe name from the root `package.json`, wrapping directory, or archive name.
NEXUS then:

1. **Inspects and gates** the archive before build. ZIP path traversal, symbolic
   links, nested ZIPs, source-control metadata, `.env` files, and common private
   credential/key files are rejected without reading their contents into logs.
2. **Detects** the project — a `package.json` with a `build` script is treated as a
   buildable app (React/Vue/Vite/CRA/etc., anything that ends up outputting static
   files to `build/`, `dist/`, or `out/`); anything else is treated as a static site.
3. **Builds** a container image (a `Dockerfile` and `nginx.conf` are generated on the
   fly — you don't need to include your own, though a build-step app does need its own
   `package.json` with a working `build` script). NPM projects with `package-lock.json`
   or `npm-shrinkwrap.json` use `npm ci` for reproducible installs.
4. **Runs a real security scan only when Trivy is available.** Otherwise the security
   scan stage is explicitly marked `skipped`; NEXUS does not claim a clean scan.
5. **Publishes** the image to ECR, if `ECR_REPOSITORY_PREFIX` is configured. Repos are
   created automatically per app name.
6. **Deploys**, choosing a mode automatically:
   - **GitOps** (recommended) — if `GIT_REPO_URL` + `ARGOCD_URL` are both set, NEXUS
     commits generated Kubernetes manifests to that repo and lets Argo CD sync them.
     Every deploy is a commit; rollback is `git revert`.
   - **Direct** — if there's no GitOps repo but the Kubernetes API is reachable and
     `ECR_REPOSITORY_PREFIX` is set, NEXUS applies the manifests itself via the
     Kubernetes API.
   - **Local** — if nothing above is configured, NEXUS runs the built image with
     `docker run` on its own host and hands back a `http://<host>:<port>` preview
     link. Zero cloud infra required to see something running.
7. **Verifies** the rollout (direct mode polls pod availability; local mode confirms
   the container is up; GitOps verification happens in Argo CD once it syncs).

Every stage streams a real `pending`, `running`, `success`, `failed`, or `skipped`
state plus logs over SSE at
`GET /api/deploy/jobs/{id}/stream`. Recent runs are listed at `GET /api/deploy/jobs`.

### Requirements for the pipeline specifically

- **Docker**: NEXUS needs to reach a Docker daemon to build/run images. Run it with
  the host's Docker socket mounted, e.g. add
  `- /var/run/docker.sock:/var/run/docker.sock` under `volumes:` in
  `docker-compose.yml`. (Mounting the docker socket gives the NEXUS container the
  same power as root on the host — fine on a machine you control, not something to
  expose publicly without further sandboxing.)
- **git** CLI, for GitOps mode — already present in the `python:3.12-slim` base image
  is not guaranteed; the Dockerfile installs it explicitly.
- **`NEXUS_API_KEY`**: set this before putting the upload endpoint on any network
  beyond your own machine. Without it, anyone who can reach NEXUS can trigger builds
  and deploys. When configured, the UI exposes an in-memory deployment access-key
  field; it is sent only with the upload request and is never stored. Production should
  use real user authentication and a dedicated, isolated build runner.

See `.env.example` for every pipeline-related setting.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
uvicorn backend.app:app --reload
```

Open:

http://localhost:8000

## Important

For Kubernetes, the backend uses the normal Kubernetes Python client loading rules:

1. in-cluster config when running inside Kubernetes
2. local kubeconfig when running locally

For AWS, use the normal boto3 credential chain. Never put long-lived secrets in frontend JavaScript.

## First milestone

Connect at least one real source (for example Kubernetes or Prometheus). NEXUS will show LIVE data for that integration and NOT CONNECTED for everything else.

Next milestones:

1. deploy NEXUS itself with Docker
2. create the actual application workload
3. create Terraform AWS infrastructure
4. deploy to EKS
5. install Prometheus/Grafana
6. add GitHub Actions
7. add Argo CD
8. add Trivy/security ingestion
9. add Loki
10. add Cost Explorer
11. replace remaining unavailable endpoints with live data

## Deployment Verification

- Local Kubernetes: Kind
- Local replicas: 2
- EKS workload: AWS Fargate
- Container registry: Amazon ECR
# Webhook test
