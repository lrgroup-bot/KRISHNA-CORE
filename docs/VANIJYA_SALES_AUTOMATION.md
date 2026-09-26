# Rishi Vanijya — KRISHNA Independent Sales & Marketing Head

Date: 26 September 2026

## Mission

Rishi Vanijya is an independent KRISHNA operating specialist responsible for taking an approved product/service from market opportunity to received revenue.

He reports to KRISHNA. He is not a MANIBHADRA sub-agent.

Responsibility split:

- **MANIBHADRA** — product/commerce source of truth, product opportunity, suppliers/marketplaces and commerce facts.
- **Rishi Vanijya** — marketing, leads, qualification, customer discovery, solution selling, proposal, negotiation, closing and revenue relationship.
- **NARAD** — authenticated external connector/workflow execution such as Gmail and WhatsApp.
- **NARADA Legal** — legal/compliance gate for outreach, jurisdiction, contracts, privacy and commercial-communication rules.
- **KRISHNA HR / bounded Shishya runtime** — creates temporary workers when Vanijya requires more manpower.
- **Zero Spend Policy** — incoming revenue allowed; outgoing spend remains hard-blocked.

## Permanent Vanijya team

1. Lead Researcher
2. SDR / Calling Shishya
3. Lead Qualifier
4. Account Executive
5. Solution Consultant
6. Proposal & Pricing Specialist
7. Negotiator / Deal Closer
8. Customer Relationship Manager

The role definitions are permanent. Runtime workers are created only for bounded requirements and retire after handover under the existing Shishya lifecycle.

## Market-to-revenue flow

MANIBHADRA opportunity
-> VANIJYA zero-spend marketing plan
-> Lead Researcher
-> SDR / Calling Shishya
-> Lead Qualifier
-> Account Executive
-> Solution Consultant
-> Proposal & Pricing Specialist
-> Negotiator / Deal Closer
-> exact customer payment request
-> trusted payment verification
-> Closed Won
-> Customer Relationship Manager
-> repeat sale / cross-sell / upsell / referral

## Mandatory MANIBHADRA check

Every new sales campaign starts with a request to MANIBHADRA for a current zero-spend product/service opportunity.

Vanijya must not fabricate a product, supplier relationship, product functionality, price/commission, fulfilment capability, marketplace/API access, customer evidence, or investment return.

## Marketing model

Default marketing is zero-spend:

- owned website;
- SEO/content;
- organic social;
- inbound enquiries;
- permissioned email;
- permissioned/inbound WhatsApp;
- relevant public B2B account research subject to current legal/channel rules;
- referral/affiliate routes allowed by the specific program.

Paid ads, paid leads and purchased databases remain blocked under zero-spend mode.

## Lead and suppression gate

A lead is not sales-ready simply because a phone number or email exists. Qualification evaluates the known requirement, intent, reachable channel, inbound/consent/authorized contact basis, and opt-out/suppression/do-not-contact state.

Opt-out is terminal for promotional follow-up until a valid new permission basis exists.

## Gmail / WhatsApp

Vanijya does not duplicate connector code. He creates the sales communication plan and NARAD owns external execution.

Automatic sales messaging may run only inside an owner-authorized verified Stable workflow when the account is connected, recipient/channel contact permission is valid, suppression/opt-out rules are enforced, NARADA Legal accepts the current jurisdictional use, provider policy is satisfied, and the workflow has passed KRISHNA governance.

Current VANIJYA explicitly prevents a public business number alone from qualifying for automatic promotional WhatsApp messaging.

## Reply handling

Inbound replies are classified into bounded next steps:

- opt-out -> suppress and stop;
- pricing/quotation -> Proposal & Pricing Specialist;
- product/details/demo -> Solution Consultant;
- purchase/proceed/payment intent -> Negotiator / Deal Closer;
- otherwise -> Account Executive.

Provider inbox/webhook ingestion remains NARAD's responsibility.

## CRM

Vanijya shares MANIBHADRA CRM rather than creating a second customer database. VANIJYA can read the sales dashboard and add/update leads and deals.

## Exact UPI payment request

After the customer agrees to the order, Vanijya can generate a receive-only UPI URI containing payee VPA, payee name, exact amount, INR, order/transaction reference, and transaction note.

The URI is both a payment link and the QR payload.

### Local QR image

scripts/INSTALL_KRISHNA_QR.ps1 installs the free BSD-licensed qrcode==8.2 package only into an identified KRISHNA/E-drive virtual environment and keeps pip cache under the repository.

vanijya.payment.qr renders the payment payload locally to SVG/data-URI form. No paid QR API is used.

## Payment verification

QR generation is not payment confirmation.

Never accept screenshots, customer statements, receipt images, browser redirects, client callbacks, QR creation, or link creation as sufficient payment proof.

Payment can become verified only from a trusted server-side class such as bank API, bank statement API, PSP API, UPI PSP status API, UPI acquirer webhook, or payment gateway webhook.

Before Closed Won, Vanijya checks successful terminal state, expected amount, expected order/reference, and transaction ID / UTR / RRN.

Actual automatic reconciliation remains inactive until an owner-authorized bank/PSP/gateway connection exists.

## Open-source reference patterns studied

### Twenty
Programmable CRM objects, views, workflows and agents. No Twenty source code was copied into KRISHNA.

### EspoCRM
Lead/opportunity pipeline organization. MANIBHADRA CRM remains canonical.

### Mautic
Self-hosted marketing automation, segmentation and privacy-oriented campaign design. No Mautic code was copied.

### Chatwoot
One conversation layer across email/WhatsApp/social channels and agent routing. KRISHNA keeps NARAD instead of installing a duplicate stack.

### n8n
Event-triggered workflows, integrations, approvals and observability. VANIJYA plugs into NARAD instead of creating another automation engine.

### python-qrcode
Optional free local QR renderer. Version pinned by the install script: 8.2.

## KRISHNA actions

vanijya.status
vanijya.team
vanijya.hr.plan
vanijya.hr.execute
vanijya.product.scout
vanijya.marketing.plan
vanijya.lead.qualify
vanijya.outreach.plan
vanijya.inbound.reply
vanijya.crm.dashboard
vanijya.crm.upsert_lead
vanijya.crm.upsert_deal
vanijya.payment.request
vanijya.payment.qr
vanijya.payment.verify
vanijya.pipeline.next
vanijya.automation.blueprint

## Activation truth

The KRISHNA code can model and orchestrate the sales lifecycle, create bounded sales workers, share the existing CRM, construct exact payment requests, render a local QR when the free renderer is installed, and validate trusted payment evidence.

Live autonomous Gmail/WhatsApp sending, inbox event ingestion and live payment reconciliation depend on corresponding owner-authorized real account/provider connections. Those connections are not fabricated and credentials are never committed to GitHub.

No paid service has been enabled and no outgoing-payment authority has been added.
