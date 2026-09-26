# Rishi Vāṇijya — KRISHNA Independent Sales & Marketing Head

Date: 26 September 2026

## Mission

Rishi Vāṇijya is KRISHNA's independent Sales & Marketing Head. He owns the path from an approved product/service opportunity to qualified customer, truthful solution, proposal, negotiation, exact payment request, verified received revenue and ongoing customer relationship.

Responsibility boundaries:

- **MANIBHADRA** is the commerce/product source of truth and CRM.
- **Rishi Vāṇijya** owns marketing, lead generation, sales development, discovery, solution selling, proposals, negotiation, closing and revenue relationships.
- **GARUDA / VANIK-NETRA** provide public market research and market intelligence; Vāṇijya does not create duplicate research agents.
- **NARAD** owns authenticated external Gmail/WhatsApp/provider execution and durable inbox/outbox workflows.
- **NARADA Legal** owns legal/compliance review.
- **KRISHNA bounded Shishya runtime** creates temporary workers for Vāṇijya requirements and destroys their temporary identities after handover.
- **MRITYUNJAY** is repair-only and is activated by health/action failure, not normal sales work.
- **Zero Spend** remains hard: receive money; do not send money.

## Permanent sales agents

1. Lead Researcher
2. SDR / Calling Shishya
3. Lead Qualifier
4. Account Executive
5. Solution Consultant
6. Proposal & Pricing Specialist
7. Negotiator / Deal Closer
8. Customer Relationship Manager

The eight role identities are permanent. Extra runtime workers are bounded Shishyas created only when required.

## Autonomous product loop

Each Vāṇijya autopilot tick:

1. synchronizes approved MANIBHADRA product records;
2. asks MANIBHADRA which new or improved zero-spend product/service should be marketed next;
3. inspects real CRM leads, deals and follow-up tasks;
4. builds a prioritized work queue for the eight sales agents;
5. performs no external send and no spend in the planning tick.

If no product is ready, the next required action is a MANIBHADRA product request. Vāṇijya never fabricates product capability, price, supplier relationship, commission, fulfilment, customer evidence or marketplace access.

## Marketing rules

Zero-spend routes include owned website/SEO/content, organic social, inbound enquiries, permissioned email, permissioned/inbound WhatsApp, relevant lawful public B2B research, and program-permitted referrals/affiliates.

Paid advertising, paid leads, purchased databases, paid boosts and paid acquisition remain disabled.

## Contact and reply rules

Outreach is fail-closed unless the provider is connected and the recipient has a legitimate public-business, inbound, existing-customer or consent basis. Opt-out, unsubscribe and do-not-contact signals stop promotional follow-up. Promotional WhatsApp is stricter: a public number alone does not qualify for automatic promotion.

Inbound replies route to the correct role: pricing -> Proposal & Pricing; requirement/question -> Solution Consultant; positive/discovery -> Account Executive; purchase/negotiation -> Deal Closer; opt-out -> stop/suppress.

## External execution

Vāṇijya prepares the sales communication. NARAD creates and executes the provider workflow. A Gmail/WhatsApp send must use a connected credential and the existing NARAD/Sudarshan verification/promotion gates. Gmail replies can preserve Gmail thread IDs and reply headers.

No credential is committed to GitHub.

## Shared CRM

Vāṇijya uses MANIBHADRA CRM rather than creating a second customer database. Sales state additionally records Vāṇijya campaigns, conversations, quotes, payment requests, temporary workers, HR requests, product assignments and sales activity in `.krishna_state/vanijya-sales.json` with backup recovery.

## Exact UPI request and local QR

After agreement, Vāṇijya can create an exact INR UPI payment URI containing payee VPA, payee name, invoice/reference, note and exact amount. The same URI is the payment link and QR payload.

`scripts/INSTALL_KRISHNA_QR.ps1` optionally installs the free local `qrcode==8.2` package only into KRISHNA's identified virtual environment. `vanijya.payment.qr` can then render the payload locally as SVG/data URI without a paid QR API.

QR/link creation is never payment proof.

## Payment verification

A payment remains PENDING until trusted authenticated server-side evidence arrives from an allowed class such as bank API, bank statement API, PSP API, UPI PSP status API, UPI acquirer webhook or payment-gateway webhook.

Vāṇijya verifies trusted source class, signature/bank verification, successful terminal state, exact invoice/reference, exact amount and transaction/UTR/RRN identity. Customer claims, screenshots, images, browser redirects, client callbacks and manual text never mark a deal paid.

A linked MANIBHADRA deal moves to `won` only after verified payment.

## Future commerce expansion registry

MANIBHADRA now has explicit zero-spend readiness contracts for ONDC, eBay, Etsy, Google Merchant free listings, Google Search Console, Pinterest organic shopping, organic social, supplier-funded dropshipping, B2B RFQ matching, global importer/distributor discovery, AI-commerce/UCP readiness and self-hosted Medusa.

These are fail-closed contracts, not fabricated connections. Paid or unverified routes stay disabled.

## Main UI rule

Vāṇijya appears as a Sales & Marketing Head panel **inside MANIBHADRA**. He does not add another main-menu entry. Main menu remains KRISHNA / Sudarshan / MANIBHADRA / Plugins.

## Core actions

- `vanijya.status`, `vanijya.team`, `vanijya.dashboard`, `vanijya.health`, `vanijya.health.verify`
- `vanijya.manibhadra.request`, `vanijya.products.sync`, `vanijya.product.scout`
- `vanijya.sales_cycle`, `vanijya.autopilot.tick`, `vanijya.campaign.create`, `vanijya.marketing.plan`
- `vanijya.hr.request`, `vanijya.hr.create`, `vanijya.hr.retire`, `vanijya.hr.plan`, `vanijya.hr.execute`
- `vanijya.outreach.decide`, `vanijya.outreach.plan`, `vanijya.outbound.plan`, `vanijya.narad.workflow`
- `vanijya.reply.ingest`, `vanijya.inbound.reply`, `vanijya.lead.qualify`
- `vanijya.crm.dashboard`, `vanijya.crm.upsert_lead`, `vanijya.crm.upsert_deal`
- `vanijya.quote.create`
- `vanijya.payment.upi_request`, `vanijya.payment.qr`, `vanijya.payment.verify`
- `vanijya.pipeline.next`, `vanijya.automation.blueprint`
- `manibhadra.expansion.status`, `manibhadra.expansion.plan`

## Activation truth

The code supports the autonomous sales lifecycle and provider handoffs. Live autonomous Gmail/WhatsApp messaging and automatic payment reconciliation remain inactive until the corresponding owner-authorized real accounts/credentials are connected and verified. No paid fallback and no outgoing-payment authority has been added.
