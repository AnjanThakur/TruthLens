# Publisher classification review — 12 October 2026

Classification is eligibility for excerpt assessment, not a guarantee of truth,
independence, relevance, or completeness. Exact fetched quotations, claim scope,
conflicts, dates and provenance still pass the existing verdict guards.

| Publisher | Review evidence | Decision and limits |
| --- | --- | --- |
| Reuters | [Journalistic standards](https://reutersagency.com/about/standards-values/) explicitly require accuracy, transparent corrections, attribution and freedom from bias. | Retain existing secondary classification. A search headline is never proof. |
| AP | Existing reviewed wire registry; no classification expansion in this change. | Retain existing secondary classification. The discovered article returned HTTP 403 to the application fetcher, so its search excerpt cannot establish a verdict. |
| Times of India | Its [verification and corrections policy](https://timesofindia.indiatimes.com/about-us/articleshow/67527602.cms) describes cross-checks, original-source investigation and correction notes. Its published [DNPA code](https://timesofindia.indiatimes.com/india/dnpa-code-of-ethics-for-digital-news-websites/articleshow/78840462.cms) states accuracy, pre-publication verification, updates, corrections and grievance handling. | Add secondary eligibility for `/india/` and `/news/` editorial paths, including the supplied news liveblog. Exclude `/blogs/` and other paths. Policies are self-declared; actual body attribution and contradictory reporting remain necessary checks. A liveblog may contain updates, not independent reporting origins. |
| NDTV | Its [2024–25 annual report](https://www.ndtv.com/convergence/ndtv/corporatepage/images/NDTVAnnualReport2024-25.pdf) states editorial independence, accuracy/fairness and adherence to NBDA standards and complaint handling. | Add secondary eligibility for article paths: india-news, world-news, entertainment, cities, business, science and health. Exclude video/UGC/other paths. The supplied video page remains other and currently returns HTTP 403. Corporate policy claims are not independent validation of an individual story. |
| NBC News | The supplied obituary produced a readable 1,642-character body, but its editorial-policy review could not be completed through the available read-only browsing surface. | Remains other. A professional brand or a readable page alone does not justify registry expansion. When an eligible complete source enables assessment, its real fetched excerpt is also supplied, with unreviewed classification preserved. |
| Wikipedia / YouTube | Encyclopedia or user-upload platform; no publisher-quality review establishing editorial eligibility for this claim. | Remain other. The manga page is a namesake; video-player text is not a video transcript. |

New eligibility uses hostname boundaries and scoped paths; lookalike domains
remain other. Syndicated passages are marked and their duplication flag reaches
the evidence assessor. Distinct publisher names help selection diversity but do
not prove independent reporting. No fetched-source or citation guard was relaxed.
