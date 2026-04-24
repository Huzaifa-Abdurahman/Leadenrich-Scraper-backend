import re
from typing import List

def extract_emails(text: str) -> List[str]:
    """Standard email regex."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(pattern, text)))

def extract_phones(text: str) -> List[str]:
    """Detects international and local formats (+, (), -, digits)."""
    # Matches various formats: +1-234-567-8901, (123) 456-7890, 123.456.7890, etc.
    pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}?\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}'
    matches = re.findall(pattern, text)
    # Filter out short sequences that aren't phones
    return list(set([m.strip() for m in matches if len(re.sub(r'\D', '', m)) >= 9]))

def extract_company_name(text: str, domain: str) -> str:
    """Heuristic: Look for Title in markdown or fallback to domain."""
    # Find Title: # Title or [Title] or Title\n=====
    title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()
    
    # Fallback to domain name
    name = domain.split('.')[0].capitalize()
    return name
