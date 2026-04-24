import re
from urllib.parse import urlparse

def normalize_url(input_str: str) -> str:
    """
    Normalizes a domain or URL string into a clean https:// URL.
    - Adds https:// if missing
    - Removes www.
    - Strips trailing slashes
    """
    if not input_str:
        return ""
        
    url = input_str.strip().lower()
    
    # Remove protocol if existing to start from a clean slate
    url = re.sub(r'^https?://', '', url)
    
    # Remove www.
    url = re.sub(r'^www\.', '', url)
    
    # Strip trailing slashes and paths (since we want homepage)
    url = url.split('/')[0]
    
    if not url:
        return ""
        
    return f"https://{url}"
