import uuid
import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.services.firecrawl import extract_contact_info

logger = logging.getLogger(__name__)

# In-memory job store
JOBS: Dict[str, Dict[str, Any]] = {}

# Browser-session scrape quota (persisted)
SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSIONS_FILE = "sessions.json"
MAX_SCRAPES_PER_SESSION = 3


def load_sessions():
    global SESSIONS
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r") as f:
                SESSIONS = json.load(f)
        except Exception:
            SESSIONS = {}
    else:
        SESSIONS = {}


def save_sessions():
    with open(SESSIONS_FILE, "w") as f:
        json.dump(SESSIONS, f)


def get_or_create_session(session_id: Optional[str] = None) -> Dict[str, Any]:
    """Return existing session or create a new one with 3 scrapes."""
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]

    new_id = session_id or str(uuid.uuid4())
    SESSIONS[new_id] = {
        "session_id": new_id,
        "uses_left": MAX_SCRAPES_PER_SESSION,
        "created_at": datetime.utcnow().isoformat(),
    }
    save_sessions()
    return SESSIONS[new_id]


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    return SESSIONS.get(session_id)


def verify_session(session_id: str) -> bool:
    session = SESSIONS.get(session_id)
    return bool(session and session.get("uses_left", 0) > 0)


def consume_session(session_id: str) -> int:
    """Decrement scrape quota. Returns remaining uses."""
    session = SESSIONS.get(session_id)
    if not session:
        return 0
    if session["uses_left"] > 0:
        session["uses_left"] -= 1
        save_sessions()
    return session["uses_left"]


def list_sessions() -> List[Dict[str, Any]]:
    return sorted(
        SESSIONS.values(),
        key=lambda s: s.get("created_at", ""),
        reverse=True,
    )


# Initial load
load_sessions()


def create_job(total: int) -> str:
    job_id = str(uuid.uuid4())
    job_data = {
        "id": job_id,
        "status": "processing",
        "total": total,
        "completed": 0,
        "results": [],
        "errors": 0,
        "current_action": "Initializing Pipeline...",
        "created_at": datetime.utcnow().isoformat(),
    }
    JOBS[job_id] = job_data
    logger.info(f"📝 Job created: {job_id} for {total} domains")
    return job_id


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status from in-memory store only"""
    return JOBS.get(job_id)


async def _process_single_url(job_id: str, url: str):
    job = JOBS.get(job_id)
    if not job:
        logger.warning(f"Job {job_id} not found")
        return

    try:
        def update_status(status, poll_count):
            msg = f"Scanning {url}: {status} (Poll #{poll_count})"
            job["current_action"] = msg

        loop = asyncio.get_event_loop()
        result_data = await loop.run_in_executor(
            None, extract_contact_info, url, update_status
        )

        if result_data and result_data.get("data"):
            d = result_data["data"]
            flattened = {
                "website": d.get("website") or url,
                "company_name": d.get("company_name") or url,
                "emails": d.get("emails", []) or [],
                "phones": d.get("phone_numbers", []) or [],
                "addresses": d.get("addresses", []) or [],
                "representatives": d.get("hr_or_representatives", []) or [],
                "socials": d.get("social_profiles", []) or [],
                "confidence": d.get("data_confidence", "low") or "low",
                "score": 100
                if d.get("data_confidence") == "high"
                else 75
                if d.get("data_confidence") == "medium"
                else 40,
                "description": f"Extracted via Agentic Selenium Engine. Confidence: {d.get('data_confidence', 'N/A')}.",
            }

            job["results"].append(flattened)
            job["completed"] += 1
            logger.info(f"✅ Extracted: {flattened['company_name']} ({url})")
        else:
            job["errors"] += 1
            logger.warning(f"⚠️ No data found for {url}")

    except Exception as e:
        logger.error(f"❌ Failed to process {url}: {e}")
        job["errors"] += 1


async def run_job_background(job_id: str, urls: List[str]):
    job = JOBS.get(job_id)
    if not job:
        return

    try:
        semaphore = asyncio.Semaphore(5)

        async def SemaphoredProcess(url):
            async with semaphore:
                await _process_single_url(job_id, url)

        tasks = [SemaphoredProcess(url) for url in urls]
        await asyncio.gather(*tasks)

        job["status"] = "completed"
        job["current_action"] = "All domains processed."
        logger.info(f"✅ Job #{job_id} COMPLETED")

    except Exception as e:
        logger.error(f"❌ Job #{job_id} failed: {str(e)}")
        job["status"] = "failed"
        job["current_action"] = f"CRITICAL FAILURE: {str(e)}"


def list_jobs() -> List[Dict[str, Any]]:
    """Return all jobs from in-memory store"""
    return sorted(JOBS.values(), key=lambda j: j.get("created_at", ""), reverse=True)
