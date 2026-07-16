import pandas as pd
import io
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Header
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional

try:
    from app.services.job_manager import (
        create_job,
        get_job_status,
        run_job_background,
        verify_session,
        consume_session,
    )
    from app.utils.url_normalizer import normalize_url
except ImportError:
    from services.job_manager import (
        create_job,
        get_job_status,
        run_job_background,
        verify_session,
        consume_session,
    )
    from utils.url_normalizer import normalize_url


router = APIRouter(tags=["lead-gen"])
logger = logging.getLogger(__name__)


class ManualCrawlRequest(BaseModel):
    domains: List[str]


def _require_session(session_id: Optional[str]) -> str:
    if not session_id:
        raise HTTPException(
            401,
            "Missing session. Call /api/session first and send X-Session-Id header.",
        )
    if not verify_session(session_id):
        raise HTTPException(
            401,
            "Scraping limit reached for this browser (3 free scrapes). Clear site data only resets if the session is new — limit is per browser session.",
        )
    return session_id


@router.post("/manual")
async def manual_crawl(
    request: ManualCrawlRequest,
    background_tasks: BackgroundTasks,
    x_session_id: Optional[str] = Header(default=None),
):
    session_id = _require_session(x_session_id)

    urls = [normalize_url(d) for d in request.domains if d.strip()]
    if not urls:
        raise HTTPException(400, "No valid domains")

    if len(urls) > 10:
        urls = urls[:10]
        logger.warning("Limit exceeded: truncating to 10 domains")

    uses_left = consume_session(session_id)
    job_id = create_job(len(urls))
    background_tasks.add_task(run_job_background, job_id, urls)
    return {"success": True, "job_id": job_id, "uses_left": uses_left}


@router.post("/upload")
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    x_session_id: Optional[str] = Header(default=None),
):
    session_id = _require_session(x_session_id)

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "Must be CSV")

    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        col = next(
            (
                c
                for c in df.columns
                if any(k in c.lower() for k in ["domain", "website", "url"])
            ),
            df.columns[0],
        )
        urls = [normalize_url(str(d)) for d in df[col].dropna().tolist() if d]

        if not urls:
            raise HTTPException(400, "No URLs found in CSV")

        if len(urls) > 10:
            urls = urls[:10]
            logger.warning("Limit exceeded: truncating to 10 domains")

        uses_left = consume_session(session_id)
        job_id = create_job(len(urls))
        background_tasks.add_task(run_job_background, job_id, urls)
        return {"success": True, "job_id": job_id, "uses_left": uses_left}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV upload error: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/{job_id}")
async def status(job_id: str):
    job = get_job_status(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/download/csv/{job_id}")
async def download_csv(job_id: str):
    job = get_job_status(job_id)
    if not job or not job.get("results"):
        raise HTTPException(404, "No results found for this job")

    rows = []
    for r in job["results"]:
        rows.append(
            {
                "url": r.get("website", ""),
                "company": r.get("company_name", ""),
                "emails": ", ".join(r.get("emails", [])),
                "phones": ", ".join(r.get("phones", [])),
                "addresses": "; ".join(r.get("addresses", [])),
                "confidence": r.get("confidence", "low"),
            }
        )

    df = pd.DataFrame(rows)
    stream = io.StringIO()
    df.to_csv(stream, index=False)

    return Response(
        content=stream.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=contact_results_{job_id[:8]}.csv"
        },
    )


@router.get("/download/md/{job_id}")
async def download_md(job_id: str):
    job = get_job_status(job_id)
    if not job or not job.get("results"):
        raise HTTPException(404, "No results found for this job")

    output = f"# Contact Extraction Results - Job {job_id[:8]}\n\n"
    for r in job["results"]:
        output += f"## {r.get('company_name', r.get('website'))}\n"
        output += f"- **Website**: {r.get('website')}\n"
        output += f"- **Emails**: {', '.join(r.get('emails', [])) or 'None'}\n"
        output += f"- **Phones**: {', '.join(r.get('phones', [])) or 'None'}\n"
        output += f"- **Addresses**: {'; '.join(r.get('addresses', [])) or 'None'}\n"
        output += f"- **Confidence**: {r.get('confidence', 'low')}\n\n"

    return Response(
        content=output,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename=contact_results_{job_id[:8]}.md"
        },
    )
