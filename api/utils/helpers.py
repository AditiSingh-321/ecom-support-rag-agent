"""
Helper utilities for API requests, string formatting, and error handling.
"""
from typing import Any, Dict, Optional

def sanitize_id(identifier: Optional[str]) -> str:
    """Normalize order or product ID by stripping spaces and prefixes."""
    if not identifier:
        return ""
    return identifier.strip().lstrip("#").upper()

def format_error_response(message: str, code: int = 400) -> Dict[str, Any]:
    """Standardized error dictionary."""
    return {"error": message, "status_code": code}
