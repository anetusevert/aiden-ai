"""Seed router — admin-only endpoints to load/wipe mock demo data."""

import logging
from datetime import date, timedelta
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import RequestContext, require_admin
from src.models.case import Case
from src.models.client import Client
from src.services.organization_access_service import ensure_workspace_org_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/seed", tags=["seed"])

MOCK_REF_PREFIX = "MOCK-"


class SeedResponse(BaseModel):
    action: str
    cases_count: int
    clients_count: int


async def _get_org_id(ctx: RequestContext, db: AsyncSession) -> str:
    org_id = await ensure_workspace_org_access(
        db,
        tenant_id=ctx.tenant.id,
        workspace_id=ctx.workspace.id if ctx.workspace else "",
        workspace_name=ctx.workspace.name if ctx.workspace else None,
        user_id=ctx.user.id,
        workspace_role=ctx.role or "ADMIN",
    )
    if not org_id:
        raise HTTPException(status_code=400, detail="User is not a member of any organization")
    return org_id


MOCK_DATA = [
    {
        "ref": "MOCK-001",
        "title": "Al-Rajhi Bank vs. Tadawul Group",
        "title_ar": "بنك الراجحي ضد مجموعة تداول",
        "practice_area": "litigation",
        "jurisdiction": "KSA",
        "priority": "high",
        "status": "active",
        "court_name": "Riyadh Commercial Court",
        "court_circuit": "3rd Circuit",
        "opposing_party": "Tadawul Group LLC",
        "opposing_counsel": "Hasan & Partners",
        "deadline_offset": 5,
        "deadline_desc": "Filing deadline for Statement of Defence",
        "description": "Commercial dispute arising from a failed securities settlement agreement. Al-Rajhi Bank alleges breach of clearing obligations under the Capital Market Authority regulations.",
        "client_name": "Al-Rajhi Bank",
        "client_type": "company",
        "client_sector": "Banking & Finance",
    },
    {
        "ref": "MOCK-002",
        "title": "Emaar Properties JV Formation",
        "title_ar": "تأسيس مشروع مشترك إعمار العقارية",
        "practice_area": "corporate",
        "jurisdiction": "UAE",
        "priority": "medium",
        "status": "active",
        "deadline_offset": 14,
        "deadline_desc": "Board resolution deadline for JV approval",
        "description": "Structuring a joint venture between Emaar Properties and a sovereign wealth fund for a mixed-use development in Dubai Creek Harbour.",
        "client_name": "Emaar Properties PJSC",
        "client_type": "company",
        "client_sector": "Real Estate",
    },
    {
        "ref": "MOCK-003",
        "title": "SAGIA Foreign Investment Compliance",
        "title_ar": "امتثال الاستثمار الأجنبي – ساجيا",
        "practice_area": "compliance",
        "jurisdiction": "KSA",
        "priority": "high",
        "status": "active",
        "deadline_offset": 3,
        "deadline_desc": "Regulatory filing deadline with SAGIA",
        "description": "Annual compliance review for a multinational's KSA operations under the Foreign Investment Law and SAGIA licensing requirements.",
        "client_name": "Siemens Saudi Arabia",
        "client_type": "company",
        "client_sector": "Industrial",
    },
    {
        "ref": "MOCK-004",
        "title": "DIFC Employee Termination Dispute",
        "title_ar": "نزاع إنهاء خدمة موظف – مركز دبي المالي",
        "practice_area": "employment",
        "jurisdiction": "DIFC",
        "priority": "medium",
        "status": "on_hold",
        "deadline_offset": 21,
        "deadline_desc": "Mediation session scheduled",
        "description": "Wrongful termination claim by a senior portfolio manager. Employee alleges constructive dismissal; employer cites performance grounds under DIFC Employment Law No. 2.",
        "client_name": "Gulf Capital Advisors",
        "client_type": "company",
        "client_sector": "Financial Services",
    },
    {
        "ref": "MOCK-005",
        "title": "ICC Arbitration — Maritime Freight",
        "title_ar": "تحكيم غرفة التجارة الدولية – شحن بحري",
        "practice_area": "dispute_resolution",
        "jurisdiction": "UAE",
        "priority": "high",
        "status": "active",
        "court_name": "ICC Arbitration Centre, Abu Dhabi",
        "deadline_offset": 10,
        "deadline_desc": "Submission of Claimant's Memorial",
        "description": "International arbitration under ICC Rules concerning a USD 45M charter party dispute. Vessel owner claims demurrage and deadfreight against charterer.",
        "client_name": "Arabian Maritime Co.",
        "client_type": "company",
        "client_sector": "Shipping & Logistics",
    },
    {
        "ref": "MOCK-006",
        "title": "Promissory Note Enforcement",
        "title_ar": "تنفيذ سند لأمر",
        "practice_area": "enforcement",
        "jurisdiction": "KSA",
        "priority": "low",
        "status": "pending",
        "court_name": "Jeddah Execution Court",
        "deadline_offset": 30,
        "deadline_desc": "Enforcement hearing date",
        "description": "Enforcement of a SAR 2.4M promissory note through the Execution Court. Debtor has filed an objection citing partial payment.",
        "client_name": "Al-Sulaiman Trading",
        "client_type": "company",
        "client_sector": "Trading",
    },
    {
        "ref": "MOCK-007",
        "title": "Saudi Telecom Regulatory Filing",
        "title_ar": "إيداع تنظيمي – الاتصالات السعودية",
        "practice_area": "compliance",
        "jurisdiction": "KSA",
        "priority": "medium",
        "status": "active",
        "deadline_offset": 7,
        "deadline_desc": "CITC annual compliance submission",
        "description": "Preparing the annual regulatory submission to the Communications, Space and Technology Commission, covering spectrum allocation compliance and consumer protection metrics.",
        "client_name": "Saudi Telecom Company",
        "client_type": "company",
        "client_sector": "Telecommunications",
    },
    {
        "ref": "MOCK-008",
        "title": "ADGM Fund Structure Advisory",
        "title_ar": "استشارات هيكل صندوق – سوق أبوظبي العالمي",
        "practice_area": "corporate",
        "jurisdiction": "ADGM",
        "priority": "high",
        "status": "active",
        "deadline_offset": 12,
        "deadline_desc": "FSRA application submission deadline",
        "description": "Advising on the establishment of a USD 200M private equity fund domiciled in ADGM, including FSRA licensing, fund documentation, and investor onboarding frameworks.",
        "client_name": "Mubadala Capital",
        "client_type": "company",
        "client_sector": "Investment Management",
    },
    {
        "ref": "MOCK-009",
        "title": "Qatar Airways Labor Mediation",
        "title_ar": "وساطة عمالية – الخطوط الجوية القطرية",
        "practice_area": "employment",
        "jurisdiction": "Qatar",
        "priority": "low",
        "status": "active",
        "deadline_offset": 18,
        "deadline_desc": "Ministry of Labour mediation hearing",
        "description": "Group labor dispute involving cabin crew alleging unpaid overtime and end-of-service gratuity miscalculation under Qatar Labour Law No. 14 of 2004.",
        "client_name": "Qatar Airways Group",
        "client_type": "company",
        "client_sector": "Aviation",
    },
    {
        "ref": "MOCK-010",
        "title": "Cross-Border Debt Recovery — GCC",
        "title_ar": "استرداد ديون عابر للحدود – دول الخليج",
        "practice_area": "enforcement",
        "jurisdiction": "GCC",
        "priority": "high",
        "status": "pending",
        "deadline_offset": 8,
        "deadline_desc": "Recognition application filing in Riyadh",
        "description": "Enforcing a UAE court judgment in KSA under the GCC Convention on the Execution of Judgments. Debt of AED 18M arising from a construction contract default.",
        "client_name": "Arabtec Holding",
        "client_type": "company",
        "client_sector": "Construction",
    },
]


