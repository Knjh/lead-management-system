# models/lead_models.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class CallStatus(str, Enum):
    NEW = "new"
    CALLING = "calling"
    COMPLETED = "completed"
    RETRY = "retry"
    CALLBACK = "callback"
    FAILED = "failed"

class DisconnectionReason(str, Enum):
    USER_HANGUP = "user_hangup"
    AGENT_HANGUP = "agent_hangup"
    CALL_TRANSFER = "call_transfer"
    VOICEMAIL = "voicemail"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    FAILED = "failed"

class Lead(BaseModel):
    id: Optional[str] = None
    phone_number: str = Field(..., description="Lead's phone number")
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    custom_data: Optional[Dict[str, Any]] = {}
    priority: int = 0
    priority_reason: Optional[str] = None

    # Call management fields
    call_status: CallStatus = CallStatus.NEW
    number_of_retries: int = 0
    last_call_time: Optional[datetime] = None
    callback_time: Optional[datetime] = None
    
    # Call result data
    post_call_data: Optional[Dict[str, Any]] = {}
    call_recordings: Optional[list] = []
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class CallWebhookEvent(BaseModel):
    event_type: str
    call_id: str
    agent_id: str
    call_type: str
    phone_number: str
    from_number: str
    to_number: str
    direction: str
    call_status: str
    start_timestamp: Optional[int] = None
    end_timestamp: Optional[int] = None
    disconnection_reason: Optional[str] = None
    recording_url: Optional[str] = None
    public_log_url: Optional[str] = None
    llm_dynamic_variables: Optional[Dict[str, Any]] = {}
    opt_out_sensitive_data_storage: Optional[bool] = False

class RetellCreateCallRequest(BaseModel):
    from_number: str
    to_number: str
    override_agent_id: Optional[str] = None
    retell_llm_dynamic_variables: Optional[Dict[str, Any]] = {}
    drop_call_if_machine_detected: bool = True
