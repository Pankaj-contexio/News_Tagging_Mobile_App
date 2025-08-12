from datetime import datetime
from models import usage_collection
from flask import session


def track_action(action_type, details=None):
    """Track user actions in the system"""
    if not session.get('username'):
        return  # Don't track if user isn't logged in

    record = {
        'username': session.get('username'),
        'company': session.get('company'),
        'action_type': action_type,
        'timestamp': datetime.utcnow(),
        'details': details or {}
    }

    usage_collection.insert_one(record)