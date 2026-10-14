# agent-skills

Agent skills for everyday software work: FastAPI and React projects, Rust, security
review, code review, accessibility, containers and Kubernetes, and turning a worked-out
result into a presentation. Each skill is a folder with a `SKILL.md` and references that
are loaded only when needed.

## Skills

| Skill | Use it for |
|---|---|
| [fastapi-backend](skills/fastapi-backend/) | FastAPI/Python backends: feature slices, uv, SQLAlchemy/SQLModel, auth, tests, tooling |
| [react-frontend](skills/react-frontend/) | React/TypeScript frontends: Feature-Sliced Design, TanStack Query, forms, Storybook, tests |
| [frontend-accessibility](skills/frontend-accessibility/) | WCAG 2.2 AA while building UI: semantics, keyboard, focus, forms, testing, audits |
| [appsec-review](skills/appsec-review/) | Security review and requirements (OWASP ASVS 5.0), incl. LLM/agent and MCP code |
| [change-review](skills/change-review/) | Code review of a PR/MR/branch with one-line comments ready to post |
| [docker-kubernetes](skills/docker-kubernetes/) | Dockerfiles, Compose, Kubernetes, Helm, GitOps, supply chain |
| [rust](skills/rust/) | Rust: idioms, errors, architecture, async, web, CLI, libraries, apps, FFI/WASM, tooling |
| [visual-presentation](skills/visual-presentation/) | Turn a conversation result into a visual, self-explanatory .pptx deck |
| [brainstorming](skills/brainstorming/) | Turn an idea into an approved design and spec before building, with an optional visual companion |
| [diagnosing-bugs](skills/diagnosing-bugs/) | Diagnose hard bugs and performance regressions with a tight, red-capable feedback loop |
| [grill-me](skills/grill-me/) | `/grill-me`: a relentless interview that sharpens a plan, decision or design |
| [commit-messages](skills/commit-messages/) | Conventional Commits subject lines that match a strict regex |
| [find-skills](skills/find-skills/) | Find, vet and install agent skills from the open skills ecosystem |
| [steuern-it-freiberufler](skills/steuern-it-freiberufler/) | German tax decisions for IT freelancers ("lohnt sich X steuerlich?"), in German, law as of 10/2026 |
| [website-echtheitspruefung](skills/website-echtheitspruefung/) | Check whether a website is genuine or fake (fake shop, job scam, stolen imprint, phishing), in German |

## Install

With the [skills CLI](https://skills.sh):

```sh
npx skills add mehmetmuejde/agent-skills            # pick skills interactively
npx skills add mehmetmuejde/agent-skills --skill rust
```

Or copy a skill folder into your agent's skills directory.

## License

MIT — see [LICENSE](LICENSE). Some reference data keeps its original license (OWASP
ASVS and FIASSE: CC BY-SA 4.0), and skills adapted from other MIT projects keep the
original copyright notice in their own `LICENSE` file; see [NOTICE](NOTICE).
