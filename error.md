# Kasauti Deployment and Application Error History

This document records the application, authentication, Azure, and GitHub Actions issues encountered during deployment. It is intended to provide context to another engineer or coding agent.

## Project

- Repository: `abhishekk2540/Kasauti-sahi_bhav-sahi_hisaab`
- Frontend: Next.js 15.5.29
- Backend: FastAPI
- Frontend directory: `frontend`
- Backend directory: `backend`
- Azure resource group: `kasauti-rg`
- Azure region: `uaenorth`
- Azure Container Registry: `kasautiacr27103`
- Azure Container App: `kasauti-api`
- Azure backend hostname:
  `kasauti-api.gentledune-0984646a.uaenorth.azurecontainerapps.io`

Do not add database credentials, `.env` values, Azure passwords, or GitHub secret values to this file.

## 1. Initial frontend route error

### Error

Next.js reported:

```text
You cannot define a route with the same specificity as a optional catch-all route
("/login" and "/login[[...sign-in]]").
```

### Cause

The frontend contained both a normal `/login` route and Clerk's optional catch-all route:

```text
/login
/login/[[...sign-in]]
```

The same type of conflict existed for signup.

### Fix

Duplicate login/signup routes were removed. The frontend was later migrated away from Clerk to local authentication, so the Clerk catch-all routes are no longer part of the intended authentication flow.

## 2. Repeated login/dashboard redirect loop

### Symptoms

The browser repeatedly navigated between:

```text
/
/dashboard
/login
```

Requests repeatedly returned `200` for `/login` and `/dashboard`, while API authentication failed.

### Root cause

Clerk considered the browser signed in, but the backend `/me` request returned `401`. The frontend and backend therefore disagreed about the authentication state.

### Fix

Clerk frontend and backend usage was removed. Local email/password authentication was implemented:

- JWT token stored as `kasauti_token`
- Backend password hashing uses `hashlib.scrypt`
- Password policy requires at least 7 characters, uppercase, lowercase, digit, and special character
- Local login and signup routes/forms were added
- Auth state now uses the local token and backend API

## 3. Frontend UI and validation work completed

The following work was completed and previously validated:

- Reusable error UI and route/global error boundaries
- Not-found page
- Shimmer loading states
- Redesigned Rates and Dashboard pages
- Redesigned rate cards and price history chart
- Shared modal, cards, buttons, tables, empty states, and form styling
- Backtest and Settings forms converted to modal flows
- Bundled DejaVu Sans font for reliable `₹` rendering in backend banners
- Phone validation rejecting invalid values such as `kumar`
- CORS and API error handling improvements

Validation completed before Azure deployment:

- Backend test suite: `50 passed`
- Frontend TypeScript checks passed
- Frontend production build passed
- Bundled font tests passed

## 4. Azure resource setup

The Azure subscription allowed only selected regions. `uaenorth` was used successfully.

Created resources:

- Resource group: `kasauti-rg`
- ACR: `kasautiacr27103`
- Container Apps environment: `kasauti-container-env`
- Container App: `kasauti-api`

The existing Container Apps environment is an **Express environment**.

Important Express limitation:

```text
System-assigned managed identity is not supported for container apps in Express environments.
```

Attempts to configure system identity produced errors such as:

```text
ExpressRegistrySystemIdentityNotSupported
ExpressSystemAssignedIdentityNotSupported
```

The Azure CLI command to remove the system identity also failed with an internal `KeyError: 'identity'`, because the Express environment does not expose the expected identity configuration.

## 5. ACR Tasks failure

The original deployment approach used `az acr build`, but Azure rejected ACR Tasks:

```text
(TasksOperationsNotAllowed) ACR Tasks requests for the registry
kasautiacr27103 ... are not permitted.
```

### Fix

The GitHub Actions workflow was changed to build the Docker image on the GitHub-hosted runner and push it to ACR:

```text
docker build
docker push
```

The workflow file is:

```text
.github/workflows/deploy-backend.yml
```

## 6. GitHub Actions configuration

