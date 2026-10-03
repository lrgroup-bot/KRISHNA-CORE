# KRISHNA Secure Communication Gateway

Status: implemented secure-mail intelligence foundation on `feature/secure-communication-gateway`.

## Security contract

Incoming email is always treated as untrusted external content. Message text never has instruction authority over KRISHNA, Sudarshan, the Shared Action Bus, provider credentials, files, memory, or other tools.

Before email content is exposed to an AI model, KRISHNA:

1. Redacts secret-like material including password/PIN fields, API/client secrets, bearer tokens, OpenAI-style keys, AWS access keys, private keys and payment-card-like numbers.
2. Marks the message with an explicit `untrusted_external_content` trust boundary.
3. Scores phishing language, prompt-injection patterns and suspicious URL forms.
4. Quarantines prompt-injection messages for review and prevents them from being interpreted as commands.
5. Preserves the existing Gmail triage buckets for normal operational use.

## Outgoing-mail contract

The secure intelligence layer does not contact Gmail, SMTP or another mail provider directly.

AI-generated outgoing mail must be represented as a review request. Review requests:

- require explicit owner approval;
- block drafts that contain secret-like material;
- become a one-time provider-send authorization after approval;
- cannot be consumed twice;
- maintain a bounded local audit trail.

The actual provider adapter must still execute through KRISHNA's governed action path. This keeps provider delivery, deletion, forwarding and other external mutations behind the Shared Action Bus and its permission/approval/audit controls.

## Existing KRISHNA integration

`Orchestrator` already owns one `GmailTriage` instance and exposes `gmail.triage` through the Shared Action Bus. Therefore existing callers automatically receive the new security assessment and model-safe message envelope without changing the public action name.

The existing authenticated MCP transport continues to expose only Shared Action Bus tools, so email content cannot create a new MCP command by itself.

## Follow-up integration contract

When a live provider adapter is connected later, it should expose separate scoped actions rather than a single broad mail permission:

- `mail.read`
- `mail.search`
- `mail.draft`
- `mail.request_send`
- `mail.send_approved` (mutating + explicit approval)
- `mail.archive`
- `mail.move`
- `mail.delete` (mutating + explicit approval)

Provider OAuth/API credentials must stay in KRISHNA's secure credential boundary and must never be inserted into model context, action receipts, prompts, or logs.

## Regression coverage

`core/tests/test_secure_gmail_triage.py` covers:

- prompt-injection quarantine;
- secret redaction before model use;
- explicit owner review before send authorization;
- one-time send authorization;
- outgoing secret leakage prevention;
- preservation of normal sales classification.
