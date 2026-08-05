# StreamForge Proxmox Installation

Milestone 1 uses Docker Compose as the canonical deployment method. This guide targets a Proxmox VE host running an unprivileged Debian LXC when possible.

## Recommended LXC Shape

- Debian 13 or current stable Debian template.
- Unprivileged container.
- Static DHCP lease or reserved IP address.
- Persistent storage mounted for PostgreSQL, Redis, and uploaded playlist volumes.
- Optional future mounts for recordings, timeshift buffers, logos, and backups.

## Host Preparation

Do not run unsafe `curl | bash` installers for Milestone 1. Install Docker Engine and Docker Compose using the official distribution packages or your normal Proxmox administration process.

## Application Deployment

1. Copy the repository into the LXC.
2. Create an environment file from `.env.example`.
3. Set a strong `STREAMFORGE_SECRET_KEY`.
4. Start the stack with `make dev`.
5. Run migrations with `make migrate`.
6. Open the dashboard and complete first-run setup.
7. Add an authorized M3U URL, upload a synthetic M3U file, or create the built-in synthetic demo source from the Sources page.

## Persistent Data

The Compose file uses named volumes for database, Redis, and uploaded playlist state so container restarts do not erase Milestone 1 or Milestone 2 data.

Future milestones will add external media storage mounts for recordings and timeshift buffers. Recording media must live outside the application container.

## Reverse Proxy

Caddy or NGINX should terminate TLS and forward dashboard and API traffic to the container services. Reverse-proxy examples are deferred until external access and production hardening are implemented.

## Operational Notes

- Keep the LXC firewall restrictive.
- Restrict dashboard access to trusted networks until remote-access mode is fully implemented.
- Back up database volumes before upgrades.
- Do not place provider playlists, credentials, or recordings in version control.