The workflow requires these repository secrets:

```text
AZURE_CLIENT_ID
AZURE_TENANT_ID
AZURE_SUBSCRIPTION_ID
```

It requires these repository variables:

```text
AZURE_RESOURCE_GROUP=kasauti-rg
AZURE_ACR_NAME=kasautiacr27103
AZURE_CONTAINER_APP=kasauti-api
```

The GitHub OIDC application is named:

```text
kasauti-github-deploy
```

The service principal must have:

- `Contributor` on resource group `kasauti-rg`
- `AcrPush` on ACR `kasautiacr27103`

## 7. GitHub Actions run history

### Run 1

Failed during the earlier workflow configuration.

### Run 2

Configuration/tests completed successfully after workflow changes.

### Run 3

The workflow completed with `config` and `test` success, but the `deploy` job was skipped because the required secrets/variables were not configured.

### Run 4

The `deploy` job started, but Azure OIDC login failed:

```text
AADSTS700213: No matching federated identity record found for presented assertion subject
```

The subject shown in the GitHub log was:

```text
repo:abhishekk2540@102416622/Kasauti-sahi_bhav-sahi_hisaab@1454234793:ref:refs/heads/main
```

A federated credential was then added for this exact issuer, subject, and audience:

```text
Issuer:
https://token.actions.githubusercontent.com

Audience:
api://AzureADTokenExchange
```

After this, `azure/login@v2` succeeded.

## 8. Container App name/configuration issue

A deployment initially failed with:

```text
The containerapp 'kasauti-api' does not exist
```

The app was later confirmed to exist in `kasauti-rg` and uses:

```text
/subscriptions/.../resourceGroups/kasauti-rg/providers/Microsoft.App/managedEnvironments/kasauti-container-env
```

The GitHub repository variable was checked for leading/trailing whitespace and corrected to:

```text
kasauti-api
```

## 9. Docker image status

The image was successfully built and pushed by GitHub Actions.

The following ACR repository exists:

```text
kasauti-api
```

The following image tag exists:

```text
d7b4b121ec9b0a2f7f885e45d820dc0f9a1f7cc3
```

The current Container App image is also:

```text
kasautiacr27103.azurecr.io/kasauti-api:d7b4b121ec9b0a2f7f885e45d820dc0f9a1f7cc3
```

Therefore, image creation and image push are not the current problem.

## 10. Current deployment failure

GitHub Actions now succeeds through:

```text
azure/login
Build and push image to Azure Container Registry
```

It fails at:

```text
Roll out new revision
```

Exact error:

```text
Failed to provision revision for container app 'kasauti-api'.
BuildFailed: Authentication failed when pulling container image
'kasautiacr27103.azurecr.io/kasauti-api:d7b4b121ec9b0a2f7f885e45d820dc0f9a1f7cc3'.
Provide 'registryCredentials' (username and token) or
'managedIdentityClientId' in your request to authenticate.
```

The smoke test is skipped because the rollout fails first.

## 11. ACR credential investigation

ACR admin access was enabled:

```bash
az acr update \
  --name kasautiacr27103 \
  --admin-enabled true
```

The ACR is Basic SKU:

```text
Managed_Basic
```

The ACR image exists and the admin credentials were tested directly against the registry:

```text
HTTP status: 200
```

The test used:

```bash
curl -u "$ACR_USER:$ACR_PASSWORD" \
  https://kasautiacr27103.azurecr.io/v2/
```

This proves:

- DNS works
- ACR endpoint works
- The image exists
- The ACR admin username/password are valid

However, this command still fails to provision a revision:

```bash
az containerapp registry set \
  --name kasauti-api \
  --resource-group kasauti-rg \
  --server kasautiacr27103.azurecr.io \
  --username "$ACR_USER" \
  --password "$ACR_PASSWORD"
```

It returns:

```text
Updating existing registry.
Failed to provision revision for container app 'kasauti-api'.
BuildFailed: Authentication failed when pulling container image ...
```

