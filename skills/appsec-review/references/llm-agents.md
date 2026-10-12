# LLM, agent and RAG review checklist

Load this when the code under review calls an LLM API, builds prompts, defines
tools/function calling, runs an agent loop, retrieves context (RAG, vector store), keeps
agent memory, or renders model output. MCP servers/clients: also `mcp.md`.

Standards: **OWASP Top 10 for LLM Applications 2025** (LLM01–LLM10) and **OWASP Top 10
for Agentic Applications 2026** (ASI01–ASI10). ASVS 5.0 has no LLM chapter — cite the
ASVS requirement of the underlying weakness (authorization, injection, logging,
resource limits) where one exists.

## Ground rules for LLM findings

- **Assume prompt injection succeeds.** Any text the model reads from an untrusted source
  can steer it. The question in review is: *what can the model do, with whose rights, and
  where can data go, once it is steered?*
- **Instructions in a prompt are not a security control.** "Never reveal…", "only call
  delete when…" in a system prompt don't count as authorization, validation or secrecy.
- **Regex/keyword blocklists against prompt injection are not a fix.** Don't propose them
  as remediation; propose structural controls (authorization in code, confirmation,
  output validation, removing capabilities or outbound channels).
- **Model output is untrusted input** to every sink it reaches (DB, shell, HTML, file
  system, HTTP, other agents).

---

## 1. Map the data flow first

Record for the reviewed feature:

| Aspect | Question |
|---|---|
| Provider / client | Which SDK, which model, where is the API key held (server only?) |
| Prompt construction | Where do system prompt, user input and context get combined? |
| Context sources | User input, uploaded files, RAG documents, web pages, emails, tool results, other agents, memory |
| Tools / actions | Which functions can the model trigger; read-only or mutating; external effects |
| Identity | With whose permissions do tools run — the requesting user, or a service account? |
| Output sinks | Where does model output go: UI (HTML/Markdown), DB, shell, files, URLs, emails, other agents |
| Memory | What persists across turns/sessions, scoped per user/tenant? |
| Limits | `max_tokens`, timeouts, retries, loop/step limits, per-user quotas |

### Injection surface

| Input path | Risk | Vector |
|---|---|---|
| User message | Medium | Direct prompt injection |
| Uploaded files, web fetches, emails | High | Indirect injection |
| RAG / vector store documents | High | Indirect injection via poisoned documents |
| Tool / MCP results, resources | High | Indirect injection via data |
| Other agents' messages | High | Inter-agent injection |
| Environment, config | Low | Supply-chain / config injection |

**Dangerous combination**: untrusted content in the context **+** access to private data
**+** an outbound channel (HTTP fetch, email/message send, link/image rendering, writing
to shared places). If all three are present for one model turn without a human
confirmation in between, report the exfiltration path — usually High.

---

## 2. LLM Top 10 2025

### LLM01 — Prompt Injection (CWE-1427)

- [ ] Untrusted content goes into user/tool messages, clearly delimited and labelled as
      data — never concatenated into the system prompt.
- [ ] Indirect sources (files, RAG, web, email, tool output) are treated as untrusted.
- [ ] The impact of a successful injection is bounded by code: tool authorization
      (LLM06), confirmation for consequential actions, no unneeded outbound channels.
- [ ] No reliance on prompt wording as the only defence.

### LLM02 — Sensitive Information Disclosure (CWE-359, CWE-532)

- [ ] The context contains only data the **requesting user** may see (no other users'
      records, no admin data "for the model's information") [8.2.2].
- [ ] PII sent to a third-party provider is minimized/redacted; data-processing terms
      and retention settings are a documented decision (else "Out of scope / not checked").
- [ ] Prompts and completions are logged only redacted, or not at all [16.2.5].
- [ ] Error messages from the provider (may contain prompt fragments) aren't returned to
      the client [16.5.1].

### LLM03 — Supply Chain (CWE-494, CWE-502)

- [ ] Model weights/adapters from trusted, pinned sources; `safetensors` instead of
      pickle; `torch.load(..., weights_only=True)`.
- [ ] No `trust_remote_code=True` for models from unvetted repos (CWE-94).
- [ ] Framework components with dangerous capabilities (Python REPL tools, shell tools,
      `allow_dangerous_*` flags) are a deliberate, sandboxed choice.
- [ ] SDKs pinned in the lockfile; see `secrets-and-dependencies.md`.

### LLM04 — Data and Model Poisoning (no specific CWE; cite the access-control weakness)

- [ ] Who can add documents to the RAG corpus or memory, and is it per tenant?
- [ ] Ingested documents keep provenance (source, uploader, tenant); untrusted sources
      are separated from curated ones.
