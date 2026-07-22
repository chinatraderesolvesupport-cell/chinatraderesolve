import asyncio
from app.db import init_db, create_case
from app.schemas import ApplicationCreate
from app.triage import rules_triage
import secrets
from datetime import datetime, timezone

init_db()
payload = ApplicationCreate(
    full_name="Demo Buyer", email="demo@example.com", country="Serbia", preferred_language="English",
    purchasing_channel="Alibaba", amount_in_dispute="EUR 4,500", main_problem="Wrong material or specification",
    supplier_name="Example Supplier Ltd.", order_number="DEMO-001", order_value="EUR 12,000",
    requested_result="Partial refund", description="The written order specifies one material, but supplier messages and delivered product photographs indicate a different material. We have the invoice, order record, chat messages and photographs.",
    company_website="", free_access_terms=True, sharing_authority=True, ai_consent=True, no_guarantee=True,
)
triage = rules_triage(payload).model_dump()
ref = f"CTR-{datetime.now(timezone.utc).year}-{secrets.token_hex(3).upper()}"
case = create_case(payload.model_dump(), triage, ref, secrets.token_urlsafe(24))
print(case["case_reference"])