@router.post("/mock-cases", response_model=SeedResponse)
async def seed_mock_cases(
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    org_id = await _get_org_id(ctx, db)

    existing = (await db.execute(
        select(Case).where(Case.org_id == org_id, Case.internal_ref.like(f"{MOCK_REF_PREFIX}%"))
    )).scalars().all()

    if existing:
        return SeedResponse(action="already_exists", cases_count=len(existing), clients_count=0)

    today = date.today()
    clients_created = 0

    for item in MOCK_DATA:
        existing_client = (await db.execute(
            select(Client).where(
                Client.org_id == org_id,
                Client.display_name == item["client_name"],
            )
        )).scalar_one_or_none()

        if existing_client:
            client_id = existing_client.id
        else:
            client = Client(
                id=str(uuid4()),
                org_id=org_id,
                client_type=item["client_type"],
                display_name=item["client_name"],
                sector=item.get("client_sector"),
                created_by=ctx.user.id,
            )
            db.add(client)
            await db.flush()
            client_id = client.id
            clients_created += 1

        case = Case(
            id=str(uuid4()),
            org_id=org_id,
            client_id=client_id,
            title=item["title"],
            title_ar=item.get("title_ar"),
            internal_ref=item["ref"],
            practice_area=item["practice_area"],
            jurisdiction=item["jurisdiction"],
            priority=item["priority"],
            status=item["status"],
            court_name=item.get("court_name"),
            court_circuit=item.get("court_circuit"),
            opposing_party=item.get("opposing_party"),
            opposing_counsel=item.get("opposing_counsel"),
            next_deadline=today + timedelta(days=item.get("deadline_offset", 14)),
            next_deadline_description=item.get("deadline_desc"),
            description=item.get("description"),
            created_by=ctx.user.id,
        )
        db.add(case)

    await db.commit()
    logger.info("Seeded %d mock cases for org %s", len(MOCK_DATA), org_id)
    return SeedResponse(action="created", cases_count=len(MOCK_DATA), clients_count=clients_created)


@router.delete("/mock-cases", response_model=SeedResponse)
async def wipe_mock_cases(
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    org_id = await _get_org_id(ctx, db)

    mock_cases = (await db.execute(
        select(Case).where(Case.org_id == org_id, Case.internal_ref.like(f"{MOCK_REF_PREFIX}%"))
    )).scalars().all()

    mock_client_ids = {c.client_id for c in mock_cases}
    cases_deleted = len(mock_cases)

    for case in mock_cases:
        await db.delete(case)

    clients_deleted = 0
    for cid in mock_client_ids:
        remaining = (await db.execute(
            select(Case).where(Case.client_id == cid, ~Case.internal_ref.like(f"{MOCK_REF_PREFIX}%"))
        )).scalars().first()
        if not remaining:
            client = await db.get(Client, cid)
            if client:
                await db.delete(client)
                clients_deleted += 1

    await db.commit()
    logger.info("Wiped %d mock cases, %d orphaned clients for org %s", cases_deleted, clients_deleted, org_id)
    return SeedResponse(action="wiped", cases_count=cases_deleted, clients_count=clients_deleted)
