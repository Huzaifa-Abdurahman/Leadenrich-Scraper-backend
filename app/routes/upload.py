import asyncio
import pandas as pd
import io
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from typing import List

# Use actual internal imports, removing normalize_url if redundant or fixing its import
try:
    from app.services.job_manager import create_job, get_job_status, run_job_background, verify_key, consume_key
    from app.utils.url_normalizer import normalize_url
except ImportError:
    from services.job_manager import create_job, get_job_status, run_job_background, verify_key, consume_key
    from utils.url_normalizer import normalize_url


router = APIRouter(tags=["lead-gen"])
logger = logging.getLogger(__name__)

class ManualCrawlRequest(BaseModel):
    domains: List[str]
    access_key: str

@router.post("/manual")
async def manual_crawl(request: ManualCrawlRequest, background_tasks: BackgroundTasks):
    if not verify_key(request.access_key):
        raise HTTPException(401, "Invalid or expired access key")
        
    urls = [normalize_url(d) for d in request.domains if d.strip()]
    if not urls: 
        raise HTTPException(400, "No valid domains")
    
    # Enforce 10 website limit
    if len(urls) > 10:
        urls = urls[:10]
        logger.warning(f"Limit exceeded: truncating to 10 domains")

    consume_key(request.access_key)
    job_id = create_job(len(urls))
    background_tasks.add_task(run_job_background, job_id, urls)
    return {"success": True, "job_id": job_id}

@router.post("/upload")
async def upload_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...), access_key: str = ""):
    if not verify_key(access_key):
        raise HTTPException(401, "Invalid or expired access key")

    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "Must be CSV")

    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        col = next((c for c in df.columns if any(k in c.lower() for k in ['domain', 'website', 'url'])), df.columns[0])
        urls = [normalize_url(str(d)) for d in df[col].dropna().tolist() if d]
        
        if not urls:
            raise HTTPException(400, "No URLs found in CSV")

        # Enforce 10 website limit
        if len(urls) > 10:
            urls = urls[:10]
            logger.warning(f"Limit exceeded: truncating to 10 domains")

        consume_key(access_key)
        job_id = create_job(len(urls))
        background_tasks.add_task(run_job_background, job_id, urls)
        return {"success": True, "job_id": job_id}

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
        rows.append({
            "url": r.get("website", ""),
            "company": r.get("company_name", ""),
            "emails": ", ".join(r.get("emails", [])),
            "phones": ", ".join(r.get("phones", [])),
            "addresses": "; ".join(r.get("addresses", [])),
            "confidence": r.get("confidence", "low")
        })
    
    df = pd.DataFrame(rows)
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    return Response(
        content=stream.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=contact_results_{job_id[:8]}.csv"}
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
        headers={"Content-Disposition": f"attachment; filename=contact_results_{job_id[:8]}.md"}
    )
