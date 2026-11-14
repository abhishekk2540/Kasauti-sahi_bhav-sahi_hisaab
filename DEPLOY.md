# Deploy Kasauti: Neon + Azure Container Apps + Vercel + GitHub Actions + Sentry

Order matters: **Database -> Backend -> Frontend -> connect them -> Telegram -> monitoring -> CI/CD.**
Commands for Azure/Neon/Vercel were written from documentation knowledge and NOT run against real accounts. If one fails,
read its error and the linked portal screen; names of options can change.

You will collect these values as you go. Keep them in a notes file (never in Git):

| Name | Comes from | Used in |
|---|---|---|
| `DATABASE_URL` | Neon (step 1) | Azure app, GitHub secret |
| `JWT_SECRET` | you generate (step 0) | Azure app, GitHub secret |
| `GROQ_API_KEY` | console.groq.com | Azure app, GitHub secret |
| `BACKEND_URL` | Azure (step 3) | Vercel, Telegram |
| `FRONTEND_URL` | Vercel (step 5) | Azure CORS |
| `TELEGRAM_*` | @BotFather | Azure app, GitHub secret |
| `SENTRY_DSN` | sentry.io | Azure app, GitHub secret |

## 0. Prepare
- Accounts: GitHub (repo already pushed), Neon, Azure (with an active subscription), Vercel, Sentry, Groq, Telegram.
- Install Azure CLI and log in: `az login`. Then: `az extension add --name containerapp --upgrade`,
  `az provider register -n Microsoft.App --wait`, `az provider register -n Microsoft.OperationalInsights --wait`.
- Generate the JWT secret: `python -c "import secrets;print(secrets.token_urlsafe(48))"`
- Make the repo's `main` branch the deploy branch. Keep `backend/.env` out of Git (the `.gitignore` already does).

## 1. Database: Neon
1. neon.com > create project. Region: nearest to your Azure region (Singapore or Mumbai if offered).
2. Copy the **connection string** (looks like `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`).
   Prefer the *pooled* string (host contains `-pooler`). Save it as `DATABASE_URL`.
3. Turn on whatever backup / point-in-time-restore option your Neon plan gives. Rates history cannot be re-created.
4. Tables are created automatically on the backend's first start. There are no migrations yet (see "Before real customers").

## 2. Azure: registry + environment
Pick unique names. Example uses Central India; use the region closest to your users.
```bash
RG=kasauti-rg;  LOC=centralindia;  ACR=kasautiacr$RANDOM;  ENV=kasauti-env;  APP=kasauti-api
az group create -n $RG -l $LOC
az acr create -n $ACR -g $RG --sku Basic --admin-enabled true
az containerapp env create -n $ENV -g $RG -l $LOC
echo $ACR    # write this name down
```

## 3. Azure: first backend deploy
Build the first image in Azure (no Docker needed on your PC) and create the app:
```bash
az acr build -r $ACR -t kasauti-api:v1 ./backend          # run from the repo root

ACR_PASS=$(az acr credential show -n $ACR --query "passwords[0].value" -o tsv)

az containerapp create -n $APP -g $RG --environment $ENV \
  --image $ACR.azurecr.io/kasauti-api:v1 \
  --registry-server $ACR.azurecr.io --registry-username $ACR --registry-password "$ACR_PASS" \
  --target-port 8000 --ingress external \
  --cpu 0.5 --memory 1.0Gi --min-replicas 1 --max-replicas 1 \
  --secrets "dburl=<DATABASE_URL>" "jwt=<JWT_SECRET>" "groq=<GROQ_API_KEY>" "tgtoken=<TELEGRAM_BOT_TOKEN>" "tgsecret=<TELEGRAM_WEBHOOK_SECRET>" "sentry=<SENTRY_DSN>" \
  --env-vars APP_ENV=production DATABASE_URL=secretref:dburl JWT_SECRET=secretref:jwt GROQ_API_KEY=secretref:groq \
     TELEGRAM_BOT_TOKEN=secretref:tgtoken TELEGRAM_WEBHOOK_SECRET=secretref:tgsecret SENTRY_DSN=secretref:sentry \
     TELEGRAM_BOT_USERNAME=<bot_username> RATE_PROVIDER=goldapi RATE_ADJUST_GOLD_PCT=0 RATE_ADJUST_SILVER_PCT=0 \
     CORS_ORIGINS=http://localhost:3000

az containerapp show -n $APP -g $RG --query properties.configuration.ingress.fqdn -o tsv   # = your BACKEND_URL host
```
Notes:
- Leave out any secret you do not have yet (for example Telegram/Sentry) and add later with `az containerapp secret set` + `az containerapp update --set-env-vars`.
- `APP_ENV=production` makes the app refuse to start without `JWT_SECRET`, and the Telegram webhook refuses calls without its secret.
- Keep **max-replicas 1** for now: tables are created at startup and two instances starting together could race.
- **Check:** open `https://<fqdn>/health` -> `{"status":"ok"}`, and `https://<fqdn>/docs` loads.
  If not: `az containerapp logs show -n $APP -g $RG --follow`.

## 4. Real rates + AI check (backend only)
Sign up through `/docs` (POST `/auth/signup`), authorize, then call `POST /rates/refresh`.
- `ok: true` -> live prices work. `ok: false` -> read `error` (the price provider may need changing).
- Compare the gold price with a local jeweller's rate and tune `RATE_ADJUST_GOLD_PCT` / `RATE_ADJUST_SILVER_PCT`:
  `az containerapp update -n $APP -g $RG --set-env-vars RATE_ADJUST_GOLD_PCT=6`
