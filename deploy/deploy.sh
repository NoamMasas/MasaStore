#!/usr/bin/env bash
# MasaStore → Google Cloud. One subcommand per stage so each can be reviewed
# and run on its own. See docs/DEPLOYMENT.md for the architecture and costs.
#
#   deploy/deploy.sh <apis|network|iam|secrets|registry|build|vm|api|ui|budget|killswitch|reopen|status|destroy>
#
# Prereqs: gcloud CLI, `gcloud auth login`, `gcloud config set project <id>`,
# billing linked. Run from the repo root (Git Bash / Cloud Shell / Linux / macOS).
# Secrets are generated or piped straight into Secret Manager and never printed.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"          # Always Free e2-micro region + Cloud Run tier 1
ZONE="${ZONE:-us-central1-a}"
REPO=masastore
NETWORK=masastore-vpc
SUBNET=masastore-subnet
SUBNET_RANGE=10.10.0.0/24
DATA_VM=masastore-data
DATA_VM_IP=10.10.0.10
DATA_TAG=masastore-data
IAP_RANGE=35.235.240.0/20                # Google's IAP TCP-forwarding range (SSH only)
API_SERVICE=masastore-api
UI_SERVICE=masastore-ui
SA_API="masastore-api@${PROJECT_ID}.iam.gserviceaccount.com"
SA_UI="masastore-ui@${PROJECT_ID}.iam.gserviceaccount.com"
SA_VM="masastore-vm@${PROJECT_ID}.iam.gserviceaccount.com"
SA_KILL="masastore-killswitch@${PROJECT_ID}.iam.gserviceaccount.com"
KILL_TOPIC=masastore-budget-alerts
KILL_FUNCTION=masastore-kill-switch
IMAGE_PREFIX="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}"
STAGING_BUCKET="gs://${PROJECT_ID}-build-staging"
BUDGET_AMOUNT="${BUDGET_AMOUNT:-5ILS}"   # must be in the billing account's currency
CHAT_DAILY_USER_LIMIT="${CHAT_DAILY_USER_LIMIT:-20}"
CHAT_DAILY_GLOBAL_LIMIT="${CHAT_DAILY_GLOBAL_LIMIT:-400}"

[[ -n "$PROJECT_ID" ]] || { echo "No project: run 'gcloud config set project <id>'" >&2; exit 1; }
# Billing/budget APIs otherwise bill quota to gcloud's own client project.
export CLOUDSDK_BILLING_QUOTA_PROJECT="$PROJECT_ID"
log() { printf '\n==> %s\n' "$*"; }
exists() { "$@" >/dev/null 2>&1; }

cmd_apis() {
  log "Enabling APIs"
  gcloud services enable \
    run.googleapis.com compute.googleapis.com artifactregistry.googleapis.com \
    cloudbuild.googleapis.com secretmanager.googleapis.com iap.googleapis.com \
    billingbudgets.googleapis.com cloudbilling.googleapis.com \
    pubsub.googleapis.com eventarc.googleapis.com cloudfunctions.googleapis.com
}

cmd_network() {
  log "VPC + subnet (Private Google Access: lets the IP-less VM reach Artifact Registry / Secret Manager)"
  exists gcloud compute networks describe "$NETWORK" ||
    gcloud compute networks create "$NETWORK" --subnet-mode=custom
  exists gcloud compute networks subnets describe "$SUBNET" --region "$REGION" ||
    gcloud compute networks subnets create "$SUBNET" --network "$NETWORK" --region "$REGION" \
      --range "$SUBNET_RANGE" --enable-private-ip-google-access

  log "Firewall: MySQL/Redis only from the subnet (Cloud Run Direct VPC egress), SSH only via IAP"
  exists gcloud compute firewall-rules describe masastore-allow-data-from-subnet ||
    gcloud compute firewall-rules create masastore-allow-data-from-subnet --network "$NETWORK" \
      --direction INGRESS --allow tcp:3306,tcp:6379 --source-ranges "$SUBNET_RANGE" \
      --target-tags "$DATA_TAG"
  exists gcloud compute firewall-rules describe masastore-allow-iap-ssh ||
    gcloud compute firewall-rules create masastore-allow-iap-ssh --network "$NETWORK" \
      --direction INGRESS --allow tcp:22 --source-ranges "$IAP_RANGE" --target-tags "$DATA_TAG"

  log "Reserving the VM's internal IP (internal addresses are free)"
  exists gcloud compute addresses describe masastore-data-ip --region "$REGION" ||
    gcloud compute addresses create masastore-data-ip --region "$REGION" \
      --subnet "$SUBNET" --addresses "$DATA_VM_IP"
}

