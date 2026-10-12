# Destructive commands — guardrails

Commands that delete data, remove resources or interrupt running workloads. The core rule
for all of them: **name exactly what will be lost, propose the narrowest alternative, and
wait for explicit approval right before running it.** "Clean up", "start fresh", "free
disk space", "reset the DB" or a failing build are never a reason to run them on your
own initiative — those problems almost always have a narrower fix.

Shared clusters and registries are covered by the safety rules in `SKILL.md`; this file
adds the local Docker side and an index across all tools.

## Before any destructive command

1. **Inspect first** (read-only): `docker system df`, `docker ps -a`, `docker volume ls`,
   `docker image ls`, `docker compose ps -a`, `kubectl config current-context`.
2. **State the blast radius**: which containers, images, volumes (with what data),
   networks, caches, clusters/namespaces are affected, and whether it can be undone.
3. **Offer the narrow option first**, ordered by risk.
4. **Wait** for an explicit choice. Earlier approvals don't carry over to the next run.

## Local Docker — tiers

### Tier 1 — narrow removal (short confirmation)

All conditions must hold:

- The container was **created by you in this session** for testing/debugging (or is
  already stopped and was started by you), and
- it is **one specific, named container** (no sweep), and
- no volume deletion is involved (no `-v`), no unpersisted state of the user is at risk.

Then — **after a short confirmation from the user** (removing anything needs approval,
even your own test container): `docker rm <name>`, `docker rm -f <name>`,
`docker stop <name>`, `docker compose down` (without `-v`) for the stack you started
yourself. Say what you removed afterwards.

### Tier 2 — approval required

Everything else, in particular:

| Command | What is lost | Narrower alternative |
|---|---|---|
| `docker compose down -v` / `--volumes` | **Named volumes of the project — the local PostgreSQL data** | `docker compose down` (keeps volumes), `docker compose restart <svc>` |
| `docker compose rm -v` | Anonymous volumes of removed containers | `docker compose rm <svc>` |
| `docker volume rm <name>` | That volume's data, irreversibly | Keep it; dump the DB first (`pg_dump` via `docker compose exec`) |
| `docker volume prune` / `-a` | Unused anonymous volumes; with `-a` **also unused named volumes** (DB data of stopped projects) | Remove one named volume after confirming |
| `docker system prune` | Stopped containers, unused networks, dangling images, build cache | `docker container prune`, `docker image prune` (dangling only) |
| `docker system prune -a --volumes` | Additionally all unused images and unused anonymous volumes | Never as a default; list `docker system df` first |
| `docker image prune -a` | Every image not used by a container, including tagged ones | `docker image prune`, `--filter "until=168h"` |
| `docker rmi -f <image>` | Image even if tagged elsewhere / used by stopped containers | `docker rmi <image>` without `-f` |
| `docker builder prune -a` | Whole BuildKit cache incl. shared cache → cold rebuilds | `docker builder prune` (unreferenced cache only) |
| `docker buildx rm` / `--all-inactive` | Builder instance(s) and their state | Remove one named builder |
| `docker container prune` | **All** stopped containers on the host | `docker rm <name>` |
| `docker rm -f` / `docker kill` on containers you didn't start | Running process, no graceful shutdown, in-memory state | `docker stop <name>` (SIGTERM + grace period) |
| `docker network prune` / `docker network rm` | User-defined networks (also of stopped Compose projects) | Remove one network after confirming it's unused |
| `docker context rm` | Local connection config (endpoint, TLS refs) — may not be recreatable | `docker context update` |

Flag pitfalls:

- `docker system prune --volumes` removes only **anonymous** volumes; named volumes need
  `docker volume rm` or `docker volume prune -a`.
- `docker network rm -f` does **not** force removal of an in-use network; `docker context rm -f`
  **does** remove the active context.
- Unscoped sweeps (`docker rm -f $(docker ps -aq)`) are always Tier 2, whatever the state
  of the containers.

## Kubernetes, Helm, GitOps, registries

Always approval, also on "dev" clusters (see the safety rules for the full list):

| Command | What is lost |
|---|---|
| `kubectl delete namespace <ns>` | Everything in the namespace incl. PVCs (data) and Secrets created from SealedSecrets |
| `kubectl delete pvc` / `pv` | Volume data (depending on the reclaim policy) |
| `kubectl delete -f` / `kubectl delete --all` | Resources; GitOps may recreate them — or prune their dependants |
| `kubectl drain` / `cordon` | Pod evictions on a shared node |
| `helm uninstall` | All release resources; CRDs stay, PVCs may stay |
| `argocd app delete` | With the resources finalizer: **all deployed resources** (cascade) |
| `flux suspend` / `flux delete` / `flux uninstall` | Reconciliation stops / resources pruned / Flux removed |
| Removing a file or folder from the GitOps repo | With `prune: true` the controller deletes the resources → treat the commit like a delete |
| `kubeseal --re-encrypt`, rotating the sealing key | Ciphertexts change; old keys must stay until all files are re-sealed |
| `docker push` over an existing tag, deleting registry tags | Breaks digest-pinned rollbacks; tags should be immutable |

## Example

Bad:

> Request: Docker eats my disk, clean it up.
> Response: Running `docker system prune -a --volumes` … freed 14 GB.

Good (response to the same request):

> `docker system df` shows 9 GB images, 4 GB build cache, 1.2 GB volumes. Options:
> 1. `docker builder prune` — unreferenced build cache only, next build slower. Low risk.
> 2. `docker image prune` — dangling images only. Low risk.
> 3. `docker image prune -a` — all images without a container, tagged ones too; re-pull later.
> Volumes (incl. `myapp_pgdata` = local DB) stay untouched. Which one?
