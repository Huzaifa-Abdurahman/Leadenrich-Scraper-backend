import time
import json
import re
import os
import requests
from urllib.parse import urlparse
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
try:
    from app.config import settings
except ImportError:
    import sys
    import os
    sys.path.append(os.getcwd())
    from app.config import settings

# Strict configuration from user request
ENABLE_WEB_SEARCH      = True
INCLUDE_SUBDOMAINS     = True
MAP_CONTACT_PAGES      = True
MAX_MAP_URLS_PER_SITE  = 8
POLL_INTERVAL_SEC      = 4
MAX_POLL_ATTEMPTS      = 45
BASE = "https://api.firecrawl.dev/v2"

console = Console()

CONTACT_SCHEMA = {
    "type": "object",
    "properties": {
        "company_name": {"type": ["string", "null"], "description": "Official name"},
        "emails": {"type": "array", "items": {"type": "string"}},
        "phone_numbers": {"type": "array", "items": {"type": "string"}},
        "addresses": {"type": "array", "items": {"type": "string"}},
        "hr_or_representatives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name":  {"type": "string"},
                    "title": {"type": "string"},
                    "email": {"type": ["string", "null"]}
                }
            }
        },
        "social_profiles": {"type": "array", "items": {"type": "string"}},
        "website": {"type": ["string", "null"]},
        "data_confidence": {"type": "string", "enum": ["high", "medium", "low"]}
    },
    "required": ["emails", "phone_numbers", "addresses", "data_confidence"]
}

EXTRACTION_PROMPT = "Extract ALL available contact information. Include emails, phones, and addresses. Deduplicate."

def get_headers():
    key = settings.firecrawl_api_key
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }

def safe_post(endpoint, payload, retries=3):
    url = f"{BASE}{endpoint}"
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, headers=get_headers(), json=payload, timeout=60)
            if resp.status_code == 429: 
                time.sleep(int(resp.headers.get("Retry-After", 10)))
                continue
            if resp.status_code >= 400:
                print(f"DEBUG: Firecrawl Error {resp.status_code} - {resp.text}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == retries: raise
            time.sleep(5 * attempt)

def safe_get(endpoint, retries=3):
    url = f"{BASE}{endpoint}"
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=get_headers(), timeout=60)
            if resp.status_code == 429: 
                time.sleep(10)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt == retries: raise
            time.sleep(5 * attempt)

def poll_job(job_id, label, update_cb=None):
    endpoint = f"/extract/{job_id}"
    # Rich progress is for logs/terminal, but we support update_cb for backend job management
    # We'll use a silent version if no console is needed, but we'll keep it for debugging
    for i in range(MAX_POLL_ATTEMPTS):
        time.sleep(POLL_INTERVAL_SEC)
        try:
            data = safe_get(endpoint)
            status = data.get("status", "")
            
            if update_cb:
                update_cb(status, i+1)
            else:
                print(f"[{label}] Status: {status} (poll {i+1})")
                
            if status == "completed": 
                return data.get("data")
            elif status in ("failed", "cancelled"): 
                return None
        except Exception as e:
            print(f"DEBUG: Polling error for {job_id}: {str(e)}")
            continue
    return None

def discover_contact_pages(base_url):
    try:
        payload = {"url": base_url, "includeSubdomains": INCLUDE_SUBDOMAINS}
        resp = safe_post("/map", payload)
        all_urls = resp.get("links", [base_url])
        pats = re.compile(r"/(contact|about|team|hr|careers)", re.I)
        priority = [u for u in all_urls if pats.search(u)]
        return list(dict.fromkeys([base_url] + priority))[:MAX_MAP_URLS_PER_SITE]
    except Exception: 
        return [base_url]

def extract_contact_info(target_url, update_cb=None):
    domain = urlparse(target_url).netloc or target_url
    urls = discover_contact_pages(target_url)
    try:
        job = safe_post("/extract", {
            "urls": urls, 
            "prompt": EXTRACTION_PROMPT, 
            "schema": CONTACT_SCHEMA, 
            "enableWebSearch": ENABLE_WEB_SEARCH, 
            "scrapeOptions": {"formats": ["markdown"]}
        })
        if not job or "id" not in job:
            return {"source_url": target_url, "data": {}, "pages_scanned": urls}
            
        data = poll_job(job.get("id"), domain, update_cb)
    except Exception as e: 
        print(f"DEBUG: Extraction failed for {target_url}: {str(e)}")
        data = None
    return {"source_url": target_url, "data": data or {}, "pages_scanned": urls}