- [ ] Fine-tuning/feedback data from users isn't used unreviewed.

### LLM05 — Improper Output Handling (CWE by sink: 89, 78, 94, 79, 22, 918, 601)

- [ ] Model output never reaches `text()`/raw SQL, `subprocess`/shell, `eval`/`exec`,
      file paths, URLs fetched by the server, redirects, `HTMLResponse`, templates or
      email headers without the same validation as user input [1.2.4, 1.2.5, 1.3.2,
      1.3.6, 5.3.2].
- [ ] Structured output is parsed into a Pydantic model (enums/`Literal` for actions,
      constrained fields) and validated before use [2.2.1].
- [ ] Frontend renders model output as text or sanitized Markdown (see
      `frontend-checklist.md` §10) [1.3.5].

### LLM06 — Excessive Agency (CWE-250, CWE-862, CWE-269)

- [ ] Tool set is minimal for the feature; no generic tools (raw SQL, shell, arbitrary
      HTTP, arbitrary file read/write) unless sandboxed and justified.
- [ ] Tools run with the **requesting user's** identity and permissions; the code passes
      `current_user` into the tool — the model never supplies `user_id`, `tenant_id`,
      `owner_id` or roles (Derived Integrity) [8.3.3, 8.2.2].
- [ ] Authorization is checked **inside** each tool (same scoping as the REST endpoint).
- [ ] Destructive, irreversible, financial or externally visible actions (delete, pay,
      send, publish, push) need human confirmation: the server stores a pending action,
      the user confirms it in a separate request [2.3.5].
- [ ] Credentials available to tools are scoped and short-lived.

### LLM07 — System Prompt Leakage (CWE-200, CWE-798)

- [ ] No secrets, API keys, connection strings, internal URLs or user data in system
      prompts [13.3.1].
- [ ] No security rule exists only in the system prompt (assume it is public).

### LLM08 — Vector and Embedding Weaknesses (CWE-639)

- [ ] Vector queries filter by tenant/user/ACL **in the query** (`WHERE tenant_id = :tid`
      with pgvector, metadata filter in the vector DB) — not by post-filtering in Python,
      not by trusting the model [8.4.1, 8.2.2].
- [ ] Separate collections/namespaces per tenant where the store supports it.
- [ ] Access rights of a document are checked at ingestion and retrieval time; deleting
      a document removes its embeddings.
- [ ] Embeddings of sensitive documents are treated as sensitive data [14.1.1].

### LLM09 — Misinformation

- [ ] High-stakes output (legal, medical, financial, code that gets executed) has human
      review, grounding/citations, or is marked as generated. Usually `Info` in code
      review unless an automated decision depends on it.

### LLM10 — Unbounded Consumption (CWE-770, CWE-400)

- [ ] `max_tokens` / `max_output_tokens` set on every call.
- [ ] Client timeout and bounded retries (`timeout=`, `max_retries=`) [13.2.6].
- [ ] Agent loops have a step/iteration limit and a tool-call budget.
- [ ] Per-user rate limit and cost budget for LLM endpoints [2.4.1, 15.2.2].
- [ ] Input size limited (message length, file size, number of documents in context).
- [ ] Streaming responses and connections bounded.

---

## 3. Agentic Top 10 2026 (for tool-calling and agent loops)

| Id | Name | Check in code |
|---|---|---|
| ASI01 | Agent Goal Hijack | Goals and allowed task types fixed by code; untrusted content can't add tasks; outbound actions confirmed; exfiltration channels (fetch, send, image/link rendering) limited. |
| ASI02 | Tool Misuse and Exploitation | Tool parameters validated by schema (enums, path/URL allowlists, length limits); dangerous chains (read private data → send externally) blocked or confirmed; tool results treated as untrusted. |
| ASI03 | Identity and Privilege Abuse | Per-user delegated credentials, not an admin service account; no credentials in prompts or tool descriptions; no forwarding of the user's token to third parties (see `mcp.md` token passthrough). |
| ASI04 | Agentic Supply Chain Vulnerabilities | Third-party tools, MCP servers, plugins and prompt templates pinned and reviewed; no dynamic loading of tools from untrusted registries; tool definitions can't change silently (`mcp.md`). |
| ASI05 | Unexpected Code Execution (RCE) | Generated code runs only in a sandbox (container/VM without secrets and network, CPU/memory/time limits); no `exec`/`eval`/shell on model output in the app process. |
| ASI06 | Memory & Context Poisoning | Memory writes from untrusted content are restricted; memory scoped per user/tenant, with provenance and expiry; users can inspect/delete it. |
| ASI07 | Insecure Inter-Agent Communication | Agent-to-agent messages authenticated, schema-validated and treated as data, not as privileged instructions; A2A endpoints require auth. |
| ASI08 | Cascading Failures | Validation between pipeline stages; step limits, circuit breakers, idempotent actions; a kill switch to stop running agents. |
| ASI09 | Human-Agent Trust Exploitation | Confirmations show the real operation and parameters from server state, with a diff for changes; no auto-approve defaults; "approve all" not available for destructive actions. |
| ASI10 | Rogue Agents | Every tool call audit-logged (actor, on-behalf-of user, tool, parameters redacted, outcome) [16.2.1, 16.3.3]; agents can't change their own permissions/config; agents can be disabled and their credentials revoked. |