cmd_iam() {
  log "Service accounts (one per component, least privilege)"
  for sa in masastore-api masastore-ui masastore-vm; do
    exists gcloud iam service-accounts describe "${sa}@${PROJECT_ID}.iam.gserviceaccount.com" ||
      gcloud iam service-accounts create "$sa" --display-name "MasaStore ${sa#masastore-}"
  done
  for role in roles/logging.logWriter roles/monitoring.metricWriter; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:${SA_VM}" \
      --role "$role" --condition=None >/dev/null
  done
  echo "ok (secret and registry access is granted per resource in 'secrets' / 'registry')"
}

# Creates the secret if missing and adds a first version from stdin.
# An existing secret is never overwritten: MySQL was initialised with it.
create_secret() {
  local name=$1
  if exists gcloud secrets describe "$name"; then
    echo "secret $name exists — keeping current value"
    cat >/dev/null
    return
  fi
  gcloud secrets create "$name" --replication-policy=user-managed --locations="$REGION" --data-file=- >/dev/null
  echo "secret $name created"
}

grant_secret() {
  gcloud secrets add-iam-policy-binding "$1" --member "serviceAccount:$2" \
    --role roles/secretmanager.secretAccessor >/dev/null
}

cmd_secrets() {
  log "Secrets (generated locally, piped to Secret Manager, never printed)"
  local gemini_key
  gemini_key=$(sed -n 's/^GEMINI_API_KEY=//p' .env 2>/dev/null | tr -d '\r"' | head -n1)
  [[ -n "$gemini_key" ]] || { echo "GEMINI_API_KEY not found in .env" >&2; exit 1; }
  printf '%s' "$gemini_key" | create_secret gemini-api-key
  unset gemini_key

  # \r too: Git Bash's openssl on Windows emits CRLF.
  openssl rand -hex 32 | tr -d '\r\n' | create_secret jwt-secret-key
  openssl rand -hex 24 | tr -d '\r\n' | create_secret mysql-app-password
  openssl rand -hex 24 | tr -d '\r\n' | create_secret redis-password

  if ! exists gcloud secrets describe database-url; then
    local db_pw
    db_pw=$(gcloud secrets versions access latest --secret mysql-app-password | tr -d '\r\n')
    printf 'mysql+pymysql://masastore:%s@%s:3306/main' "$db_pw" "$DATA_VM_IP" | create_secret database-url
    unset db_pw
  else
    echo "secret database-url exists — keeping current value"
  fi

  log "Per-secret access"
  for s in gemini-api-key jwt-secret-key database-url redis-password; do grant_secret "$s" "$SA_API"; done
  for s in mysql-app-password redis-password; do grant_secret "$s" "$SA_VM"; done
  echo "ok"
}

cmd_registry() {
  log "Artifact Registry repo (keep only the 2 newest versions of each image)"
  exists gcloud artifacts repositories describe "$REPO" --location "$REGION" ||
    gcloud artifacts repositories create "$REPO" --repository-format=docker --location "$REGION"
  local policy
  policy=$(mktemp)
  cat > "$policy" <<'JSON'
[
  {"name": "keep-2-newest", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 2}},
  {"name": "delete-rest", "action": {"type": "Delete"}, "condition": {"tagState": "any"}}
]
JSON
  gcloud artifacts repositories set-cleanup-policies "$REPO" --location "$REGION" \
    --policy "$policy" --no-dry-run >/dev/null
  rm -f "$policy"
  gcloud artifacts repositories add-iam-policy-binding "$REPO" --location "$REGION" \
    --member "serviceAccount:${SA_VM}" --role roles/artifactregistry.reader >/dev/null

  log "Build-source staging bucket in ${REGION} (free-tier region), auto-delete after 7 days"
  if ! exists gcloud storage buckets describe "$STAGING_BUCKET"; then
    gcloud storage buckets create "$STAGING_BUCKET" --location "$REGION" --uniform-bucket-level-access
    local lifecycle
    lifecycle=$(mktemp)
    echo '{"rule":[{"action":{"type":"Delete"},"condition":{"age":7}}]}' > "$lifecycle"
    gcloud storage buckets update "$STAGING_BUCKET" --lifecycle-file "$lifecycle"
    rm -f "$lifecycle"
  fi
}

cmd_build() {
  log "Cloud Build: app, db, redis images → Artifact Registry"
  gcloud builds submit --config cloudbuild.yaml --region "$REGION" \
    --gcs-source-staging-dir "${STAGING_BUCKET}/source" \
    --substitutions "_REGION=${REGION},_REPO=${REPO}"
}

