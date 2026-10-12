# Secrets — Sealed Secrets

Secrets reach the cluster only as `SealedSecret` objects committed to the GitOps repo.
The Sealed Secrets controller in the cluster holds the private key and turns each
`SealedSecret` into a normal `Secret`; `kubeseal` encrypts with the controller's public
certificate. A SealedSecret is safe to commit — a `kind: Secret` is not (base64 is not
encryption).

## Rules

- **Never commit** a raw `Secret`, `stringData`, a `.env` file, a values file with
  credentials or a sealing-key backup.
- **Whoever prepares the change never handles real values**: prepare the command; the
  person who owns the value runs it. Don't print, log, decode or paste secret values.
- Raw secret material exists only in memory or in a temp file outside the repo, removed
  right after sealing.
- **One sealed file per environment/cluster** — every cluster has its own key. Never
  copy a sealed file from prod to dev or vice versa.
- **Scope `strict`** (default) for all app secrets.
- SealedSecrets live in the GitOps environment folder (`envs/<env>/sealed-secrets/`),
  not in the app chart; the chart references the resulting Secret by name
  (`existingSecret`).
- Rotating the real value (password, API key) is required periodically and after any
  leak — controller key renewal does not replace it.

## Scopes

| Scope | Bound to | Use |
|---|---|---|
| `strict` (default) | name **and** namespace (part of the ciphertext) | All app secrets |
| `namespace-wide` | namespace; may be renamed | Only if the Secret's name must change per release |
| `cluster-wide` | nothing — any name, any namespace | Avoid. Anyone who can create a SealedSecret in *any* namespace can unseal your ciphertext into a Secret they can read. |

Name and namespace can't change after sealing with `strict` — renaming means sealing
again. Keys inside the Secret (`encryptedData.<key>`) can be renamed freely.

## Workflow

The controller's **public** certificate per cluster is committed
(`envs/<env>/sealed-secrets.pem`) so sealing works offline. Fetching it once talks to
the cluster (`kubeseal --fetch-cert`, approval required). Pass `--controller-name` /
`--controller-namespace` if the controller isn't `sealed-secrets-controller` in
`kube-system` (the Helm chart installs it as `sealed-secrets`).

```bash
# Run by the person who owns the value. Nothing is written into the repo unencrypted.
read -rs DB_PASSWORD                     # typed, not echoed, not in shell history

kubectl create secret generic backend-secrets \
    --namespace myapp-prod \
    --from-literal=DATABASE_PASSWORD="$DB_PASSWORD" \
    --dry-run=client -o yaml \
  | kubeseal --cert envs/prod/sealed-secrets.pem --format yaml \
  > envs/prod/sealed-secrets/backend-secrets.yaml

unset DB_PASSWORD
```

- `--dry-run=client` never contacts the cluster; `kubeseal --cert` works offline.
- Add or change one key in an existing sealed file:

```bash
read -rs NEW_VALUE
kubectl create secret generic backend-secrets --namespace myapp-prod \
    --from-literal=OIDC_CLIENT_SECRET="$NEW_VALUE" --dry-run=client -o yaml \
  | kubeseal --cert envs/prod/sealed-secrets.pem --format yaml \
      --merge-into envs/prod/sealed-secrets/backend-secrets.yaml
unset NEW_VALUE
```

- Labels, annotations and type of the resulting Secret go into
  `spec.template.metadata` / `spec.template.type` of the SealedSecret, e.g. an image pull
  secret:

```bash
kubectl create secret docker-registry registry-credentials --namespace myapp-prod \
    --docker-server=registry.example.com --docker-username=puller \
    --docker-password="$REGISTRY_TOKEN" --dry-run=client -o yaml \
  | kubeseal --cert envs/prod/sealed-secrets.pem --format yaml \
  > envs/prod/sealed-secrets/registry-credentials.yaml
```

Resulting file (committed):

```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: backend-secrets
  namespace: myapp-prod
spec:
  encryptedData:
    DATABASE_PASSWORD: AgBy8hCi…   # ciphertext, safe in Git
  template:
    metadata:
      name: backend-secrets
      namespace: myapp-prod
      labels:
        app.kubernetes.io/name: backend
```

- Commit check before pushing: `git diff --cached` shows only `SealedSecret` objects and
  ciphertext; `rg -n '^kind:\s*Secret' envs/` finds nothing.
- `kubeseal --validate` checks a file against the controller — talks to the cluster,
  approval required.

## Controller key backup

Without the private keys, every SealedSecret in Git is unreadable after a cluster
rebuild. With them, everyone can decrypt everything in Git — treat the backup as the
most sensitive secret of the environment.

- Platform admins export the keys (approval required, never by the app team's tooling):
  `kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml`
- Store the export **offline** in the team's password manager / vault — never in Git,
  never in a ticket, chat or CI artifact.
- Restore: apply the key Secrets into the controller's namespace before (or then
  restart) the controller.
- Test the restore once per year on a throwaway cluster.

## Rotation

- **Sealing key renewal**: the controller adds a new key every 30 days
  (`--key-renew-period`). Old keys are kept, so existing SealedSecrets still decrypt;
  new sealing uses the newest key (fetch the cert again after renewal).
- **Re-encrypt** existing files with the newest key before old keys are retired:
  `kubeseal --re-encrypt < file > tmp && mv tmp file` (talks to the controller,
  approval required).
- **Real secret rotation** (the passwords and keys themselves) on a schedule and
  immediately after a suspected leak: change it at the source (DB, IdP, provider),
  seal the new value, commit, roll the pods.
- **Sealing key compromised**: renew early (`--key-cutoff-time` /
  `SEALED_SECRETS_KEY_CUTOFF_TIME`), then rotate **every** real secret that was sealed
  with it — Git history keeps the old ciphertexts forever.

## Access control

- Only the controller reads its key Secrets; restrict `get/list` on Secrets in the
  controller namespace to platform admins.
- App namespaces: nobody needs `list`/`watch` on Secrets except admins; apps read their
  own Secret via mounted files.
- The Secrets in etcd should be encrypted at rest (platform setting — ask, don't assume).

## Review checklist

- [ ] No `kind: Secret`, `stringData` or credentials in Git (charts, values, env folders).
- [ ] Every SealedSecret uses `strict` scope (no `sealedsecrets.bitnami.com/cluster-wide`
      or `namespace-wide` annotation without a documented reason).
- [ ] Sealed per environment; name/namespace match the target.
- [ ] Charts reference `existingSecret`; Secrets mounted as files.
- [ ] Key backup exists offline; rotation of real secrets is scheduled.
