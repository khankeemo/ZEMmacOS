"""Universal conversation engine — thin wrapper; ALL logic lives in LicenseEngine"""
from .license_engine import LicenseEngine

__all__ = ["create_communication", "get_conversation", "reply_to_conversation",
           "list_conversations", "get_request_history"]


def create_communication(engine: LicenseEngine, **kwargs) -> dict:
    return engine.create_communication(**kwargs)


def get_conversation(engine: LicenseEngine, conversation_id: str) -> dict:
    return engine.get_conversation(conversation_id)


def reply_to_conversation(engine: LicenseEngine, conversation_id: str, message: str,
                          customer_name: str = "", customer_email: str = "") -> dict:
    return engine.reply_to_conversation(conversation_id, message, customer_name, customer_email)


def list_conversations(engine: LicenseEngine, email: str) -> dict:
    return engine.list_conversations(email)


def get_request_history(engine: LicenseEngine, email: str) -> dict:
    return engine.get_request_history(email)
