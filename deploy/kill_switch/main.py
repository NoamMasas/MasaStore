"""Budget kill switch. Budget alerts only send email; this function turns them
into a hard stop: once spend reaches the budget, both Cloud Run services are
switched to internal-only ingress, so public requests (the only thing that
bills) are refused. Reopen with `deploy/deploy.sh reopen`."""

import base64
import json
import os

import functions_framework
from google.cloud import run_v2

PROJECT_ID = os.environ["PROJECT_ID"]
REGION = os.environ["REGION"]
SERVICES = os.environ["SERVICES"].split(",")
KILL_AT = float(os.environ.get("KILL_AT", "1.0"))  # fraction of the budget

INTERNAL_ONLY = run_v2.IngressTraffic.INGRESS_TRAFFIC_INTERNAL_ONLY


@functions_framework.cloud_event
def stop_billing(cloud_event):
    alert = json.loads(base64.b64decode(cloud_event.data["message"]["data"]))
    cost = float(alert["costAmount"])
    budget = float(alert["budgetAmount"])
    if cost < budget * KILL_AT:
        print(f"cost {cost} < {KILL_AT:.0%} of budget {budget}: no action")
        return

    client = run_v2.ServicesClient()
    for name in SERVICES:
        service = client.get_service(name=client.service_path(PROJECT_ID, REGION, name))
        if service.ingress == INTERNAL_ONLY:
            print(f"{name}: already internal-only")
            continue
        service.ingress = INTERNAL_ONLY
        client.update_service(service=service).result()
        print(f"cost {cost} >= budget {budget}: {name} switched to internal-only")