Therefore, this is not an ACR password typo. It appears to be a Container Apps Express environment limitation or a failure of the current Container App registry configuration to use ACR admin credentials.

## 12. Anonymous pull attempt

Anonymous pull was considered as a temporary workaround, but Azure rejected it because Basic ACR does not support anonymous pull:

```text
(BadRequest) Anonymous pull is not supported for SKU Managed_Basic.
```

The image must not be made public unless explicitly chosen because anonymous pull exposes the container image publicly.

## 17. Runtime 503 root cause

After switching to the public GHCR image, image pull and port configuration succeeded, but the smoke test returned HTTP `503`.

Container logs showed:

```text
sqlite3.OperationalError: unable to open database file
ERROR: Application startup failed. Exiting.
```

The backend defaults to `sqlite:///./kasauti.db` when `DATABASE_URL` is not configured. The Dockerfile runs the application as the non-root `appuser`, but `/app` was owned by root, so SQLite could not create the database file during the FastAPI lifespan startup.

The Dockerfile was fixed to make `/app` writable by `appuser` before switching users:

```dockerfile
RUN chown -R appuser:appuser /app
```

For production, configure a persistent `DATABASE_URL` (for example Neon PostgreSQL). The container-local SQLite database is writable after this fix but is ephemeral and should not be used for durable production data.

## 13. Current state

### Completed successfully

- Frontend authentication loop fixed
- Duplicate login route fixed
- Local authentication implemented
- Frontend/backend validation and UI improvements completed
- Azure resource group created
- ACR created
- Backend Docker image built
- Backend Docker image pushed to ACR
- GitHub OIDC login fixed
- GitHub `config` job succeeds
- GitHub backend tests succeed
- GitHub deployment job reaches Azure rollout
- ACR credentials independently verified with HTTP 200

### Still failing

The existing Express Container App cannot authenticate while pulling the private ACR image during revision provisioning.

### Not completed

- Secure managed-identity-based image pull
- Successful Azure Container App revision rollout
- Successful `/health` smoke test against the real FastAPI backend
- Frontend deployment to Vercel
- Final production `NEXT_PUBLIC_API_URL` and CORS configuration

## 14. Chosen next direction

The chosen direction is **secure deployment**, not a public image workaround.

The intended secure design is:

1. Create a non-Express Azure Container Apps environment in `uaenorth`.
2. Enable system-assigned managed identity on the new Container App.
3. Assign the `AcrPull` role to that identity on ACR `kasautiacr27103`.
4. Configure the Container App to use the system identity for the ACR registry.
5. Deploy the image from GitHub Actions.
6. Verify:

```text
https://<new-container-app-fqdn>/health
```

Expected response:

```json
{"status":"ok"}
```

The old Express environment and `kasauti-api` app should not be deleted until the secure replacement is running and verified.

## 16. Secure environment attempt result

Two additional environments were created:

- `kasauti-secure-env`
- `kasauti-managed-env`

The second environment was created with:

```bash
--enable-workload-profiles
```

However, both environments still reject managed identity registry authentication with:

```text
ExpressRegistrySystemIdentityNotSupported
System-assigned managed identity for container registry authentication
is not supported for container app ...
```

This confirms that the current Azure subscription/region provisioning path is still producing Express environments. A system-assigned identity cannot be used for ACR image pulls in these environments.

The secure managed-identity deployment is therefore blocked in the current Container Apps setup. The remaining choices are:

1. Use a different Azure region/subscription or a non-Express Container Apps environment that supports managed identity.
2. Deploy using a different Azure service that supports private ACR pulls with managed identity.
3. Use a public image only as a temporary diagnostic workaround, understanding that it exposes the image.

## 15. Important security notes

- Never commit ACR passwords, database URLs, `.env` files, or GitHub secret values.
- Do not paste passwords into chat.
- Do not enable anonymous ACR pull unless accepting a public image is intentional.
- Do not delete the existing Container App until the secure replacement is verified.
- The GitHub Actions workflow currently uses ACR admin login for pushing the image and should eventually use a least-privilege OIDC/service-principal setup where practical.