- Test AI: `POST /agent/chat` with `{"messages":[{"role":"user","content":"aaj gold ka rate?"}]}`.

## 5. Frontend: Vercel
1. vercel.com > Add New > Project > import the GitHub repo.
2. **Root Directory = `frontend`**. Framework preset: Next.js (auto).
3. Environment variable: `NEXT_PUBLIC_API_URL` = `https://<azure fqdn>` (https, no trailing slash).
4. Deploy. Note the URL (for example `https://kasauti.vercel.app`) = `FRONTEND_URL`.
`NEXT_PUBLIC_*` values are baked in at build time: if the backend URL changes, edit the variable and **redeploy**.

## 6. Connect them (CORS)
The browser calls the backend directly, so the backend must allow the Vercel address:
```bash
az containerapp update -n $APP -g $RG --set-env-vars CORS_ORIGINS=https://<your-vercel-domain>
```
(Several origins: comma-separated, no spaces. Add your custom domain here too later.)
**Check:** open the Vercel URL, sign up, press *Fetch rates now*, open the banner.

## 7. Telegram
1. @BotFather > `/newbot` > save the token and username. Set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET` (any random string) on the Azure app.
2. Register the webhook once:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook" -d "url=https://<azure fqdn>/telegram/webhook" -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
   ```
3. In the app: Settings > Open Telegram > Start. Customers get their own invite link on the Customers page.

## 8. CI/CD with GitHub Actions
**(a) Deploy on every push to `main`** (`.github/workflows/deploy-backend.yml`: tests -> build in ACR -> new revision -> health check).
Passwordless login via OIDC. Run once:
```bash
SUB=$(az account show --query id -o tsv);  TENANT=$(az account show --query tenantId -o tsv)
az ad app create --display-name kasauti-github
APP_ID=$(az ad app list --display-name kasauti-github --query "[0].appId" -o tsv)
az ad sp create --id $APP_ID
az role assignment create --assignee $APP_ID --role Contributor --scope /subscriptions/$SUB/resourceGroups/$RG
az ad app federated-credential create --id $APP_ID --parameters '{
  "name":"github-main","issuer":"https://token.actions.githubusercontent.com",
  "subject":"repo:<github-user>/<repo>:ref:refs/heads/main","audiences":["api://AzureADTokenExchange"]}'
echo $APP_ID $TENANT $SUB
```
GitHub repo > Settings > Secrets and variables > Actions:
- **Secrets:** `AZURE_CLIENT_ID` (=APP_ID), `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
- **Variables:** `AZURE_RESOURCE_GROUP` (=kasauti-rg), `AZURE_ACR_NAME` (=your ACR name), `AZURE_CONTAINER_APP` (=kasauti-api)

**(b) Daily rates / alerts / reminders** (`daily-job.yml`, 09:15 IST). It talks to Neon directly, so add **Secrets:**
`DATABASE_URL`, `JWT_SECRET`, `GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`, `SENTRY_DSN` (and optional variables
`RATE_ADJUST_GOLD_PCT`, `RATE_ADJUST_SILVER_PCT`: **keep them equal to the Azure values**). Run it once via Actions > Daily rates + alerts > Run workflow.
The job exits red when the price API fails, which is your signal.

**(c) Frontend** deploys by itself: Vercel redeploys on every push to `main` and makes preview URLs for PRs.

## 9. Sentry
1. sentry.io > create project, platform **FastAPI/Python** > copy the DSN (already wired in step 3 and the daily job).
2. Trigger a test: `curl https://<fqdn>/does-not-exist` is a 404 (not an error); to see an event temporarily raise an exception in a route, or check Sentry > Issues after a real failure.
3. The backend sends no request bodies, cookies, IPs or auth headers (login passwords and customer phone numbers stay out of Sentry).
4. Frontend monitoring is not added yet. Later: `npx @sentry/wizard@latest -i nextjs` inside `frontend/`.

## 10. Dependabot
`.github/dependabot.yml` is included: weekly PRs for pip, npm, Docker and GitHub Actions. In repo Settings > Code security, also enable **Dependabot alerts** and **security updates**. CI runs on those PRs; merge when green.

## 11. Go-live checklist
- [ ] `/health` OK on Azure; signup + login work from the Vercel URL
- [ ] `POST /rates/refresh` returns `ok: true`; price roughly matches a local jeweller (adjust %)
- [ ] Margin saved, banner shows correct Indian-format price
- [ ] AI chat answers; "mark paid" shows a confirmation card
- [ ] Telegram: you receive a test alert; a customer link works; `/stop` opts out
- [ ] Daily job ran green once from the Actions tab
- [ ] Sentry receives a test event
- [ ] Neon backups confirmed; secrets only in Azure/GitHub/Vercel (none in Git)
- [ ] Custom domain (optional): Vercel > Domains; add it to `CORS_ORIGINS`

## Before real customers
1. **Add Alembic migrations.** Today tables come from `create_all`; changing a column later will not update an existing database.
2. Check the legal/consent side (customer opt-in is built; get advice on messaging rules and the disclaimer wording).
3. Review costs: min-replica 1 on Container Apps, ACR Basic and Neon's free-tier limits (autosuspend makes the first request after idle slower).

## Rollback
```bash
az containerapp revision list -n $APP -g $RG -o table
az containerapp update -n $APP -g $RG --image $ACR.azurecr.io/kasauti-api:<older-git-sha>
```
Vercel: Deployments > pick an older one > Promote to Production.
