# Utility functions (placeholder for future use)
# This file is kept as a placeholder for future utility functions
# when you expand your CI/CD learning project

def get_timestamp():
    """Get current timestamp in ISO format"""
    from datetime import datetime
    return datetime.utcnow().isoformat()

def format_version(version: str):
    """Format version string"""
    return f"v{version}"
