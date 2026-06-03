"""Seed FHIR R4 field bindings — maps resource.field → ValueSet.

Run:
  uv run python -m app.terminology.seed_field_bindings
  # or
  just terminology-seed-bindings

Idempotent — safe to re-run. Skips bindings whose value set is not in the DB.
"""
import asyncio
import time

import asyncpg

# (resource_type, field_name, value_set_canonical_url, binding_strength, multiple_allowed)
FIELD_BINDINGS: list[tuple[str, str, str, str, bool]] = [
    # ── Patient ────────────────────────────────────────────────────────────────
    ("Patient", "gender", "http://hl7.org/fhir/ValueSet/administrative-gender", "required", False),
    ("Patient", "maritalStatus", "http://hl7.org/fhir/ValueSet/marital-status", "extensible", False),
    ("Patient", "communication.language", "http://hl7.org/fhir/ValueSet/languages", "preferred", False),
    ("Patient", "link.type", "http://hl7.org/fhir/ValueSet/link-type", "required", False),
    ("Patient", "telecom.system", "http://hl7.org/fhir/ValueSet/contact-point-system", "required", False),
    ("Patient", "telecom.use", "http://hl7.org/fhir/ValueSet/contact-point-use", "required", False),
    ("Patient", "contact.telecom.system", "http://hl7.org/fhir/ValueSet/contact-point-system", "required", False),
    ("Patient", "contact.telecom.use", "http://hl7.org/fhir/ValueSet/contact-point-use", "required", False),
    ("Patient", "contact.gender", "http://hl7.org/fhir/ValueSet/administrative-gender", "required", False),
    # ── Practitioner ───────────────────────────────────────────────────────────
    ("Practitioner", "gender", "http://hl7.org/fhir/ValueSet/administrative-gender", "required", False),
    ("Practitioner", "telecom.system", "http://hl7.org/fhir/ValueSet/contact-point-system", "required", False),
    ("Practitioner", "telecom.use", "http://hl7.org/fhir/ValueSet/contact-point-use", "required", False),
    # ── PractitionerRole ───────────────────────────────────────────────────────
    ("PractitionerRole", "code", "http://hl7.org/fhir/ValueSet/practitioner-role", "example", True),
    ("PractitionerRole", "specialty", "http://hl7.org/fhir/ValueSet/c80-practice-codes", "preferred", True),
    # ── Encounter ──────────────────────────────────────────────────────────────
    ("Encounter", "status", "http://hl7.org/fhir/ValueSet/encounter-status", "required", False),
    ("Encounter", "type", "http://hl7.org/fhir/ValueSet/encounter-type", "extensible", True),
    ("Encounter", "priority", "http://hl7.org/fhir/ValueSet/v3-ActPriority", "example", False),
    ("Encounter", "reasonCode", "http://hl7.org/fhir/ValueSet/encounter-reason", "preferred", True),
    ("Encounter", "dischargeDisposition", "http://hl7.org/fhir/ValueSet/encounter-discharge-disposition", "preferred", False),
    # ── Appointment ────────────────────────────────────────────────────────────
    ("Appointment", "status", "http://hl7.org/fhir/ValueSet/appointmentstatus", "required", False),
    ("Appointment", "serviceType", "http://hl7.org/fhir/ValueSet/service-type", "example", True),
    ("Appointment", "specialty", "http://hl7.org/fhir/ValueSet/c80-practice-codes", "preferred", True),
    ("Appointment", "cancelationReason", "http://hl7.org/fhir/ValueSet/appointment-cancellation-reason", "example", False),
    # ── Condition ──────────────────────────────────────────────────────────────
    ("Condition", "clinicalStatus", "http://hl7.org/fhir/ValueSet/condition-clinical", "required", False),
    ("Condition", "verificationStatus", "http://hl7.org/fhir/ValueSet/condition-ver-status", "required", False),
    ("Condition", "category", "http://hl7.org/fhir/ValueSet/condition-category", "extensible", True),
    ("Condition", "severity", "http://hl7.org/fhir/ValueSet/condition-severity", "preferred", False),
    ("Condition", "code", "http://hl7.org/fhir/ValueSet/condition-code", "example", False),
    ("Condition", "bodySite", "http://hl7.org/fhir/ValueSet/body-site", "example", True),
    ("Condition", "stage.summary", "http://hl7.org/fhir/ValueSet/condition-stage", "example", False),
    ("Condition", "stage.type", "http://hl7.org/fhir/ValueSet/condition-stage-type", "example", False),
    # ── Observation ────────────────────────────────────────────────────────────
    ("Observation", "status", "http://hl7.org/fhir/ValueSet/observation-status", "required", False),
    ("Observation", "category", "http://hl7.org/fhir/ValueSet/observation-category", "preferred", True),
    ("Observation", "code", "http://hl7.org/fhir/ValueSet/observation-codes", "example", False),
    ("Observation", "interpretation", "http://hl7.org/fhir/ValueSet/observation-interpretation", "extensible", True),
    ("Observation", "bodySite", "http://hl7.org/fhir/ValueSet/body-site", "example", False),
    ("Observation", "method", "http://hl7.org/fhir/ValueSet/observation-methods", "example", False),
    # ── MedicationRequest ──────────────────────────────────────────────────────
    ("MedicationRequest", "status", "http://hl7.org/fhir/ValueSet/medicationrequest-status", "required", False),
    ("MedicationRequest", "intent", "http://hl7.org/fhir/ValueSet/medicationrequest-intent", "required", False),
    ("MedicationRequest", "category", "http://hl7.org/fhir/ValueSet/medicationrequest-category", "example", True),
    ("MedicationRequest", "priority", "http://hl7.org/fhir/ValueSet/request-priority", "required", False),
    ("MedicationRequest", "statusReason", "http://hl7.org/fhir/ValueSet/medicationrequest-status-reason", "example", False),
    # ── Medication ─────────────────────────────────────────────────────────────
    ("Medication", "status", "http://hl7.org/fhir/ValueSet/medication-status", "required", False),
    ("Medication", "form", "http://hl7.org/fhir/ValueSet/medication-form-codes", "example", False),
    # ── Procedure ──────────────────────────────────────────────────────────────
    ("Procedure", "status", "http://hl7.org/fhir/ValueSet/event-status", "required", False),
    ("Procedure", "category", "http://hl7.org/fhir/ValueSet/procedure-category", "example", False),
    ("Procedure", "code", "http://hl7.org/fhir/ValueSet/procedure-code", "example", False),
    ("Procedure", "bodySite", "http://hl7.org/fhir/ValueSet/body-site", "example", True),
    ("Procedure", "outcome", "http://hl7.org/fhir/ValueSet/procedure-outcome", "example", False),
    # ── DiagnosticReport ───────────────────────────────────────────────────────
    ("DiagnosticReport", "status", "http://hl7.org/fhir/ValueSet/diagnostic-report-status", "required", False),
    ("DiagnosticReport", "category", "http://hl7.org/fhir/ValueSet/diagnostic-service-sections", "example", True),
    ("DiagnosticReport", "code", "http://hl7.org/fhir/ValueSet/report-codes", "preferred", False),
    # ── ServiceRequest ─────────────────────────────────────────────────────────
    ("ServiceRequest", "status", "http://hl7.org/fhir/ValueSet/request-status", "required", False),
    ("ServiceRequest", "intent", "http://hl7.org/fhir/ValueSet/request-intent", "required", False),
    ("ServiceRequest", "priority", "http://hl7.org/fhir/ValueSet/request-priority", "required", False),
    ("ServiceRequest", "category", "http://hl7.org/fhir/ValueSet/servicerequest-category", "example", True),
    ("ServiceRequest", "code", "http://hl7.org/fhir/ValueSet/procedure-code", "example", False),
    # ── DeviceRequest ──────────────────────────────────────────────────────────
    ("DeviceRequest", "status", "http://hl7.org/fhir/ValueSet/request-status", "required", False),
    ("DeviceRequest", "intent", "http://hl7.org/fhir/ValueSet/request-intent", "required", False),
    ("DeviceRequest", "priority", "http://hl7.org/fhir/ValueSet/request-priority", "required", False),
    # ── AllergyIntolerance ─────────────────────────────────────────────────────
    ("AllergyIntolerance", "clinicalStatus", "http://hl7.org/fhir/ValueSet/allergyintolerance-clinical", "required", False),
    ("AllergyIntolerance", "verificationStatus", "http://hl7.org/fhir/ValueSet/allergyintolerance-verification", "required", False),
    ("AllergyIntolerance", "type", "http://hl7.org/fhir/ValueSet/allergy-intolerance-type", "required", False),
    ("AllergyIntolerance", "category", "http://hl7.org/fhir/ValueSet/allergy-intolerance-category", "required", True),
    ("AllergyIntolerance", "criticality", "http://hl7.org/fhir/ValueSet/allergy-intolerance-criticality", "required", False),
    ("AllergyIntolerance", "code", "http://hl7.org/fhir/ValueSet/allergyintolerance-code", "example", False),
    ("AllergyIntolerance", "reaction.severity", "http://hl7.org/fhir/ValueSet/reaction-event-severity", "required", False),
    # ── Immunization ───────────────────────────────────────────────────────────
    ("Immunization", "status", "http://hl7.org/fhir/ValueSet/immunization-status", "required", False),
    ("Immunization", "statusReason", "http://hl7.org/fhir/ValueSet/immunization-status-reason", "example", False),
    ("Immunization", "vaccineCode", "http://hl7.org/fhir/ValueSet/vaccine-code", "example", False),
    ("Immunization", "site", "http://hl7.org/fhir/ValueSet/immunization-site", "example", False),
    ("Immunization", "route", "http://hl7.org/fhir/ValueSet/immunization-route", "example", False),
    ("Immunization", "reason", "http://hl7.org/fhir/ValueSet/immunization-reason", "example", True),
    # ── DocumentReference ──────────────────────────────────────────────────────
    ("DocumentReference", "status", "http://hl7.org/fhir/ValueSet/document-reference-status", "required", False),
    ("DocumentReference", "docStatus", "http://hl7.org/fhir/ValueSet/composition-status", "required", False),
    ("DocumentReference", "type", "http://hl7.org/fhir/ValueSet/c80-doc-typecodes", "preferred", False),
    ("DocumentReference", "category", "http://hl7.org/fhir/ValueSet/document-classcodes", "example", True),
    # ── Coverage ───────────────────────────────────────────────────────────────
    ("Coverage", "status", "http://hl7.org/fhir/ValueSet/fm-status", "required", False),
    ("Coverage", "type", "http://hl7.org/fhir/ValueSet/coverage-type", "preferred", False),
    ("Coverage", "relationship", "http://hl7.org/fhir/ValueSet/subscriber-relationship", "extensible", False),
    # ── Claim ──────────────────────────────────────────────────────────────────
    ("Claim", "status", "http://hl7.org/fhir/ValueSet/fm-status", "required", False),
    ("Claim", "type", "http://hl7.org/fhir/ValueSet/claim-type", "extensible", False),
    ("Claim", "use", "http://hl7.org/fhir/ValueSet/claim-use", "required", False),
    ("Claim", "priority", "http://hl7.org/fhir/ValueSet/process-priority", "required", False),
    # ── ClaimResponse ──────────────────────────────────────────────────────────
    ("ClaimResponse", "status", "http://hl7.org/fhir/ValueSet/fm-status", "required", False),
    ("ClaimResponse", "use", "http://hl7.org/fhir/ValueSet/claim-use", "required", False),
    ("ClaimResponse", "outcome", "http://hl7.org/fhir/ValueSet/remittance-outcome", "required", False),
    # ── Invoice ────────────────────────────────────────────────────────────────
    ("Invoice", "status", "http://hl7.org/fhir/ValueSet/invoice-status", "required", False),
    ("Invoice", "type", "http://hl7.org/fhir/ValueSet/invoice-type", "example", False),
    # ── CarePlan ───────────────────────────────────────────────────────────────
    ("CarePlan", "status", "http://hl7.org/fhir/ValueSet/request-status", "required", False),
    ("CarePlan", "intent", "http://hl7.org/fhir/ValueSet/care-plan-intent", "required", False),
    ("CarePlan", "category", "http://hl7.org/fhir/ValueSet/care-plan-category", "example", True),
    ("CarePlan", "activity.detail.status", "http://hl7.org/fhir/ValueSet/care-plan-activity-status", "required", False),
    # ── Task ───────────────────────────────────────────────────────────────────
    ("Task", "status", "http://hl7.org/fhir/ValueSet/task-status", "required", False),
    ("Task", "intent", "http://hl7.org/fhir/ValueSet/task-intent", "required", False),
    ("Task", "priority", "http://hl7.org/fhir/ValueSet/request-priority", "required", False),
    ("Task", "code", "http://hl7.org/fhir/ValueSet/task-code", "example", False),
    # ── EpisodeOfCare ──────────────────────────────────────────────────────────
    ("EpisodeOfCare", "status", "http://hl7.org/fhir/ValueSet/episode-of-care-status", "required", False),
    ("EpisodeOfCare", "type", "http://hl7.org/fhir/ValueSet/episodeofcare-type", "example", True),
    # ── AuditEvent ─────────────────────────────────────────────────────────────
    ("AuditEvent", "action", "http://hl7.org/fhir/ValueSet/audit-event-action", "required", False),
    ("AuditEvent", "outcome", "http://hl7.org/fhir/ValueSet/audit-event-outcome", "required", False),
    ("AuditEvent", "type", "http://hl7.org/fhir/ValueSet/audit-event-type", "extensible", False),
    # ── Schedule ───────────────────────────────────────────────────────────────
    ("Schedule", "serviceType", "http://hl7.org/fhir/ValueSet/service-type", "example", True),
    ("Schedule", "specialty", "http://hl7.org/fhir/ValueSet/c80-practice-codes", "preferred", True),
    # ── Slot ───────────────────────────────────────────────────────────────────
    ("Slot", "status", "http://hl7.org/fhir/ValueSet/slotstatus", "required", False),
    ("Slot", "serviceType", "http://hl7.org/fhir/ValueSet/service-type", "example", True),
    ("Slot", "specialty", "http://hl7.org/fhir/ValueSet/c80-practice-codes", "preferred", True),
    # ── Location ───────────────────────────────────────────────────────────────
    ("Location", "status", "http://hl7.org/fhir/ValueSet/location-status", "required", False),
    ("Location", "mode", "http://hl7.org/fhir/ValueSet/location-mode", "required", False),
    ("Location", "type", "http://hl7.org/fhir/ValueSet/v3-ServiceDeliveryLocationRoleType", "extensible", True),
    ("Location", "physicalType", "http://hl7.org/fhir/ValueSet/location-physical-type", "example", False),
    ("Location", "telecom.system", "http://hl7.org/fhir/ValueSet/contact-point-system", "required", False),
    ("Location", "telecom.use", "http://hl7.org/fhir/ValueSet/contact-point-use", "required", False),
    # ── Organization ───────────────────────────────────────────────────────────
    ("Organization", "type", "http://hl7.org/fhir/ValueSet/organization-type", "example", True),
    ("Organization", "telecom.system", "http://hl7.org/fhir/ValueSet/contact-point-system", "required", False),
    ("Organization", "telecom.use", "http://hl7.org/fhir/ValueSet/contact-point-use", "required", False),
    # ── Provenance ─────────────────────────────────────────────────────────────
    ("Provenance", "reason", "http://terminology.hl7.org/ValueSet/v3-PurposeOfUse", "extensible", True),
    ("Provenance", "activity", "http://hl7.org/fhir/ValueSet/provenance-activity-type", "extensible", False),
    ("Provenance", "agent.type", "http://hl7.org/fhir/ValueSet/provenance-agent-type", "extensible", False),
    ("Provenance", "agent.role", "http://hl7.org/fhir/ValueSet/security-role-type", "example", True),
    # ── Specimen ───────────────────────────────────────────────────────────────
    ("Specimen", "status", "http://hl7.org/fhir/ValueSet/specimen-status", "required", False),
    ("Specimen", "type", "http://hl7.org/fhir/ValueSet/v2-0487", "example", False),
    ("Specimen", "collection.method", "http://hl7.org/fhir/ValueSet/specimen-collection-method", "example", False),
    ("Specimen", "collection.bodySite", "http://hl7.org/fhir/ValueSet/body-site", "example", False),
    # ── RelatedPerson ──────────────────────────────────────────────────────────
    ("RelatedPerson", "relationship", "http://hl7.org/fhir/ValueSet/relatedperson-relationshiptype", "preferred", True),
    ("RelatedPerson", "gender", "http://hl7.org/fhir/ValueSet/administrative-gender", "required", False),
    ("RelatedPerson", "telecom.system", "http://hl7.org/fhir/ValueSet/contact-point-system", "required", False),
    ("RelatedPerson", "telecom.use", "http://hl7.org/fhir/ValueSet/contact-point-use", "required", False),
    # ── HealthcareService ──────────────────────────────────────────────────────
    ("HealthcareService", "category", "http://hl7.org/fhir/ValueSet/service-category", "example", True),
    ("HealthcareService", "type", "http://hl7.org/fhir/ValueSet/service-type", "example", True),
    ("HealthcareService", "specialty", "http://hl7.org/fhir/ValueSet/c80-practice-codes", "preferred", True),
]