---

## 4. Grep patterns

Python:

```bash
rg -n --type py 'chat\.completions\.create|responses\.create|messages\.create|ChatOpenAI|ChatAnthropic|litellm\.(a?completion)|generate_content|\.a?invoke\(|Agent\('   # LLM calls
rg -n --type py 'max_tokens|max_output_tokens|max_completion_tokens|max_retries|timeout\s*='                                        # limits present?
rg -n --type py 'system_prompt\s*=\s*f|["'\'']role["'\'']\s*:\s*["'\'']system["'\''].*f["'\'']|SystemMessage\(\s*content\s*=\s*f'      # input in system prompt
rg -n --type py 'f["'\'']{1,3}.*\{(request|body|payload|user_input|message|query|q|text|content)\b'                                # prompt f-strings with request data
rg -n --type py -i '(system|prompt).*(settings\.|os\.environ|getenv|api_key|password|secret|token)'                              # secrets near prompts
rg -n --type py '(text|execute)\(.*(completion|response|output|result|answer|content)'                                          # output → SQL
rg -n --type py '(subprocess\.\w+|os\.system|eval|exec)\(.*(completion|response|output|result|answer|content|tool_call|arguments)' # output → exec
rg -n --type py '(HTMLResponse|Path|open|RedirectResponse|httpx\.\w+)\(.*(completion|response|output|result|answer|content)'        # output → HTML/file/URL
rg -n --type py '@tool|@function_tool|@\w+\.tool\(|StructuredTool|Tool\(|tools\s*=\s*\[|tool_choice|function_call'                # tool definitions
rg -n --type py 'def \w+\([^)]*(user_id|tenant_id|owner_id|account_id|role)\s*:'                                                 # model-controlled identity params in tools
rg -n --type py 'PythonREPLTool|PythonAstREPLTool|ShellTool|allow_dangerous|trust_remote_code|torch\.load\(|from_pretrained\('    # dangerous capabilities
rg -n --type py 'log(ger)?\.\w+\(.*(prompt|messages|completion|response\.content|output_text)'                                   # prompt/response logging
rg -n --type py 'similarity_search|as_retriever|max_marginal_relevance|<=>|<->|<#>|cosine_distance|l2_distance|\.query\(.*(vector|embedding)' # vector queries — tenant filter?
rg -n --type py -i 'memory|save_context|add_memory|remember|mem0|checkpointer'                                                   # long-term memory
```

TypeScript / frontend:

```bash
rg -n -t ts -t js 'from ["'\''](openai|@anthropic-ai/sdk|ai|@ai-sdk/\w+)["'\'']|streamText|generateText|useChat'   # LLM SDK in the browser?
rg -n 'VITE_\w*(OPENAI|ANTHROPIC|LLM|AI|MODEL)\w*KEY' -g '!node_modules'                                           # provider key shipped to the browser → Critical
```

A provider API key in browser code is always a finding (Critical if it has spending or
data access); calls go through the backend.

---

## 5. Prompt-injection testing (not part of a review)

Active testing is out of scope for a code review. Offer it only as a follow-up, run it
only on explicit request, against a local or staging environment, with the allowed test
intents agreed first. Useful intents (from the Arcanum PI taxonomy): system prompt
extraction, tool enumeration, extraction of secrets from the prompt, attacking other
users through stored output, data/memory poisoning, resource exhaustion. Record results
as findings with the exact payload, the surface used and the missing control.

## Sources

- OWASP Top 10 for LLM Applications 2025 — <https://genai.owasp.org/llm-top-10/>
- OWASP Top 10 for Agentic Applications 2026 — <https://genai.owasp.org/>
- OWASP Secure Agent Playbook (CC BY 4.0): plays `agent-security-audit`,
  `llm-risk-assess`, `agentic-ai-risk-assess`, `prompt-injection-testing` — condensed;
  code examples not taken over.
- Arcanum Prompt Injection Taxonomy by Jason Haddix (Arcanum Information Security),
  CC BY 4.0 — <https://github.com/Arcanum-Sec/arc_pi_taxonomy> (input surfaces, test
  intents).
