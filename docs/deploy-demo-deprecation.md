# Deploy-Demo Repository Deprecation

## What Changed

As of Phase 23, the bioAF main repository now contains everything needed to
deploy and manage a bioAF instance:

- `docker/docker-compose.yml` - production Docker Compose configuration
- `docker/nginx.conf` - Nginx reverse proxy configuration
- `docker/.env.example` - environment variable template
- `bioaf` - management CLI script (setup, start, stop, logs, etc.)
- `backend/app/cli/create_admin.py` - admin account creation via CLI

## How to Transition

If you are running a deployment from the `bioaf-deploy-demo` repository:

1. Pull the latest bioAF main repo on your server
2. Copy your existing `docker/.env` values into a new `docker/.env` file in
   the bioAF repo (use `docker/.env.example` as a template)
3. Stop the old stack: `docker compose -f docker/docker-compose.poc.yml down`
4. Start the new stack: `./bioaf start`
5. Run migrations: `./bioaf migrate`

Your data is preserved in the `pgdata` Docker volume.

## Deploy-Demo Files (Deprecated)

The following files in the `bioaf-deploy-demo` repository are deprecated:

- `docker/docker-compose.poc.yml` - replaced by `docker/docker-compose.yml`
  in the main repo
- `docker/nginx.poc.conf` - replaced by `docker/nginx.conf` in the main repo
- `docker/.env.example` - replaced by `docker/.env.example` in the main repo
- `scripts/deploy.sh` - replaced by `./bioaf setup`
- `scripts/manage.sh` - replaced by `./bioaf` management script

The deploy-demo repository still contains Terraform modules for VM
provisioning on GCP. Those remain valid and are not affected by this change.
