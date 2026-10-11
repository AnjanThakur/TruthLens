# Optional Meta and WhatsApp setup requirements

Prepared during G0. Full integration is G5 and must not delay the website. P2 owns platform setup; P1 owns signed webhook code, media processing, deduplication and replies. No Meta assets have been created and no credentials are present.

## Requirements checklist

1. An authorized Meta developer account and appropriate app/business permissions. Confirm account eligibility in the current Meta dashboard; do not assume business or production approval.
2. A Meta app with WhatsApp Business Platform access, a test WABA and test phone number where supplied, and an explicitly permitted test recipient.
3. Record WABA ID and phone-number ID separately from the phone number. Record the selected supported Graph API version instead of hardcoding an assumed version.
4. Obtain a properly scoped token through the approved Meta flow. Check `whatsapp_business_messaging` and `whatsapp_business_management` for the operations being used; business-management permissions depend on setup. Confirm exact current requirements in Meta documentation/dashboard.
5. P1 must deploy an HTTPS `GET/POST /webhook/whatsapp`. Agree callback URL and verification token; P1 implements challenge validation and signature checking with the app secret.
6. Configure the app/WABA webhook subscriptions and `messages` events as applicable. P1 must test inbound text, media IDs/downloads, duplicate events and signed requests, then outgoing cited replies.
7. Keep tokens, app secret and verification token in P1's secret manager. Never put these values in Git, browser variables, QR codes or client code.
8. After a real test passes, prepare a demo link/QR containing only the permitted phone/link and optional non-sensitive starter text. The website remains an independent demo.

## P1 handoff values

`META_WABA_ID`, `META_PHONE_NUMBER_ID`, `META_ACCESS_TOKEN`, `META_APP_SECRET`, `META_VERIFY_TOKEN`, confirmed Graph API version, public webhook callback URL, test recipient and subscriptions. Values must be transferred through an approved secret channel, not this document.

## Production gate

Review current eligibility, app review, permission requirements, messaging windows/templates, consent, quotas/pricing and the policies applicable to this use case before enabling public use. A successful dashboard test is not proof of production eligibility. The bot can process voluntarily submitted content; it cannot inspect private chats or forwarding recipient graphs.

Official references: [Cloud API getting started](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started), [Cloud API webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks), [Meta's official API collection](https://www.postman.com/meta/whatsapp-business-platform/collection/wlk6lh4/whatsapp-cloud-api). Checked 2026-10-11: direct Meta documentation fetch was rate-limited/unavailable; account-specific/current details still require dashboard verification. No account setup or messaging tests have been performed.
