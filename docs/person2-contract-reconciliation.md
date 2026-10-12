# Person 2 contract reconciliation W0

Authority: the original Word plan defines product requirements; the owner's approved W0–W6 roadmap and WhatsApp handoff assign the isolated connector to Person 2. Person 1's `docs/backend-api-contract.md`, exported `docs/backend-openapi.json` and `backend/app/schemas/models.py` define actual HTTP field names. The old provisional `docs/api-contract.md` is historical and superseded for wire schemas.

No Person 1 code or public schemas were changed. Both channels call the same `/api/extract`, `/api/extract/url`, `/api/verify` and `/api/explain` service.

| Provisional website assumption | Actual backend and resolution |
|---|---|
| `detected_language`, `source_metadata` in verify request | Removed from transport; send `input_language`, `response_language`, `audience`, `jurisdiction`, `input_type`, `text` |
| `metadata` extraction property | Use `extraction_details`; retain page/chunk metadata locally, not as unknown verify request fields |
| Context fields as strings | Preserve structured temporal/original context; render notes |
| Only completed transport status | Accept `completed`, `partial`, `no_checkable_claims`; show partial warning prominently |
| `/explain` returns a string projection | Submit `{result,language,audience}` and retain full validated result; reject changes outside wording/presentation fields |
| `standard/easy` backend audiences | Explicit display mapping to `adult/senior`; backend also supports child/teen |
| General media MIME list | PNG/JPEG, WAV/MP3/OGG, PDF; remove formats the backend does not accept |
| Generic capability `verify` | Honor actual `claim_verification`; health does not prove provider uptime |
| 30,000-character UI input | Bound to current runtime default 24,000; backend health exposes actual deployment limits |

The complete backend result—including evidence IDs/provenance, immutable grounded reasoning, risk/context and language settings—is preserved by website validation. Re-explanation compares every immutable field before display. History signs/persists the complete canonical snapshot. Existing synthetic JSON is unchanged; conversion to the new shape happens exclusively inside the fixture module with its fictional labels retained. Live responses never use that conversion.

PDF `text_is_preview` requires the website user to choose an actual returned page chunk before checking; the result covers selected text only. The WhatsApp adapter asks for smaller files/website review rather than silently checking a preview or unexpectedly consuming many provider calls. Unreadable or truncated content is not full-document acceptance.

The installed adapter carries the exact backend OpenAPI as package data. A regression compares it to the repository export and validates actual transport fields/responses using JSON Schema. Website regressions consume an explicitly offline full-result fixture matching that schema. Contract drift must fail tests and trigger review. No field/verdict changes are negotiated silently.

Coordination still required: Person 1 review of this client mapping, real origin/runtime readiness, provider-key rotation, approved live budgets, internal deployment authentication and actual multimodal acceptance. No messages have been sent to Person 1 on the owner's behalf.
