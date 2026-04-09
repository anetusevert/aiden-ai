"""Helpers for loading and wiping the Riyadh demo dataset."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.auth import RequestContext
from src.models.case import Case, CaseDocument, CaseEvent, CaseNote
from src.models.client import Client
from src.models.office import OfficeDocument
from src.services.document_generator import create_document as generate_document
from src.services.office_service import OFFICE_CONTENT_TYPES, OfficeService
from src.storage.s3 import S3StorageError

logger = logging.getLogger(__name__)

MOCK_REF_PREFIX = "MOCK-"
RIYADH_DEMO_VERSION = "riyadh-practice-v1"
DEMO_METADATA_KEY = "demo_seed"
DEMO_STORAGE_PREFIX = "office-demo"


@dataclass
class DemoSeedSummary:
    clients_count: int = 0
    cases_count: int = 0
    documents_count: int = 0
    notes_count: int = 0
    events_count: int = 0
    warnings: list[str] = field(default_factory=list)


def _doc(
    title: str,
    doc_type: str,
    template: str,
    role: str,
    day_offset: int,
) -> dict[str, Any]:
    return {
        "title": title,
        "doc_type": doc_type,
        "template": template,
        "role": role,
        "day_offset": day_offset,
    }


def _note(content: str, day_offset: int, *, amin: bool = False) -> dict[str, Any]:
    return {
        "content": content,
        "day_offset": day_offset,
        "amin": amin,
    }


def _event(
    event_type: str,
    title: str,
    description: str,
    day_offset: int,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "title": title,
        "description": description,
        "day_offset": day_offset,
    }


RIYADH_DEMO_CLIENTS: list[dict[str, Any]] = [
    {
        "display_name": "Saudi Horizon Real Estate Company",
        "display_name_ar": "شركة الأفق السعودية العقارية",
        "client_type": "company",
        "email": "legal@saudihorizon.com",
        "phone": "+966 11 410 2200",
        "address": "King Fahd Road, Al Olaya, Riyadh 12212",
        "trade_name": "Horizon Living",
        "cr_number": "1010923410",
        "vat_number": "310184552700003",
        "sector": "Real Estate Development",
        "incorporation_country": "Saudi Arabia",
        "notes": "Key corporate client focused on mixed-use developments in Riyadh.",
        "cases": [
            {
                "internal_ref": "MOCK-RYD-001",
                "case_number": "443251890",
                "title": "Riyadh Tower EPC Payment Claim",
                "title_ar": "مطالبة مستحقات مشروع برج الرياض",
                "practice_area": "litigation",
                "jurisdiction": "KSA",
                "priority": "high",
                "status": "active",
                "court_name": "Riyadh Commercial Court",
                "court_circuit": "Second Circuit",
                "judge_name": "Hon. Abdulrahman Al-Mutairi",
                "opposing_party": "Najd Build Contracting Co.",
                "opposing_counsel": "Al Bawardi Legal Consultants",
                "opened_days_ago": 54,
                "next_deadline_in_days": 3,
                "next_deadline_description": "Finalise claimant rebuttal and exhibit bundle",
                "description": (
                    "Claim for unpaid EPC milestone invoices and delay damages arising "
                    "from a high-rise project in north Riyadh."
                ),
                "amin_briefing": (
                    "This matter is the firm's lead commercial dispute for a flagship "
                    "real-estate client. The immediate focus is tightening the payment "
                    "claim narrative and aligning the expert delay analysis with the "
                    "signed variation orders."
                ),
                "documents": [
                    _doc(
                        "Riyadh Tower Claim Draft",
                        "docx",
                        "court_brief",
                        "pleading",
                        9,
                    ),
                    _doc(
                        "Variation Order Delay Matrix",
                        "xlsx",
                        "legal_matrix",
                        "evidence",
                        11,
                    ),
                ],
                "notes": [
                    _note(
                        "Client approved the revised damages model and instructed us to press for early expert appointment.",
                        12,
                    ),
                    _note(
                        "Amin suggests cross-checking the payment certificate chronology against the engineer's reservation letters.",
                        13,
                        amin=True,
                    ),
                ],
                "events": [
                    _event(
                        "filing",
                        "Statement of claim submitted",
                        "Initial claim package filed before the Riyadh Commercial Court.",
                        6,
                    ),
                    _event(
                        "hearing",
                        "Case management hearing scheduled",
                        "Court listed the first procedural hearing and requested a concise issues memo.",
                        17,
                    ),
                ],
            },
            {
                "internal_ref": "MOCK-RYD-002",
                "case_number": "2025-CORP-118",
                "title": "Diriyah Joint Venture Structuring",
                "title_ar": "هيكلة المشروع المشترك لبوابة الدرعية",
                "practice_area": "corporate",
                "jurisdiction": "KSA",
                "priority": "medium",
                "status": "active",
                "opposing_party": "Incoming strategic investor consortium",
                "opened_days_ago": 31,
                "next_deadline_in_days": 12,
                "next_deadline_description": "Board approval package for JV vehicle",
                "description": (
                    "Advisory mandate for a new mixed-use development vehicle, including "
                    "SHA drafting, governance rights, and CMA-facing disclosure points."
                ),
                "amin_briefing": (
                    "This advisory matter showcases the firm's transactional capability "
                    "for large Riyadh projects. The next milestone is board sign-off on "
                    "reserved matters and the investor information rights schedule."
                ),
                "documents": [
                    _doc(
                        "Diriyah JV Term Sheet",
                        "docx",
                        "contract",
                        "draft",
                        7,
                    ),
                    _doc(
                        "JV Board Approval Tracker",
                        "xlsx",
                        "tracker",
                        "general",
                        10,
                    ),
                    _doc(
                        "Investor Governance Update",
                        "pptx",
                        "status_update",
                        "board_pack",
                        14,
                    ),
                ],
                "notes": [
                    _note(
                        "Sponsor requested Arabic and English board packs for the next steering committee meeting.",
                        8,
                    ),
                ],
                "events": [
                    _event(
                        "created",
                        "Kick-off workshop completed",
                        "Corporate and finance teams aligned the first draft of the governance matrix.",
                        4,
                    ),
                ],
            },
        ],
    },
    {
        "display_name": "Al Noor Family Office",
        "display_name_ar": "مكتب النور العائلي",
        "client_type": "company",
        "email": "office@alnoorfo.sa",
        "phone": "+966 11 418 9040",
        "address": "Tahlia Street, Al Sulimaniyah, Riyadh 12223",
        "trade_name": "Al Noor FO",
        "cr_number": "1010884531",
        "vat_number": "310192210600003",
        "sector": "Family Office",
        "incorporation_country": "Saudi Arabia",
        "notes": "Private client and family-wealth mandates are coordinated through the family office GC.",
        "cases": [
            {
                "internal_ref": "MOCK-RYD-003",
                "case_number": "2025-FO-077",
                "title": "Family Charter Governance Refresh",
                "title_ar": "تحديث حوكمة ميثاق العائلة",
                "practice_area": "compliance",
                "jurisdiction": "KSA",
                "priority": "medium",
                "status": "pending",
                "opened_days_ago": 22,
                "next_deadline_in_days": 9,
                "next_deadline_description": "Circulate redline of family charter",
                "description": (
                    "Governance review for the family office, including delegated "
                    "authority, investment committee quorum, and dispute-escalation "
                    "mechanics."
                ),
                "amin_briefing": (
                    "The matter highlights recurring governance advice for high-value "
                    "family businesses. The deliverable should read as discreet, "
                    "practical counsel rather than a purely academic policy memo."
                ),
                "documents": [
                    _doc(
                        "Family Charter Redline",
                        "docx",
                        "legal_memo",
                        "advice",
                        5,
                    ),
                    _doc(
                        "Governance Action Register",
                        "xlsx",
                        "tracker",
                        "tracker",
                        9,
                    ),
                ],
                "notes": [
                    _note(
                        "General counsel wants reserved matters benchmarked against peer family offices in Riyadh.",
                        6,
                    ),
                ],
                "events": [
                    _event(
                        "created",
                        "Governance review opened",
                        "Scope confirmed with the family office general counsel and chairman's office.",
                        2,
                    ),
                ],
            }
        ],
    },
    {
        "display_name": "Riyadh MedCare Clinics Company",
        "display_name_ar": "شركة عيادات ميدكير الرياض",
        "client_type": "company",
        "email": "legal@medcare-clinics.sa",
        "phone": "+966 11 521 4430",
        "address": "Prince Mohammed bin Abdulaziz Road, Riyadh 12331",
        "trade_name": "MedCare Clinics",
        "cr_number": "1010834722",
        "vat_number": "310145009800003",
        "sector": "Healthcare",
        "incorporation_country": "Saudi Arabia",
        "cases": [
            {
                "internal_ref": "MOCK-RYD-004",
                "case_number": "445118204",
                "title": "Consultant Physician Termination Claim",
                "title_ar": "دعوى إنهاء خدمة استشاري طبيب",
                "practice_area": "employment",
                "jurisdiction": "KSA",
                "priority": "high",
                "status": "active",
                "court_name": "Riyadh Labour Court",
                "court_circuit": "First Circuit",
                "opposing_party": "Dr. Khaled Al-Shehri",
                "opposing_counsel": "Al Yaqoub Law Firm",
                "opened_days_ago": 37,
                "next_deadline_in_days": 1,
                "next_deadline_description": "Submit settlement authority note before mediation",
                "description": (
                    "Wrongful termination and bonus dispute brought by a consultant "
                    "physician following a restructuring of the outpatient department."
                ),
                "amin_briefing": (
                    "This labour case will resonate with corporate legal teams because it "
                    "combines HR process risk with reputational sensitivity in healthcare. "
                    "The demo should emphasise the mediation plan and privilege controls."
                ),
                "documents": [
                    _doc(
                        "Employment Mediation Brief",
                        "docx",
                        "court_brief",
                        "pleading",
                        8,
                    ),
                    _doc(
                        "Termination Timeline Tracker",
                        "xlsx",
                        "tracker",
                        "evidence",
                        10,
                    ),
                ],
                "notes": [
                    _note(
                        "Finance confirmed the disputed incentive figures and approved a without-prejudice settlement range.",
                        10,
                    ),
                    _note(
                        "Amin recommends a short chronology for the mediator highlighting the final warning and patient complaint record.",
                        11,
                        amin=True,
                    ),
                ],
                "events": [
                    _event(
                        "hearing",
                        "Labour mediation session listed",
                        "The court referred the dispute to a mandatory mediation session next week.",
                        14,
                    ),
                ],
            },
            {
                "internal_ref": "MOCK-RYD-005",
                "case_number": "2025-HC-014",
                "title": "MOH Licensing Compliance Review",
                "title_ar": "مراجعة امتثال تراخيص وزارة الصحة",
                "practice_area": "compliance",
                "jurisdiction": "KSA",
                "priority": "medium",
                "status": "on_hold",
                "opened_days_ago": 18,
                "next_deadline_in_days": 16,
                "next_deadline_description": "Hold pending regulator feedback on clinic expansion",
                "description": (
                    "Review of clinical licensing, physician credentialing, and branch "
                    "expansion documentation for a new specialist centre in north Riyadh."
                ),
                "amin_briefing": (
                    "This file gives the demo a regulatory-advisory angle. It should feel "
                    "active but paused pending Ministry feedback, which makes the on-hold "
                    "status meaningful in the list view."
                ),
                "documents": [
                    _doc(
                        "MOH Compliance Memo",
                        "docx",
                        "legal_memo",
                        "advice",
                        7,
                    ),
                ],
                "notes": [
                    _note(
                        "Expansion application pack is complete; waiting for the client's engineering annexures.",
                        9,
                    ),
                ],
                "events": [
                    _event(
                        "status_change",
                        "Status changed to on_hold",
                        "Matter paused pending regulator clarification on the specialist licence category.",
                        12,
                    ),
                ],
            },
        ],
    },
    {
        "display_name": "Najd Logistics Services Company",
        "display_name_ar": "شركة نجد للخدمات اللوجستية",
        "client_type": "company",
        "email": "claims@najdlogistics.sa",
        "phone": "+966 11 539 2100",
        "address": "Khurais Road Logistics Zone, Riyadh 14324",
        "trade_name": "Najd Logistics",
        "cr_number": "1010798813",
        "vat_number": "310210440900003",
        "sector": "Logistics",
        "incorporation_country": "Saudi Arabia",
        "cases": [
            {
                "internal_ref": "MOCK-RYD-006",
                "case_number": "445891230",
                "title": "Promissory Note Enforcement Against Fleet Supplier",
                "title_ar": "تنفيذ سند لأمر ضد مورّد الأسطول",
                "practice_area": "enforcement",
                "jurisdiction": "KSA",
                "priority": "high",
                "status": "active",
                "court_name": "Riyadh Execution Court",
                "opposing_party": "Atlas Fleet Equipment Co.",
                "opened_days_ago": 28,
                "next_deadline_in_days": 5,
                "next_deadline_description": "File response to debtor objection",
                "description": (
                    "Execution proceedings for a SAR 6.2M promissory note issued in "
                    "connection with a trailer procurement programme."
                ),
                "amin_briefing": (
                    "This is a strong enforcement showcase because the file has a clean "
                    "instrument, a live debtor objection, and a near-term court deadline. "
                    "It demonstrates fast-moving recovery work for a logistics client."
                ),
                "documents": [
                    _doc(
                        "Execution Court Submission",
                        "docx",
                        "court_brief",
                        "pleading",
                        6,
                    ),
                    _doc(
                        "Recovery Exposure Tracker",
                        "xlsx",
                        "tracker",
                        "tracker",
                        7,
                    ),
                ],
                "notes": [
                    _note(
                        "Operations team delivered stamped originals of the promissory note and supplier acknowledgments.",
                        7,
                    ),
                ],
                "events": [
                    _event(
                        "filing",
                        "Execution application lodged",
                        "Urgent filing made with supporting note instrument evidence.",
                        3,
                    ),
                ],
            },
            {
                "internal_ref": "MOCK-RYD-007",
                "case_number": "444991208",
                "title": "Warehouse Lease Termination Dispute",
                "title_ar": "نزاع إنهاء عقد إيجار المستودع",
                "practice_area": "litigation",
                "jurisdiction": "KSA",
                "priority": "medium",
                "status": "pending",
                "court_name": "Riyadh General Court",
                "opposing_party": "Eastern Storage REIT",
                "opened_days_ago": 16,
                "next_deadline_in_days": 13,
                "next_deadline_description": "File damages position on defective handover",
                "description": (
                    "Landlord-tenant dispute regarding early termination, reinstatement "
                    "works, and withheld security deposit for a cold-storage warehouse."
                ),
                "amin_briefing": (
                    "The lease dispute adds a property flavour to the demo while staying "
                    "commercially grounded. The story should focus on evidence assembly and "
                    "quantum positioning rather than pure litigation drama."
                ),
                "documents": [
                    _doc(
                        "Lease Termination Position Paper",
                        "docx",
                        "legal_memo",
                        "advice",
                        6,
                    ),
                ],
                "notes": [
                    _note(
                        "Site photos and mechanical inspection report received from the client operations lead.",
                        8,
                    ),
                ],
                "events": [
                    _event(
                        "deadline_set",
                        "Quantum model requested",
                        "Client asked for a revised damages estimate covering reinstatement and storage disruption.",
                        10,
                    ),
                ],
            },
        ],
    },
    {
        "display_name": "Siraj Tech Solutions Limited",
        "display_name_ar": "شركة سراج للحلول التقنية",
        "client_type": "company",
        "email": "counsel@sirajtech.sa",
        "phone": "+966 11 445 8801",
        "address": "Digital City, Riyadh 12382",
        "trade_name": "Siraj Tech",
        "cr_number": "1011015528",
        "vat_number": "310223114100003",
        "sector": "Technology",
        "incorporation_country": "Saudi Arabia",
        "cases": [
            {
                "internal_ref": "MOCK-RYD-008",
                "case_number": "2025-TECH-041",
                "title": "SaaS Master Services Agreement Renewal",
                "title_ar": "تجديد اتفاقية الخدمات البرمجية الرئيسية",
                "practice_area": "corporate",
                "jurisdiction": "KSA",
                "priority": "medium",
                "status": "active",
                "opposing_party": "National Retail Platforms Co.",
                "opened_days_ago": 20,
                "next_deadline_in_days": 6,
                "next_deadline_description": "Deliver final liability cap options",
                "description": (
                    "Commercial renegotiation of a flagship SaaS contract, with focus on "
                    "liability caps, data localisation, and audit rights."
                ),
                "amin_briefing": (
                    "This file shows the product handling day-to-day commercial contracting "
                    "work for a Saudi tech client. The most visible discussion point is the "
                    "balanced position on data-hosting and indemnity language."
                ),
                "documents": [
                    _doc(
                        "MSA Renewal Redline",
                        "docx",
                        "contract",
                        "draft",
                        5,
                    ),
                    _doc(
                        "Commercial Negotiation Deck",
                        "pptx",
                        "legal_overview",
                        "board_pack",
                        9,
                    ),
                ],
                "notes": [
                    _note(
                        "Sales team accepted a narrower SLA credit model if the customer drops unlimited audit access.",
                        7,
                    ),
                ],
                "events": [
                    _event(
                        "created",
                        "Renewal workstream launched",
                        "Commercial and privacy issues list prepared for the client GC.",
                        3,
                    ),
                ],
            },
            {
                "internal_ref": "MOCK-RYD-009",
                "case_number": "2025-DP-022",
                "title": "Data Incident Response Advisory",
                "title_ar": "استشارة الاستجابة لحادثة بيانات",
                "practice_area": "compliance",
                "jurisdiction": "KSA",
                "priority": "high",
                "status": "active",
                "opened_days_ago": 9,
                "next_deadline_in_days": 2,
                "next_deadline_description": "Finalise incident notification assessment",
                "description": (
                    "Urgent advisory on a suspected personal-data incident affecting a "
                    "regional HR platform, including reporting thresholds and containment."
                ),
                "amin_briefing": (
                    "This matter gives the demo a sharp, modern advisory example with a "
                    "clear executive timeline. The emphasis should be on triage, regulator "
                    "analysis, and board-ready communications."
                ),
                "documents": [
                    _doc(
                        "Incident Response Memo",
                        "docx",
                        "legal_memo",
                        "advice",
                        2,
                    ),
                    _doc(
                        "Breach Response Tracker",
                        "xlsx",
                        "tracker",
                        "tracker",
                        3,
                    ),
                ],
                "notes": [
                    _note(
                        "Forensics vendor confirmed no evidence of onward data exfiltration so far.",
                        2,
                    ),
                    _note(
                        "Amin flagged that the customer notice should be aligned with the client's bilingual communications policy.",
                        3,
                        amin=True,
                    ),
                ],
                "events": [
                    _event(
                        "amin_action",
                        "Privilege protocol activated",
                        "Outside counsel instructions issued to keep forensic workstream under privilege where possible.",
                        1,
                    ),
                ],
            },
        ],
    },
    {
        "display_name": "Ajyal Community Association",
        "display_name_ar": "جمعية أجيال المجتمعية",
        "client_type": "organisation",
        "email": "governance@ajyal.org.sa",
        "phone": "+966 11 480 2007",
        "address": "Imam Saud Road, Riyadh 12474",
        "org_type": "non-profit",
        "notes": "Representative non-profit / organisation client for public-interest and governance work.",
        "cases": [
            {
                "internal_ref": "MOCK-RYD-010",
                "case_number": "2025-NPO-008",
                "title": "Grant Agreement Governance Review",
                "title_ar": "مراجعة حوكمة اتفاقية المنحة",
                "practice_area": "compliance",
                "jurisdiction": "KSA",
                "priority": "low",
                "status": "active",
                "opened_days_ago": 24,
                "next_deadline_in_days": 11,
                "next_deadline_description": "Issue governance comments on donor reporting obligations",
                "description": (
                    "Review of donor grant conditions, delegated signing thresholds, and "
                    "reporting obligations for a Riyadh-based community programme."
                ),
                "amin_briefing": (
                    "This file broadens the client mix without leaving the operations "
                    "workflow. It should read as a clean governance review for a mission-led "
                    "organisation, with practical next steps."
                ),
                "documents": [
                    _doc(
                        "Grant Governance Memo",
                        "docx",
                        "legal_memo",
                        "advice",
                        6,
                    ),
                ],
                "notes": [
                    _note(
                        "Client requested a short annex summarising who can sign donor amendments under the bylaws.",
                        8,
                    ),
                ],
                "events": [
                    _event(
                        "created",
                        "Governance review initiated",
                        "Association leadership approved the scope and donor-facing deliverables.",
                        3,
                    ),
                ],
            }
        ],
    },
    {
        "display_name": "Faisal Al-Qahtani",
        "display_name_ar": "فيصل القحطاني",
        "client_type": "individual",
        "email": "faisal.qahtani@email.com",
        "phone": "+966 55 720 1890",
        "address": "Al Yasmin District, Riyadh 13326",
        "national_id": "1098765432",
        "nationality": "Saudi",
        "notes": "Private client matters coordinated discreetly with personal assistant.",
        "cases": [
            {
                "internal_ref": "MOCK-RYD-011",
                "case_number": "445602114",
                "title": "Executive Employment Bonus Claim",
                "title_ar": "مطالبة مكافأة تنفيذية",
                "practice_area": "employment",
                "jurisdiction": "KSA",
                "priority": "high",
                "status": "active",
                "court_name": "Riyadh Labour Court",
                "opposing_party": "Gulf Manufacturing Holding",
                "opposing_counsel": "Mubarak & Co.",
                "opened_days_ago": 34,
                "next_deadline_in_days": 4,
                "next_deadline_description": "Submit witness summary for final labour session",
                "description": (
                    "Senior executive seeks unpaid bonus, restricted stock cash-out, and "
                    "end-of-service entitlements following termination."
                ),
                "amin_briefing": (
                    "This private-client employment case adds contrast to the corporate "
                    "portfolio while staying highly relatable to business owners and HR "
                    "teams. It also gives the dashboard another urgent active matter."
                ),
                "documents": [
                    _doc(
                        "Bonus Claim Hearing Bundle",
                        "docx",
                        "court_brief",
                        "hearing_bundle",
                        7,
                    ),
                ],
                "notes": [
                    _note(
                        "Client approved settlement floor but prefers to finish the hearing cycle unless payment terms improve materially.",
                        9,
                    ),
                ],
                "events": [
                    _event(
                        "hearing",
                        "Final labour session listed",
                        "Court directed the parties to exchange concise witness summaries before the next session.",
                        16,
                    ),
                ],
            },
            {
                "internal_ref": "MOCK-RYD-012",
                "case_number": "444781550",
                "title": "Residential Boundary and Easement Dispute",
                "title_ar": "نزاع حدود وارتفاق عقاري سكني",
                "practice_area": "litigation",
                "jurisdiction": "KSA",
                "priority": "medium",
                "status": "on_hold",
                "court_name": "Riyadh General Court",
                "opposing_party": "Adjacent landowner",
                "opened_days_ago": 41,
                "next_deadline_in_days": 18,
                "next_deadline_description": "Await municipality technical report",
                "description": (
                    "Property dispute concerning access rights, shared boundary lines, and "
                    "encroachment allegations in a north Riyadh villa district."
                ),
                "amin_briefing": (
                    "This file gives the demo a very human private-client story. The "
                    "on-hold status is useful because it reflects a real waiting period for "
                    "municipality evidence rather than internal inactivity."
                ),
                "documents": [
                    _doc(
                        "Boundary Dispute Brief",
                        "docx",
                        "legal_memo",
                        "advice",
                        8,
                    ),
                ],
                "notes": [
                    _note(
                        "Municipality survey request submitted; client asked for weekly status updates only if there is movement.",
                        10,
                    ),
                ],
                "events": [
                    _event(
                        "status_change",
                        "Status changed to on_hold",
                        "Matter paused until the municipality surveyor issues the technical report.",
                        13,
                    ),
                ],
            },
        ],
    },
    {
        "display_name": "Sara Al-Harbi",
        "display_name_ar": "سارة الحربي",
        "client_type": "individual",
        "email": "s.harbi@email.com",
        "phone": "+966 50 112 7740",
        "address": "Hittin District, Riyadh 13512",
        "national_id": "1084456671",
        "nationality": "Saudi",
        "cases": [
            {
                "internal_ref": "MOCK-RYD-013",
                "case_number": "445991774",
                "title": "Inheritance Asset Partition Advisory",
                "title_ar": "استشارة قسمة أصول التركة",
                "practice_area": "corporate",
                "jurisdiction": "KSA",
                "priority": "medium",
                "status": "active",
                "opened_days_ago": 26,
                "next_deadline_in_days": 7,
                "next_deadline_description": "Share bilingual inheritance roadmap with client family office",
                "description": (
                    "Advisory mandate on estate-asset partition, corporate holdings, and "
                    "board reconstitution following succession."
                ),
                "amin_briefing": (
                    "This is a polished private-client advisory matter that still feels "
                    "commercial. It demonstrates that the product can handle sensitive, "
                    "multi-stakeholder work beyond court disputes."
                ),
                "documents": [
                    _doc(
                        "Inheritance Structuring Memo",
                        "docx",
                        "legal_memo",
                        "advice",
                        7,
                    ),
                    _doc(
                        "Estate Asset Schedule",
                        "xlsx",
                        "tracker",
                        "tracker",
                        8,
                    ),
                ],
                "notes": [
                    _note(
                        "Client wants the next draft to separate immediate operational actions from long-term governance recommendations.",
                        8,
                    ),
                ],
                "events": [
                    _event(
                        "created",
                        "Succession workstream opened",
                        "Kick-off completed with family representatives and external accountants.",
                        4,
                    ),
                ],
            },
            {
                "internal_ref": "MOCK-RYD-014",
                "case_number": "2024-REC-219",
                "title": "Private Debt Recovery Settlement",
                "title_ar": "تسوية استرداد دين خاص",
                "practice_area": "enforcement",
                "jurisdiction": "KSA",
                "priority": "low",
                "status": "closed",
                "opened_days_ago": 63,
                "closed_days_ago": 6,
                "description": (
                    "Recovery mandate that concluded with a negotiated settlement and "
                    "structured repayment of a personal lending exposure."
                ),
                "amin_briefing": (
                    "A recently closed file helps the lists and dashboard feel like a real "
                    "practice, not just a queue of open matters. It also shows a clean "
                    "successful outcome that can be mentioned in the demo narrative."
                ),
                "documents": [
                    _doc(
                        "Settlement Memorandum",
                        "docx",
                        "legal_memo",
                        "settlement",
                        9,
                    ),
                ],
                "notes": [
                    _note(
                        "Settlement funds received and release documentation countersigned by both parties.",
                        11,
                    ),
                ],
                "events": [
                    _event(
                        "status_change",
                        "Matter closed",
                        "Payment received in full and settlement release filed.",
                        57,
                    ),
                ],
            },
        ],
    },
]


def _event_timestamp(opened_at: date, day_offset: int, hour: int = 10) -> datetime:
    return datetime.combine(
        opened_at + timedelta(days=day_offset),
        time(hour=hour, minute=0),
        tzinfo=timezone.utc,
    )


def _demo_metadata(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        DEMO_METADATA_KEY: RIYADH_DEMO_VERSION,
        "demo_dataset": "riyadh_law_practice",
    }
    if extra:
        metadata.update(extra)
    return metadata


def _is_demo_document(document: OfficeDocument) -> bool:
    metadata = document.metadata_ or {}
    return bool(metadata.get(DEMO_METADATA_KEY))


async def count_demo_dataset(db: AsyncSession, org_id: str) -> DemoSeedSummary:
    summary = DemoSeedSummary()

    demo_cases = (
        await db.execute(
            select(Case.id, Case.client_id).where(
                Case.org_id == org_id,
                Case.internal_ref.like(f"{MOCK_REF_PREFIX}%"),
            )
        )
    ).all()

    if demo_cases:
        case_ids = [row[0] for row in demo_cases]
        summary.cases_count = len(case_ids)
        summary.clients_count = len({row[1] for row in demo_cases})
        summary.notes_count = (
            (
                await db.execute(
                    select(func.count())
                    .select_from(CaseNote)
                    .where(CaseNote.case_id.in_(case_ids))
                )
            ).scalar()
            or 0
        )
        summary.events_count = (
            (
                await db.execute(
                    select(func.count())
                    .select_from(CaseEvent)
                    .where(CaseEvent.case_id.in_(case_ids))
                )
            ).scalar()
            or 0
        )

    office_docs = (
        await db.execute(select(OfficeDocument).where(OfficeDocument.org_id == org_id))
    ).scalars().all()
    summary.documents_count = len([doc for doc in office_docs if _is_demo_document(doc)])

    return summary


async def wipe_demo_dataset(
    ctx: RequestContext,
    db: AsyncSession,
    org_id: str,
) -> DemoSeedSummary:
    del ctx

    summary = await count_demo_dataset(db, org_id)
    service = OfficeService(db)

    demo_cases = (
        await db.execute(
            select(Case).where(
                Case.org_id == org_id,
                Case.internal_ref.like(f"{MOCK_REF_PREFIX}%"),
            )
        )
    ).scalars().all()
    demo_client_ids = {case.client_id for case in demo_cases}

    demo_docs = (
        await db.execute(select(OfficeDocument).where(OfficeDocument.org_id == org_id))
    ).scalars().all()
    demo_docs = [doc for doc in demo_docs if _is_demo_document(doc)]

    for case in demo_cases:
        await db.delete(case)

    for document in demo_docs:
        try:
            service.storage_client.delete_object(document.storage_key)
        except S3StorageError as err:
            logger.warning("Failed to delete demo document object %s: %s", document.storage_key, err)
        await db.delete(document)

    clients_deleted = 0
    for client_id in demo_client_ids:
        remaining = (
            await db.execute(
                select(Case.id).where(
                    Case.client_id == client_id,
                    ~Case.internal_ref.like(f"{MOCK_REF_PREFIX}%"),
                )
            )
        ).first()
        if remaining:
            continue

        client = await db.get(Client, client_id)
        if client:
            await db.delete(client)
            clients_deleted += 1

    await db.commit()
    summary.clients_count = clients_deleted
    return summary


async def seed_demo_dataset(
    ctx: RequestContext,
    db: AsyncSession,
    org_id: str,
) -> DemoSeedSummary:
    summary = DemoSeedSummary()
    service = OfficeService(db)
    today = date.today()
    document_seeding_available = True

    for client_fixture in RIYADH_DEMO_CLIENTS:
        client = Client(
            id=str(uuid4()),
            org_id=org_id,
            client_type=client_fixture["client_type"],
            display_name=client_fixture["display_name"],
            display_name_ar=client_fixture.get("display_name_ar"),
            email=client_fixture.get("email"),
            phone=client_fixture.get("phone"),
            address=client_fixture.get("address"),
            notes=client_fixture.get("notes"),
            national_id=client_fixture.get("national_id"),
            nationality=client_fixture.get("nationality"),
            trade_name=client_fixture.get("trade_name"),
            cr_number=client_fixture.get("cr_number"),
            vat_number=client_fixture.get("vat_number"),
            sector=client_fixture.get("sector"),
            incorporation_country=client_fixture.get("incorporation_country"),
            org_type=client_fixture.get("org_type"),
            created_by=ctx.user.id,
        )
        db.add(client)
        await db.flush()
        summary.clients_count += 1

        for case_fixture in client_fixture["cases"]:
            opened_at = today - timedelta(days=case_fixture["opened_days_ago"])
            next_deadline = case_fixture.get("next_deadline_in_days")
            closed_days_ago = case_fixture.get("closed_days_ago")

            case = Case(
                id=str(uuid4()),
                org_id=org_id,
                client_id=client.id,
                title=case_fixture["title"],
                title_ar=case_fixture.get("title_ar"),
                case_number=case_fixture.get("case_number"),
                internal_ref=case_fixture["internal_ref"],
                practice_area=case_fixture["practice_area"],
                jurisdiction=case_fixture["jurisdiction"],
                priority=case_fixture["priority"],
                status=case_fixture["status"],
                court_name=case_fixture.get("court_name"),
                court_circuit=case_fixture.get("court_circuit"),
                judge_name=case_fixture.get("judge_name"),
                opposing_party=case_fixture.get("opposing_party"),
                opposing_counsel=case_fixture.get("opposing_counsel"),
                opened_at=opened_at,
                closed_at=today - timedelta(days=closed_days_ago) if closed_days_ago else None,
                next_deadline=today + timedelta(days=next_deadline) if next_deadline is not None else None,
                next_deadline_description=case_fixture.get("next_deadline_description"),
                description=case_fixture.get("description"),
                amin_briefing=case_fixture.get("amin_briefing"),
                lead_lawyer=ctx.user.id,
                created_by=ctx.user.id,
            )
            db.add(case)
            await db.flush()
            summary.cases_count += 1

            created_event = CaseEvent(
                case_id=case.id,
                event_type="created",
                title="Case opened",
                description=f"Case '{case.title}' opened for {client.display_name}.",
                event_date=_event_timestamp(opened_at, 0, 9),
                created_by=ctx.user.id,
                metadata_=_demo_metadata({"internal_ref": case.internal_ref}),
            )
            db.add(created_event)
            summary.events_count += 1

            if case.next_deadline and case.next_deadline_description:
                deadline_offset = max(case_fixture["opened_days_ago"] - next_deadline - 5, 1)
                db.add(
                    CaseEvent(
                        case_id=case.id,
                        event_type="deadline_set",
                        title=f"Deadline set: {case.next_deadline_description}",
                        description=f"Next deadline scheduled for {case.next_deadline.isoformat()}",
                        event_date=_event_timestamp(opened_at, min(deadline_offset, 5), 11),
                        created_by=ctx.user.id,
                        metadata_=_demo_metadata({"internal_ref": case.internal_ref}),
                    )
                )
                summary.events_count += 1

            for extra_event in case_fixture.get("events", []):
                db.add(
                    CaseEvent(
                        case_id=case.id,
                        event_type=extra_event["event_type"],
                        title=extra_event["title"],
                        description=extra_event.get("description"),
                        event_date=_event_timestamp(opened_at, extra_event["day_offset"], 14),
                        created_by=ctx.user.id,
                        metadata_=_demo_metadata({"internal_ref": case.internal_ref}),
                    )
                )
                summary.events_count += 1

            for note_fixture in case_fixture.get("notes", []):
                is_amin_generated = bool(note_fixture.get("amin"))
                note = CaseNote(
                    case_id=case.id,
                    content=note_fixture["content"],
                    is_amin_generated=is_amin_generated,
                    created_by=None if is_amin_generated else ctx.user.id,
                )
                db.add(note)
                summary.notes_count += 1

                db.add(
                    CaseEvent(
                        case_id=case.id,
                        event_type="note_added",
                        title="Note added" + (" by Amin" if is_amin_generated else ""),
                        description=note_fixture["content"][:200],
                        event_date=_event_timestamp(opened_at, note_fixture["day_offset"], 15),
                        created_by=None if is_amin_generated else ctx.user.id,
                        metadata_=_demo_metadata({"internal_ref": case.internal_ref}),
                    )
                )
                summary.events_count += 1

            for document_fixture in case_fixture.get("documents", []):
                if not document_seeding_available:
                    continue

                try:
                    document = await _create_demo_document(
                        service=service,
                        org_id=org_id,
                        owner_id=ctx.user.id,
                        title=document_fixture["title"],
                        doc_type=document_fixture["doc_type"],
                        template=document_fixture["template"],
                        metadata=_demo_metadata(
                            {
                                "case_id": case.id,
                                "case_ref": case.internal_ref,
                                "document_role": document_fixture["role"],
                            }
                        ),
                    )
                    db.add(document)
                    await db.flush()

                    db.add(
                        CaseDocument(
                            case_id=case.id,
                            document_id=document.id,
                            attached_by=ctx.user.id,
                            document_role=document_fixture["role"],
                        )
                    )
                    db.add(
                        CaseEvent(
                            case_id=case.id,
                            event_type="document_added",
                            title=f"Document attached: {document.title}",
                            description=f"Role: {document_fixture['role']}",
                            event_date=_event_timestamp(
                                opened_at,
                                document_fixture["day_offset"],
                                13,
                            ),
                            created_by=ctx.user.id,
                            metadata_=_demo_metadata({"internal_ref": case.internal_ref}),
                        )
                    )
                    summary.documents_count += 1
                    summary.events_count += 1
                except Exception as err:
                    document_seeding_available = False
                    warning = (
                        "Office document storage is unavailable, so demo clients and cases "
                        "were loaded without seeded documents."
                    )
                    if warning not in summary.warnings:
                        summary.warnings.append(warning)
                    logger.warning(
                        "Skipping demo office document seeding after failure for org %s: %s",
                        org_id,
                        err,
                    )

    await db.commit()
    return summary


async def _create_demo_document(
    *,
    service: OfficeService,
    org_id: str,
    owner_id: str,
    title: str,
    doc_type: str,
    template: str,
    metadata: dict[str, Any],
) -> OfficeDocument:
    file_bytes = generate_document(doc_type=doc_type, template=template, title=title)
    doc_id = str(uuid4())
    storage_key = f"{DEMO_STORAGE_PREFIX}/{org_id}/{doc_id}.{doc_type}"

    service.storage_client.put_object(
        key=storage_key,
        data=file_bytes,
        content_type=OFFICE_CONTENT_TYPES[doc_type],
    )

    return OfficeDocument(
        id=doc_id,
        org_id=org_id,
        owner_id=owner_id,
        title=title,
        doc_type=doc_type,
        storage_key=storage_key,
        size_bytes=len(file_bytes),
        last_modified_by=owner_id,
        metadata_=metadata,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