cmd_vm() {
  log "Data VM: e2-micro (Always Free), COS, pd-standard boot disk (pd-balanced is NOT free), no external IP"
  if exists gcloud compute instances describe "$DATA_VM" --zone "$ZONE"; then
    echo "VM exists — re-running its startup script (pulls latest images, restarts containers)"
    gcloud compute ssh "$DATA_VM" --zone "$ZONE" --tunnel-through-iap \
      --command "sudo google_metadata_script_runner startup"
    return
  fi
  gcloud compute instances create "$DATA_VM" --zone "$ZONE" \
    --machine-type e2-micro \
    --image-family cos-stable --image-project cos-cloud \
    --boot-disk-type pd-standard --boot-disk-size 10GB \
    --subnet "$SUBNET" --private-network-ip "$DATA_VM_IP" --no-address \
    --tags "$DATA_TAG" \
    --service-account "$SA_VM" --scopes cloud-platform \
    --shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring \
    --metadata "region=${REGION},repo=${REPO},google-logging-enabled=true,enable-oslogin=TRUE" \
    --metadata-from-file startup-script=deploy/vm-startup.sh
}

cmd_api() {
  log "Cloud Run: ${API_SERVICE} (Direct VPC egress to the data VM, private ranges only)"
  gcloud run deploy "$API_SERVICE" --region "$REGION" \
    --image "${IMAGE_PREFIX}/app:latest" \
    --service-account "$SA_API" \
    --execution-environment gen2 \
    --network "$NETWORK" --subnet "$SUBNET" --vpc-egress private-ranges-only \
    --cpu 1 --memory 1Gi --concurrency 40 --timeout 60 \
    --min-instances 0 --max-instances 2 \
    --set-env-vars "REDIS_HOST=${DATA_VM_IP},CHAT_DAILY_USER_LIMIT=${CHAT_DAILY_USER_LIMIT},CHAT_DAILY_GLOBAL_LIMIT=${CHAT_DAILY_GLOBAL_LIMIT}" \
    --set-secrets "DATABASE_URL=database-url:latest,SECRET_KEY=jwt-secret-key:latest,GEMINI_API_KEY=gemini-api-key:latest,REDIS_PASSWORD=redis-password:latest" \
    --allow-unauthenticated
}

cmd_ui() {
  local api_url
  api_url=$(gcloud run services describe "$API_SERVICE" --region "$REGION" --format 'value(status.url)')
  [[ -n "$api_url" ]] || { echo "Deploy the API first" >&2; exit 1; }
  log "Cloud Run: ${UI_SERVICE} → ${api_url}"
  # Streamlit keeps session state in-process, hence one instance + affinity.
  # An open tab holds a WebSocket and keeps the instance billed; the budget
  # kill switch is the safety net for that.
  gcloud run deploy "$UI_SERVICE" --region "$REGION" \
    --image "${IMAGE_PREFIX}/app:latest" \
    --service-account "$SA_UI" \
    --command streamlit \
    --args "run,ui/Main.py,--server.port=8080,--server.address=0.0.0.0,--server.headless=true,--browser.gatherUsageStats=false" \
    --cpu 1 --memory 512Mi --concurrency 50 --timeout 3600 \
    --min-instances 0 --max-instances 1 --session-affinity \
    --set-env-vars "API_BASE_URL=${api_url}" \
    --allow-unauthenticated
}

cmd_budget() {
  local billing_account
  billing_account=$(gcloud billing projects describe "$PROJECT_ID" --format 'value(billingAccountName)' | sed 's|billingAccounts/||')
  log "Budget ${BUDGET_AMOUNT} on project ${PROJECT_ID}, alerts at 50/90/100% (alerts only — they do not stop billing)"
  gcloud billing budgets create --billing-account "$billing_account" \
    --display-name "MasaStore_web" \
    --budget-amount "${BUDGET_AMOUNT}" \
    --filter-projects "projects/${PROJECT_ID}" \
    --threshold-rule percent=0.5 --threshold-rule percent=0.9 --threshold-rule percent=1.0
}

