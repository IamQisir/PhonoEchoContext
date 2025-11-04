import streamlit as st

def delete_none_ai_history(session_state, property_name: str):
    """Delete AI messages with None content from session state."""
    if property_name in session_state:
        session_state[property_name] = [
            msg for msg in session_state[property_name] if msg.get("content") is not None
        ]

def has_pronunciation_errors(error_data: dict) -> bool:
    """Return True when the error dictionary contains any non-zero entry."""
    if not error_data:
        return False

    for value in error_data.values():
        if isinstance(value, list) and value:
            return True
        if isinstance(value, (int, float)) and value > 0:
            return True
    return False
