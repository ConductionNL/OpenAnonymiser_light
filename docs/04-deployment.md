# Deployment

## Container (Docker / Podman)

```bash
# Bouwen
docker build -t openanonymiser-light:latest .
# of: podman build -t openanonymiser-light:latest .

# Draaien
docker run -d -p 8001:8080 --name openanonymiser openanonymiser-light:latest

# Smoke test
curl -s http://localhost:8001/api/v1/health
```

Het image bevat SpaCy `nl_core_news_md` (baked in). Startup duurt ~10s door model loading.

### Omgevingsvariabelen voor container

```bash
docker run -d -p 8001:8080 \
  -e UVICORN_SERVER_MODE=production \
  -e DEFAULT_NLP_ENGINE=spacy \
  -e DEFAULT_SPACY_MODEL=nl_core_news_md \
  openanonymiser-light:latest
```

Zie [configuration.md](03-configuration.md) voor alle variabelen.

---

## Kubernetes met Helm

De service is **stateless** — geen PVC, geen database, geen volumes vereist.

### Dry-run validatie

```bash
helm template openanonymiser ./charts/openanonymiser
```

### Installatie / upgrade

```bash
# Installeer (vraag eerst bevestiging)
helm install openanonymiser ./charts/openanonymiser

# Upgrade
helm upgrade openanonymiser ./charts/openanonymiser
```

### Values configuratie

Zie `charts/openanonymiser/values.yaml` voor alle opties. Minimale productie-setup:

```yaml
image:
  repository: mwest2020/openanonymiser
  tag: main        # of: latest, dev (staging)

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: "api.openanonymiser.example.com"
  tls:
    - secretName: openanonymiser-tls
      hosts:
        - "api.openanonymiser.example.com"

persistence:
  enabled: false   # Stateless – geen PVC nodig

app:
  env:
    uvicornServerMode: "production"
    defaultNlpEngine: "spacy"
    defaultSpacyModel: "nl_core_news_md"
```

---

## CI/CD (GitHub Actions)

| Workflow | Trigger | Actie |
|---------|---------|-------|
| `docker-build.yml` | push `main` of `staging` | Build + push image naar registry |
| Retag | handmatig / tag | Promoot `dev` digest naar `version`/`main`/`latest` |

Images:
- `main` branch → `:main` en `:latest`
- `staging/development` → `:dev`

---

## ArgoCD (GitOps)

ArgoCD applicaties staan in `argocd/`:

```
argocd/staging-app.yaml     → branch: staging, ns: openanonymiser-accept
argocd/production-app.yaml  → branch: main,    ns: openanonymiser
```

Staging deploy automatisch bij push naar `staging`; productie bij push naar `main`.

### DNS en TLS

| Environment | Host | TLS Secret |
|-------------|------|------------|
| Staging | `api.openanonymiser.accept.commonground.nu` | `openanonymiser-accept-tls` |
| Productie | `api.openanonymiser.commonground.nu` | `openanonymiser-tls` |

TLS via Let's Encrypt (`letsencrypt-prod` issuer, ingress class `nginx`).

### Verificatie

```bash
# Health
curl -s https://api.openanonymiser.accept.commonground.nu/api/v1/health

# Tests tegen staging
OPENANONYMISER_BASE_URL="https://api.openanonymiser.accept.commonground.nu" pytest tests/ -q

# K8s status
kubectl get pods -n openanonymiser-accept
kubectl get certificate,ingress -n openanonymiser-accept
kubectl get applications -n argocd
```

### Deployment checklist

- [ ] DNS resolveert naar cluster IP
- [ ] SSL certificaat geldig (Let's Encrypt)
- [ ] `/api/v1/health` → `{"ping":"pong"}`
- [ ] `/api/v1/analyze` en `/api/v1/anonymize` werken correct
- [ ] ArgoCD sync status: Healthy
