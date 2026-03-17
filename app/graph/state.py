# app/graph/state.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class RequisitionStatus(str, Enum):
    DRAFT            = 'DRAFT'
    APPROVAL_PENDING = 'APPROVAL_PENDING'
    APPROVED         = 'APPROVED'
    ACTIVE           = 'ACTIVE'
    CLOSED           = 'CLOSED'

class ApprovalDecision(str, Enum):
    APPROVE = 'approve'
    REJECT  = 'reject'
    EDIT    = 'edit'   # approve with requested changes

class JobRequisition(BaseModel):
    requisition_id:  str
    role_title:      str
    level:           str              # e.g. 'L5'
    region:          str              # e.g. 'EU-IE'
    department:      str
    budget_band:     Optional[str] = None
    remote_policy:   Optional[str] = None
    headcount:       int = 1
    status:          RequisitionStatus = RequisitionStatus.DRAFT
    created_by:      Optional[str] = None
    created_at:      datetime = Field(default_factory=datetime.utcnow)

class ApprovalToken(BaseModel):
    stage:         str
    approved_by:   str
    approved_at:   datetime = Field(default_factory=datetime.utcnow)
    decision:      ApprovalDecision
    comments:      Optional[str] = None
    edited_fields: Optional[Dict] = None

class EvidenceRef(BaseModel):
    candidate_id: str
    criterion:    str    # rubric criterion name
    quote:        str    # exact text from resume
    score:        float

class CandidateProfile(BaseModel):
    candidate_id:             str
    requisition_id:           str
    years_experience:         Optional[int]  = None
    skills:                   List[str]      = Field(default_factory=list)
    raw_resume_ref:           str            # Azure Blob: restricted-resumes
    redacted_text_ref:        Optional[str]  = None  # Azure Blob: redacted-resumes
    pii_redacted:             bool           = False
    injection_flagged:        bool           = False
    score:                    Optional[float]= None
    evidence_refs:            List[EvidenceRef] = Field(default_factory=list)
    uncertainty:              Optional[str]  = None   # low|medium|high
    screening_recommendation: Optional[str]  = None   # shortlist|needs_review|reject
    shortlisted:              Optional[bool] = None
    needs_review:             Optional[bool] = None
    proposed_reject:          Optional[bool] = None
    reject_reason:            Optional[str]  = None

class OfferPackage(BaseModel):
    candidate_id:                 str
    requisition_id:               str
    base_salary:                  float
    currency:                     str  = 'EUR'
    in_band:                      bool
    requires_finance_escalation:  bool = False
    legal_template_used:          str
    clauses:                      List[str] = Field(default_factory=list)
    citations:                    List[Dict] = Field(default_factory=list)
    status:                       str = 'DRAFT'

class OnboardingTask(BaseModel):
    task:       str
    owner:      str
    system:     str   # HRIS | ITSM | IAM | Calendar | Email | Payroll
    sla_days:   int
    blocked_by: Optional[str] = None
    ticket_id:  Optional[str] = None
    status:     str = 'PENDING'

class AuditEvent(BaseModel):
    event_id:   str  = Field(default_factory=lambda: __import__('uuid').uuid4().hex[:8])
    event_type: str  # APPROVAL | TOOL_CALL | PII_REDACTION | INJECTION_FLAG | NODE_ERROR
    stage:      str
    actor_id:   str  # 'system' for automated actions, user_id for human actions
    decision:   Optional[str]       = None
    payload:    Dict[str, Any]      = Field(default_factory=dict)
    ts:         datetime            = Field(default_factory=datetime.utcnow)


# ── THE MAIN STATE OBJECT ───────────────────────────────────────────
class HRCopilotState(BaseModel):
    '''
    The single clipboard that flows through every LangGraph node.
    Persisted to PostgreSQL by the checkpointer between steps.
    '''
    # Core hiring data
    job_req:          Optional[JobRequisition] = None
    jd_version:       Optional[Dict]           = None
    candidates:       List[CandidateProfile]   = Field(default_factory=list)
    shortlist:        List[str]                = Field(default_factory=list)  # candidate_ids
    interview_plan:   Optional[Dict]           = None
    offer:            Optional[OfferPackage]   = None
    onboarding_tasks: List[OnboardingTask]     = Field(default_factory=list)

    # Approvals — key = stage name, value = ApprovalToken
    approvals: Dict[str, ApprovalToken] = Field(default_factory=dict)

    # Versioning — set once at start, never change
    graph_version:         str = 'v0.1.0'
    prompt_bundle_version: str = 'v0.1.0'
    rag_index_version:     str = 'v0.1.0'
    tool_bundle_version:   str = 'v0.1.0'

    # Audit log — APPEND ONLY
    audit_events: List[AuditEvent] = Field(default_factory=list)

    # Routing
    needs_clarification:     bool       = False
    clarification_questions: List[str]  = Field(default_factory=list)
    current_stage:           str        = 'intake'
    error:                   Optional[str] = None