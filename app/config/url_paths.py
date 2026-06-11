def normalize_route_prefix(raw_path):
    """Convert an env-style URL path into a Django route prefix."""
    path = (raw_path or "").strip().strip("/")
    return f"{path}/" if path else ""