async def seed(db_url: str) -> None:
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db_url)
    t0 = time.monotonic()

    try:
        inserted = 0
        skipped_no_vs = 0

        for resource_type, field_name, vs_url, binding_strength, multiple_allowed in FIELD_BINDINGS:
            vs_id = await conn.fetchval(
                "SELECT id FROM terminology_value_set WHERE canonical_url = $1", vs_url
            )
            if vs_id is None:
                skipped_no_vs += 1
                continue

            await conn.execute(
                """
                INSERT INTO terminology_field_binding
                    (resource_type, field_name, value_set_id, binding_strength, multiple_allowed)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (resource_type, field_name) DO UPDATE SET
                    value_set_id      = EXCLUDED.value_set_id,
                    binding_strength  = EXCLUDED.binding_strength,
                    multiple_allowed  = EXCLUDED.multiple_allowed,
                    active            = TRUE
                """,
                resource_type, field_name, vs_id, binding_strength, multiple_allowed,
            )
            inserted += 1

        print(f"[SEED] Field bindings done — {inserted} upserted, {skipped_no_vs} skipped (value set not in DB)")
        print(f"[SEED] Elapsed: {time.monotonic() - t0:.1f}s")
    finally:
        await conn.close()


def main() -> None:
    from app.core.config import settings
    asyncio.run(seed(settings.TERMINOLOGY_DATABASE_URL))


if __name__ == "__main__":
    main()