cmd_killswitch() {
  log "Kill switch: budget → Pub/Sub → function that makes both services internal-only"
  exists gcloud pubsub topics describe "$KILL_TOPIC" || gcloud pubsub topics create "$KILL_TOPIC"

  exists gcloud iam service-accounts describe "$SA_KILL" ||
    gcloud iam service-accounts create masastore-killswitch --display-name "MasaStore kill switch"
  # Scoped to the two services only, not the whole project.
  for svc in "$API_SERVICE" "$UI_SERVICE"; do
    gcloud run services add-iam-policy-binding "$svc" --region "$REGION" \
      --member "serviceAccount:${SA_KILL}" --role roles/run.developer >/dev/null
  done
  for sa in "$SA_API" "$SA_UI"; do
    gcloud iam service-accounts add-iam-policy-binding "$sa" \
      --member "serviceAccount:${SA_KILL}" --role roles/iam.serviceAccountUser >/dev/null
  done
  # Waiting on the update's operation needs run.operations.get, which is only
  # grantable project-wide; run.viewer is read-only.
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:${SA_KILL}" \
    --role roles/run.viewer --condition=None >/dev/null
  # Cloud Run re-validates the image on any service update, ingress included.
  gcloud artifacts repositories add-iam-policy-binding "$REPO" --location "$REGION" \
    --member "serviceAccount:${SA_KILL}" --role roles/artifactregistry.reader >/dev/null

  gcloud functions deploy "$KILL_FUNCTION" --gen2 --region "$REGION" \
    --runtime python311 --source deploy/kill_switch --entry-point stop_billing \
    --trigger-topic "$KILL_TOPIC" --service-account "$SA_KILL" \
    --memory 256Mi --max-instances 1 --no-allow-unauthenticated \
    --set-env-vars "^;^PROJECT_ID=${PROJECT_ID};REGION=${REGION};SERVICES=${API_SERVICE},${UI_SERVICE};KILL_AT=1.0"
  # The Pub/Sub trigger invokes the function as its own service account.
  gcloud functions add-invoker-policy-binding "$KILL_FUNCTION" --region "$REGION" \
    --member "serviceAccount:${SA_KILL}" >/dev/null

  log "Connecting the budget to the topic"
  local billing_account budget_id
  billing_account=$(gcloud billing projects describe "$PROJECT_ID" --format 'value(billingAccountName)' | sed 's|billingAccounts/||')
  budget_id=$(gcloud billing budgets list --billing-account "$billing_account" \
    --filter "displayName=MasaStore_web" --format 'value(name)' | head -n1)
  [[ -n "$budget_id" ]] || { echo "Budget 'MasaStore_web' not found — run 'budget' first" >&2; exit 1; }
  gcloud billing budgets update "$budget_id" --billing-account "$billing_account" \
    --notifications-rule-pubsub-topic "projects/${PROJECT_ID}/topics/${KILL_TOPIC}"
}

cmd_reopen() {
  log "Reopening public access to both services"
  for svc in "$API_SERVICE" "$UI_SERVICE"; do
    gcloud run services update "$svc" --region "$REGION" --ingress all
  done
}

cmd_status() {
  gcloud run services list --region "$REGION" --format 'table(metadata.name,status.url)'
  gcloud compute instances list --format 'table(name,zone,machineType.basename(),networkInterfaces[0].networkIP,status)'
}

cmd_destroy() {
  read -r -p "Delete ALL MasaStore resources in ${PROJECT_ID} (including DB data)? type 'yes': " ok
  [[ "$ok" == yes ]] || exit 1
  gcloud functions delete "$KILL_FUNCTION" --region "$REGION" --quiet || true
  gcloud pubsub topics delete "$KILL_TOPIC" --quiet || true
  gcloud iam service-accounts delete "$SA_KILL" --quiet || true
  gcloud run services delete "$UI_SERVICE" --region "$REGION" --quiet || true
  gcloud run services delete "$API_SERVICE" --region "$REGION" --quiet || true
  gcloud compute instances delete "$DATA_VM" --zone "$ZONE" --quiet || true
  gcloud compute addresses delete masastore-data-ip --region "$REGION" --quiet || true
  gcloud compute firewall-rules delete masastore-allow-data-from-subnet masastore-allow-iap-ssh --quiet || true
  gcloud compute networks subnets delete "$SUBNET" --region "$REGION" --quiet || true
  gcloud compute networks delete "$NETWORK" --quiet || true
  gcloud artifacts repositories delete "$REPO" --location "$REGION" --quiet || true
  gcloud storage rm -r "$STAGING_BUCKET" || true
  for s in gemini-api-key jwt-secret-key mysql-app-password redis-password database-url; do
    gcloud secrets delete "$s" --quiet || true
  done
}

case "${1:-}" in
  apis|network|iam|secrets|registry|build|vm|api|ui|budget|killswitch|reopen|status|destroy) "cmd_$1" ;;
  *) sed -n '2,9p' "$0"; exit 1 ;;
esac
