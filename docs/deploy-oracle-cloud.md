# Deploy to Oracle Cloud Free

Goal: the API and UI run on a free ARM VM, and the database is a free Autonomous Database. Cost: $0 if you stay inside the Always Free limits.

> Oracle changes free-tier rules from time to time (in June 2026 it cut the free ARM VM to 2 CPUs / 12 GB). Check the current limits on Oracle's Free Tier page before you start.

## 1. Sign up

1. Go to the Oracle Cloud Free Tier page and create an account. Oracle asks for a card to verify you; Always Free resources are not charged.
2. **Pick your home region carefully.** You can't change it later, and free ARM VMs are sometimes "out of capacity" in busy regions. A US West region (San Jose or Phoenix) is fine for Long Beach.

## 2. Create the Autonomous Database

1. Menu → **Oracle Database → Autonomous Database → Create**.
2. Workload: **Transaction Processing**. Turn on **Always Free**.
3. Set a strong **ADMIN** password and save it in your password manager.
4. Network access: **Secure access from allowed IPs and VCNs only**. Add your laptop's public IP now, and the VM IP after step 3.
5. Untick **Require mutual TLS (mTLS) authentication**. This lets the app connect with TLS and no wallet file.
6. When it is ready: **Database connection** → TLS → copy the connection string for the **`_low`** service.

Create the app user (Database Actions → SQL, logged in as ADMIN):

```sql
CREATE USER claimshub IDENTIFIED BY "Use-A-Long-Password-1";
GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE, CREATE PROCEDURE, CREATE JOB TO claimshub;
ALTER USER claimshub QUOTA 1G ON DATA;
```

The app never uses ADMIN. It only has the grants it needs.

## 3. Create the VM

1. Menu → **Compute → Instances → Create**.
2. Image: **Canonical Ubuntu 24.04**. Shape: **VM.Standard.A1.Flex**, 2 OCPU, 12 GB (Always Free).
3. Add your SSH public key (`cat ~/.ssh/id_ed25519.pub`) and keep **Assign a public IPv4 address** on.
4. Open ports 80 and 443:
   - Networking → your VCN → Security List → **Add Ingress Rules**: source `0.0.0.0/0`, TCP, ports `80,443`.
   - Oracle's Ubuntu image also blocks ports in iptables. On the VM:
     ```bash
     sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
     sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
     sudo netfilter-persistent save
     ```
5. Add the VM's public IP to the database's allowed IPs (step 2.4).

## 4. Install Docker and the app on the VM

```bash
ssh ubuntu@<vm-ip>
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && exit     # log in again so the group applies
ssh ubuntu@<vm-ip>
git clone https://github.com/jeevanreddy492/ClaimsHub.git && cd ClaimsHub
cp .env.example .env && nano .env
```

Set these in `.env`:

```bash
CLAIMSHUB_DATABASE_URL=oracle+oracledb://CLAIMSHUB:<app password>@
CLAIMSHUB_DATABASE_DSN=<the _low TLS connection string from step 2.6>
CLAIMSHUB_JWT_SECRET=<openssl rand -hex 32>
SITE_ADDRESS=<your domain, or :80 to use the IP with plain HTTP>
```

**Free HTTPS:** get a free subdomain at duckdns.org, point it at the VM IP and set `SITE_ADDRESS=yourname.duckdns.org`. Caddy gets a Let's Encrypt certificate by itself.

## 5. First release

```bash
git tag v0.1.0 && git push origin v0.1.0          # on your laptop
./deploy/release.sh v0.1.0                         # on the VM
docker compose -f deploy/docker-compose.prod.yml --env-file .env run --rm api python -m scripts.seed --claims 300
```

Open `https://<your domain>` and log in as `supervisor1`.

**Before you share the link:** change the demo passwords, or remove the demo users.

## 6. Automatic deploys (optional)

In GitHub → Settings → Secrets → Actions add `VM_HOST`, `VM_USER` (`ubuntu`) and `VM_SSH_KEY` (a private key that can log in to the VM). After that, pushing a `v*` tag runs `.github/workflows/deploy.yml`, which calls `deploy/release.sh` on the VM.

## Keep it free and alive

- Oracle can reclaim Always Free VMs that stay idle, and it stops Always Free databases after a period without use. Check Oracle's current rules. A small cron `curl` to `/health/ready` every 15 minutes keeps both in use.
- Logs rotate (5 × 20 MB per container), so the disk will not fill up.
- Set a **budget alert at $1** in Billing → Budgets, just in case.
