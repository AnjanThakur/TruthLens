# Nana Patekar investigation repair — 12 October 2026

Base: feature/scam-alert-intelligence, b5d42d9. The earlier uncommitted factual
question fix was preserved. No private configuration, database or WhatsApp state
was modified. No Gemini, Tavily or Twilio requests were made by this investigation.

## Confirmed causes and changes

1. **Classification blocked assessment.** All six owner-supplied publishers were
   other. The engine intentionally avoids spending an assessment call when no
   complete reviewed fetched page exists. Six ledger entries therefore did not
   mean six assessed sources. TOI editorial news and scoped NDTV article paths
   now have secondary eligibility after the documented publisher review. NBC,
   Wikipedia, YouTube and the supplied NDTV video remain other. Reuters/AP were
   already recognized; their absence was discovery/selection, not classification.
2. **Discovery could omit wires and bias the cross-check toward a hoax.** The
   second model query substituted for independent discovery, and a two-query
   budget omitted that stage entirely. Unknown-authority claims now use quoted
   full entities and a neutral reporting query, with Reuters/AP/BBC preferences
   on the first existing search. Relevant-authority claims retain their official
   first search and use those preferences on corroboration. The contradiction
   search stays broad. Tavily's documented `include_domains_mode=prefer` retains
   the rest of the web; no query/attempt ceilings were increased. Cache keys
   include preferences, and the existing bounded acceptance-provider overrides
   remain compatible. A Reuters October 8 article URL was not independently
   located in this investigation; no article URL was invented.
3. **Ranking and excerpt selection were topic-only.** Publisher category and
   Tavily score outranked full-name relevance. Full-entity matching now precedes
   those scores during bounded fetch selection; contiguous excerpt windows also
   favor the actual entity. Complete pages precede failed/snippet pages at final
   selection. Distinct complete reviewed publishers are retained before repeated
   URLs from one publisher. Explicit multiword mortality subjects absent from a
   fetched excerpt receive an entity-mismatch marker and cannot establish a
   verdict or a conflict. Other topics/abbreviations retain semantic assessment.
4. **Retrieval diagnostics discarded the cause.** HTTP, connection and protocol
   failures all became url_fetch_error, and article-specific categories were lost
   at the ledger boundary. Stable error codes remain compatible, while fixed
   sanitized categories and numeric HTTP statuses now enter source diagnostics
   and authority_basis. Neither logs nor errors expose headers, credentials,
   response bodies, prompts or URL query strings. Access controls and SSRF
   restrictions remain intact; there are no new automatic page retries.
5. **Weak content could look complete and UI notices repeated.** The 145-character
   YouTube extraction was generic page text rather than a transcript. Short
   generic non-article extractions now fail completeness; brief semantic notices
   remain supported. The ledger respects content_complete=false. Actual fetched
   excerpts, IDs, provenance and page dates reach assessment, with explicit
   completeness, subject-match and duplicate-passage flags. The UI distinguishes
   assessed/unassessed complete pages, unreviewed pages, incomplete pages,
   namesakes, snippets and failed retrieval. It displays sanitized failure reasons
   and groups repeated notices while preserving the raw report warning list.

## Actual read-only source checks

These are fresh downloads with keys explicitly empty, not a reconstruction of
the earlier live verification. The earlier clipboard output lacks the four
specific warning codes; the exact historical failures cannot be established.

| Supplied/discovered source | Actual result |
| --- | --- |
| Wikipedia Nana Patekar | PASS extraction: 19,904 characters; publisher remains unreviewed. |
| Wikipedia Nana manga | PASS extraction: 35,183 characters; full person name absent; irrelevant namesake. |
| NBC obituary | PASS extraction: 1,642 characters; complete body; publisher remains unreviewed. |
| NDTV video | FAIL download: HTTP 403, access_denied. No bypass or snippet verdict. |
| TOI news liveblog | PASS extraction: 19,038 characters; complete body; full name present. Now within reviewed editorial news scope. |
| YouTube watch page | PASS download/extraction: 145 characters of generic text; no full name. Baseline incorrectly called it complete; the repair treats generic short text as incomplete. Video transcription is NOT IMPLEMENTED. |
| AP article a1f8495501327d5c7949173c7a14b55c | FAIL download: HTTP 403, access_denied. AP's indexed article was found through read-only web search, but it is not accepted as fetched decisive evidence. |

The machine-readable source checks retain the real public URLs and extraction
counts without storing article bodies. No claim verdict follows from these
checks, titles, publication dates, or web-search snippets.

## Acceptance

- PASS baseline, before edits: 80 targeted backend tests; all 59 frontend tests.
- PASS offline regression: fetched corroboration, unavailable pages, misleading
  death headlines with denial bodies, namesakes, conflicting reports, genuinely
  unconfirmed reporting, HTTP/transport categories, cache isolation and budgets.
- Final full suite/static/browser results are recorded in validation-report.md.
- SKIPPED: new provider-backed verification of the real claim; no approved budget.
- BLOCKED: AP/NDTV access-denied downloads from this laptop. A future run can use
  independently retrieved complete reporting, without bypassing those sites.
- NOT IMPLEMENTED: JavaScript execution and remote video transcription; no
  publisher access bypass or automatic paid fallback was added.

To inspect a specific public source without credits, run from backend:
`python -m scripts.diagnose_source_pages PUBLIC_ARTICLE_URL`.
It loads no private .env, never searches, never calls a model, and prints only
safe extraction/status metadata. A real end-to-end factual result still requires
an approved provider budget; this report does not claim that a live rerun passed.
