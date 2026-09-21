# NARAD + n8n Integration

KRISHNA does not embed n8n or copy its workflow runtime. NARAD implements the useful workflow patterns natively and may call an external n8n instance only through Sudarshan.

## Authority

```text
UI / Agent / Job
      |
   Sudarshan
      |
Shared Action Bus / JobRuntime
      |
PermissionRuntime + PolicyKernel
      |
     NARAD
      |
 independent verifier
```

n8n is only an external webhook connector:

```text
NARAD -> narad.adapter_webhook -> N8nBridge -> allowlisted n8n webhook
```

It never owns KRISHNA agents, permissions, jobs, memory, credentials, browser control or desktop control.

## Native n8n-style patterns implemented in NARAD

- typed DAG workflow graph;
- explicit action/job node contracts;
- safe input/node-output mapping without eval;
- retry/backoff with retry-safe metadata;
- durable checkpoints and resume;
- dead-letter capture and retry;
- manual/event/schedule/webhook triggers;
- provider/connector contracts;
- execution history;
- lifecycle states Draft -> Candidate -> Sandbox -> Verified -> Stable;
- Sudarshan permission and approval gate;
- independent verification of every node and whole workflow;
- bounded in-process concurrency;
- read-only workflow plan inspection.

## Resource policy

No n8n process is started by KRISHNA.

NARAD uses no extra worker pool for this integration. Default workflow concurrency is 2 and the hard cap is 4.

Configure locally in:

```text
E:\Krishna-The GOD\config\narad-runtime.ps1
```

Example:

```powershell
$env:KRISHNA_NARAD_MAX_CONCURRENT = "2"
$env:KRISHNA_N8N_ALLOWED_HOSTS = "127.0.0.1,n8n.my-private-domain.example"
```

Remote n8n webhooks must use HTTPS and their hostname must be explicitly allowlisted. Localhost HTTP is allowed for a locally hosted n8n instance.

## Credentials

Credential values remain in KRISHNA's existing secure credential path. NARAD passes only resolved request headers at execution time. N8nBridge does not persist secrets.

## License boundary

The implementation is KRISHNA-native code inspired by workflow-engine patterns. It does not vendor n8n's source runtime or Enterprise-only source.
