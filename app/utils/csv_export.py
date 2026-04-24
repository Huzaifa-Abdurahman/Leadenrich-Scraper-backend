import io
import pandas as pd
from typing import List, Dict, Any

def generate_csv_buffer(results: List[Dict[str, Any]]) -> io.BytesIO:
    """Strictly matching the user's save_data logic for CSV."""
    rows = []
    for r in results:
        rows.append({
            "url": r.get('website', ''),
            "emails": ", ".join(r.get("emails", [])),
            "phones": ", ".join(r.get("phones", [])),
            "addresses": "; ".join(r.get("addresses", []))
        })
    df = pd.DataFrame(rows)
    stream = io.BytesIO()
    df.to_csv(stream, index=False)
    stream.seek(0)
    return stream

def generate_markdown_buffer(results: List[Dict[str, Any]]) -> io.BytesIO:
    """Strictly matching the user's save_data logic for Markdown."""
    md_content = "# Contact Extraction Results\n\n"
    for r in results:
        md_content += f"## {r.get('website', 'Unknown Source')}\n"
        md_content += f"- **Emails**: {', '.join(r.get('emails', [])) or 'None'}\n"
        md_content += f"- **Phones**: {', '.join(r.get('phones', [])) or 'None'}\n"
        md_content += f"- **Addresses**: {'; '.join(r.get('addresses', [])) or 'None'}\n\n"
        
        # Adding HR representatives if available (extending their logic slightly for completeness)
        reps = r.get("representatives", [])
        if reps:
            md_content += "### Key Representatives\n"
            for rep in reps:
                md_content += f"- {rep.get('name')} ({rep.get('title')}) - {rep.get('email') or 'No Email'}\n"
            md_content += "\n"

    stream = io.BytesIO(md_content.encode('utf-8'))
    stream.seek(0)
    return stream
