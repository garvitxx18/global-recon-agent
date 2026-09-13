# Global Recon ADK agent

Standard Google ADK agent for the Global Recon chat workspace.

The agent talks to the existing Java APIs. It does not compute MATCHED / BREAK
itself. Java still profiles files, validates mappings, and runs reconciliation.

```text
Chat UI
   ↓
root_agent (Gemini)
   ↓
tools
   ↓
Global Recon Java service
```

Copy `app/global_recon/` into a company ADK repo if you later move this into an
enterprise template. Only `MODEL` in `agent.py` should need to change.

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Point `.env` at a running recon service and a user email:

```bash
RECON_API_BASE_URL=http://127.0.0.1:8080
RECON_USER_EMAIL=tester@company.com
```

For local Gemini, either set `GOOGLE_API_KEY` or use Vertex:

```bash
export GOOGLE_CLOUD_PROJECT=your-gcp-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=true
gcloud auth application-default login
```

```bash
pytest
adk web app
```

The ADK UI should list `global_recon`.

## GitHub Actions → Cloud Run

The workflow is already in `.github/workflows/deploy-cloud-run.yml`.
It runs tests, builds the Docker image, pushes it to Artifact Registry, and
deploys Cloud Run. You still have to connect GitHub to your GCP project.

### 1. Enable GCP APIs

In the GCP project you already created:

```bash
gcloud config set project YOUR_PROJECT_ID

gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iamcredentials.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com
```

### 2. Artifact Registry

```bash
gcloud artifacts repositories create adk-agents \
  --repository-format=docker \
  --location=us-central1
```

Use the same region later as `GCP_REGION`.

### 3. Deployer service account

```bash
gcloud iam service-accounts create github-adk-deployer \
  --display-name="GitHub Actions ADK deployer"

PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
DEPLOY_SA="github-adk-deployer@$PROJECT_ID.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/aiplatform.user"
```

Cloud Run runtime uses the default compute service account. That account also
needs Vertex AI access:

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA" \
  --role="roles/aiplatform.user"
```

### 4. Workload Identity Federation for GitHub

This is the part GitHub Actions needs. Do not upload a JSON key.

```bash
gcloud iam workload-identity-pools create github-pool \
  --location=global \
  --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc github \
  --location=global \
  --workload-identity-pool=github-pool \
  --display-name="GitHub" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor" \
  --attribute-condition="assertion.repository=='garvitxx18/global-recon-agent'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/garvitxx18/global-recon-agent"
```

Provider resource name:

```text
projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github
```

### 5. GitHub repository variables

In the GitHub repo: **Settings → Secrets and variables → Actions → Variables**

| Variable | Example |
|---|---|
| `GCP_PROJECT_ID` | your GCP project id |
| `GCP_REGION` | `us-central1` |
| `WIF_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github` |
| `WIF_SERVICE_ACCOUNT` | `github-adk-deployer@PROJECT_ID.iam.gserviceaccount.com` |
| `RECON_API_BASE_URL` | public or VPC URL of the Java recon service |
| `RECON_USER_EMAIL` | default email the agent sends as `X-User-Email` |

Create a GitHub Environment named `cloud-run` (the workflow uses it). You can
leave protection rules off until you want approvals.

### 6. Network

Cloud Run must reach the Java service. If recon is only on localhost, the
deployed agent cannot call it. Use a deployed recon URL, Cloud Run service-to-service,
or a tunnel.

`RECON_USER_EMAIL` is a temporary default. The chat UI should later pass the
signed-in user into the ADK session so the agent does not share one email.

### 7. First deploy

Push to `main` or run the workflow from **Actions → Deploy Global Recon agent to Cloud Run → Run workflow**.

After it succeeds, open the Cloud Run URL. The ADK API server is there.
For a browser chat during bring-up you can also deploy once with UI:

```bash
adk deploy cloud_run \
  --project="$GOOGLE_CLOUD_PROJECT" \
  --region="$GOOGLE_CLOUD_LOCATION" \
  --service_name=global-recon-agent \
  --with_ui \
  app/global_recon
```

Prefer the GitHub Actions Docker path for repeatable deploys.

### 8. If the workflow fails

- `WIF_PROVIDER` / `WIF_SERVICE_ACCOUNT` mismatch → auth step fails
- Artifact Registry repo `adk-agents` missing → docker push fails
- Vertex AI API or `roles/aiplatform.user` missing → agent starts but model calls fail
- `RECON_API_BASE_URL` unreachable → tools return `success: false`

## What the agent can call

These are real Java endpoints. No extra recon APIs were invented.

| Tool | API |
|---|---|
| `upload_dataset` | `POST /api/v1/datasets` |
| `get_dataset` | `GET /api/v1/datasets/{id}` |
| `get_dataset_profile` | `GET /api/v1/datasets/{id}/profile` |
| `get_dataset_records` | `GET /api/v1/datasets/{id}/records` |
| `discover_recon_plan` | `POST /api/v1/recon-plans/discover` then poll job |
| `get_recon_plan` / `update_recon_plan` / `approve_recon_plan` | plan APIs |
| `start_recon_run` | `POST /api/v1/recon-runs` then poll job |
| `get_recon_run` / `get_recon_summary` / `get_recon_results` | run APIs |
| `save_comparison` / `list_comparisons` | comparison APIs |

A future repeat-job screen (`planId` + two new files, no discovery) still needs
a Java endpoint. This agent will not pretend that API exists.
