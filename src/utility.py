def get_priority_score(urgency: str) -> int:
    """
    Convert urgency to Celery priority (10=highest, 1=lowest)
    
    Priority Queue Logic:
    🔴 HIGH urgency    → Priority 10 (processed first)
    🟡 MEDIUM urgency  → Priority 5
    🟢 LOW urgency     → Priority 1 (processed last)
    """
    priority_map = {
        'high': 10,
        'medium': 5,
        'low': 1
    }
    return priority_map.get(urgency.lower(), 5)