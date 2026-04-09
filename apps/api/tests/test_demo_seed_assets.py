"""Unit tests for demo seed assets and generated presentation documents."""

from src.services.amin_document_ops import extract_document_metadata, extract_document_state
from src.services.demo_seed_fixtures import KSA_DEMO_CLIENTS
from src.services.document_generator import create_document


def test_generated_pdf_has_previewable_metadata() -> None:
    pdf_bytes = create_document(
        doc_type="pdf",
        template="filing_receipt",
        title="North Riyadh EPC Payment Claim - Filing Receipt",
        context={
            "client_name": "Saudi Horizon Urban Development Company",
            "matter": "North Riyadh EPC Payment Claim",
            "court_name": "Riyadh Commercial Court",
            "counterparty": "Najd Build Contracting Company",
            "sections": [
                "Electronic filing confirmation issued for demo purposes only.",
                "Matter registered with bilingual exhibit references.",
            ],
        },
    )

    state = extract_document_state(pdf_bytes, "pdf")
    metadata = extract_document_metadata(pdf_bytes, "pdf")

    assert state["page_count"] >= 1
    assert metadata["page_count"] >= 1
    assert "North Riyadh EPC Payment Claim" in metadata["preview_text"]


def test_ksa_demo_seed_covers_case_mix_and_pdf_assets() -> None:
    client_types = {client["client_type"] for client in KSA_DEMO_CLIENTS}
    statuses: set[str] = set()
    practice_areas: set[str] = set()
    document_types: set[str] = set()
    case_count = 0

    for client in KSA_DEMO_CLIENTS:
        for case in client["cases"]:
            case_count += 1
            statuses.add(case["status"])
            practice_areas.add(case["practice_area"])
            for document in case["documents"]:
                document_types.add(document["doc_type"])

    assert len(KSA_DEMO_CLIENTS) >= 10
    assert case_count >= 20
    assert client_types == {"company", "individual", "organisation"}
    assert {"active", "pending", "on_hold", "closed"} <= statuses
    assert {"litigation", "corporate", "compliance", "employment", "enforcement"} <= practice_areas
    assert {"docx", "xlsx", "pptx", "pdf"} <= document_types
