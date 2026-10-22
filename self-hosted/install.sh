#!/usr/bin/env bash
set -euo pipefail
fot_domain=fot-manager-training.ru
fot_base=/opt/fot-manager-training
fot_data=/var/lib/fot-manager-training
fot_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ${EUID:-$(id -u)} != 0 ]]; then echo 'Run this installer as root on the target server.' >&2; exit 1; fi

# A raw downloaded installer fetches the exact repository revision supplied by the caller.
if [[ ! -f "$fot_script_dir/server.py" ]]; then
    fot_temp="$(mktemp -d)"
    trap 'rm -rf -- "$fot_temp"' EXIT
    fot_ref="${FOT_SOURCE_REF:-main}"
    if [[ ! "$fot_ref" =~ ^([a-fA-F0-9]{40}|main)$ ]]; then echo 'Invalid source revision.' >&2; exit 1; fi
    curl --fail --show-error --silent --location "https://api.github.com/repos/ekaterinashliakhova/fot-manager-training/tarball/$fot_ref" -o "$fot_temp/source.tar.gz"
    mkdir "$fot_temp/repository"
    tar -xzf "$fot_temp/source.tar.gz" -C "$fot_temp/repository" --strip-components=1
    bash "$fot_temp/repository/self-hosted/install.sh"
    exit
fi
if [[ ! -f /etc/os-release ]]; then echo 'Supported systems: Debian or Ubuntu with systemd.' >&2; exit 1; fi
. /etc/os-release
if [[ ${ID:-} != debian && ${ID:-} != ubuntu ]]; then echo 'Supported systems: Debian or Ubuntu with systemd.' >&2; exit 1; fi
command -v systemctl >/dev/null
if command -v ss >/dev/null && ss -H -ltnp '( sport = :80 or sport = :443 )' | grep -q .; then
    if ! systemctl is-active --quiet nginx; then
        echo 'Ports 80/443 are already used by another web server. Nothing has been changed.' >&2
        echo 'Use the supplied public/ files and reverse-proxy configuration with the existing server.' >&2
        exit 1
    fi
fi
if command -v ss >/dev/null && [[ -n "$(ss -H -ltn '( sport = :8766 )')" ]] && ! systemctl is-active --quiet fot-manager-training.service; then
    echo 'Loopback port 8766 is already in use. Nothing has been changed.' >&2; exit 1
fi
# Never replace another site's explicitly configured virtual host.
if [[ -d /etc/nginx ]]; then
    fot_conflict="$(python3 - <<'PY'
from pathlib import Path
import re
own=Path('/etc/nginx/sites-available/fot-manager-training.ru')
for directory in ['/etc/nginx/sites-enabled','/etc/nginx/conf.d']:
 for file in Path(directory).glob('*'):
  if not file.is_file() or file.resolve()==own:continue
  text=re.sub(r'#.*','',file.read_text(errors='replace'))
  if any('fot-manager-training.ru' in line.split() or 'www.fot-manager-training.ru' in line.split() for line in re.findall(r'server_name\s+([^;]+);',text)):
   print(file)
PY
)"
    if [[ -n "$fot_conflict" ]]; then
        echo 'This domain already has an explicit configuration. Nothing has been changed:' >&2
        echo "$fot_conflict" >&2
        echo 'Back up and adapt that virtual host using self-hosted/nginx.conf before continuing.' >&2
        exit 1
    fi
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends nginx python3 certbot python3-certbot-nginx curl
fot_stamp="$(date -u +%Y%m%dT%H%M%SZ)-$$"
fot_release="$fot_base/releases/$fot_stamp"
fot_backup="/var/backups/fot-manager-training/$fot_stamp"
mkdir -p "$fot_release" "$fot_backup" "$fot_data" /var/www/letsencrypt
if [[ -e "$fot_base/current" && ! -L "$fot_base/current" ]]; then echo 'current exists and is not a symlink; refusing to overwrite it.' >&2; exit 1; fi
fot_previous="$(readlink -f "$fot_base/current" 2>/dev/null || true)"
[[ -f /etc/nginx/sites-available/fot-manager-training.ru ]] && cp -a /etc/nginx/sites-available/fot-manager-training.ru "$fot_backup/nginx.conf"
[[ -f /etc/systemd/system/fot-manager-training.service ]] && cp -a /etc/systemd/system/fot-manager-training.service "$fot_backup/service.conf"
if [[ -f "$fot_data/completions.sqlite3" ]]; then
    FOT_BACKUP_DIR="$fot_backup" python3 - <<'PY'
import os,sqlite3
from pathlib import Path
with sqlite3.connect('/var/lib/fot-manager-training/completions.sqlite3') as source:
 with sqlite3.connect(Path(os.environ['FOT_BACKUP_DIR'])/'completions.sqlite3') as target:source.backup(target)
PY
fi
cp "$fot_script_dir/server.py" "$fot_release/server.py"
if [[ -d "$fot_script_dir/public" && -f "$fot_script_dir/cases.json" ]]; then
    cp -a "$fot_script_dir/public" "$fot_release/public"
    cp "$fot_script_dir/cases.json" "$fot_release/cases.json"
else
    python3 "$fot_script_dir/build.py" --source "$fot_script_dir/../dist" --output "$fot_release"
fi
chmod -R u=rwX,go=rX "$fot_release"
if ! id -u fottraining >/dev/null 2>&1; then useradd --system --user-group --home-dir "$fot_data" --shell /usr/sbin/nologin fottraining; fi
chown -R fottraining:fottraining "$fot_data"
chmod 750 "$fot_data"
ln -s "$fot_release" "$fot_base/current.next"
mv -Tf "$fot_base/current.next" "$fot_base/current"
install -m 644 "$fot_script_dir/fot-manager-training.service" /etc/systemd/system/fot-manager-training.service
systemctl daemon-reload
systemctl enable fot-manager-training.service
systemctl restart fot-manager-training.service
fot_ready=0
for fot_attempt in $(seq 1 20); do
    if curl --fail --silent http://127.0.0.1:8766/api/health | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('ready') and d.get('mode')=='training-without-ai' else 1)" 2>/dev/null; then fot_ready=1; break; fi
    sleep 1
done
if [[ "$fot_ready" != 1 ]]; then
    if [[ -n "$fot_previous" && -d "$fot_previous" ]]; then ln -s "$fot_previous" "$fot_base/current.next"; mv -Tf "$fot_base/current.next" "$fot_base/current"; systemctl restart fot-manager-training.service || true; fi
    echo 'Backend did not start. Check: journalctl -u fot-manager-training -n 50' >&2
    exit 1
fi
mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
# Keep an existing HTTPS configuration on repeat installs. Certbot owns its TLS blocks.
fot_nginx_written=0
fot_nginx_link_added=0
if [[ ! -f /etc/nginx/sites-available/fot-manager-training.ru ]]; then
    fot_nginx_written=1
    install -m 644 "$fot_script_dir/nginx.conf" /etc/nginx/sites-available/fot-manager-training.ru
fi
if [[ ! -e /etc/nginx/sites-enabled/fot-manager-training.ru ]]; then ln -s /etc/nginx/sites-available/fot-manager-training.ru /etc/nginx/sites-enabled/fot-manager-training.ru; fot_nginx_link_added=1; fi
if ! nginx -t; then
    [[ $fot_nginx_link_added == 1 ]] && rm /etc/nginx/sites-enabled/fot-manager-training.ru
    [[ $fot_nginx_written == 1 ]] && rm /etc/nginx/sites-available/fot-manager-training.ru
    echo 'Nginx configuration check failed; newly added virtual host was removed.' >&2
    exit 1
fi
systemctl enable nginx
systemctl reload-or-restart nginx
if command -v ufw >/dev/null && ufw status | grep -q '^Status: active'; then ufw allow 80/tcp; ufw allow 443/tcp; fi
fot_cert_args=(--register-unsafely-without-email)
if [[ -n "${FOT_CERT_EMAIL:-}" ]]; then fot_cert_args=(--email "$FOT_CERT_EMAIL"); fi
if ! certbot --nginx --non-interactive --agree-tos "${fot_cert_args[@]}" --redirect -d "$fot_domain" -d "www.$fot_domain"; then
    echo 'The training is installed, but automatic HTTPS setup failed. Existing sites were not disabled.' >&2
    echo 'Check DNS/ports 80 and 443, then run certbot --nginx for this domain.' >&2
    exit 1
fi
systemctl enable --now certbot.timer
printf '\nReady: https://%s/\n' "$fot_domain"
printf 'No AI/chatbot is installed. Statistics are stored in %s/completions.sqlite3\n' "$fot_data"
printf 'Previous project release: %s\nConfiguration backups: %s\n' "${fot_previous:-none}" "$fot_backup"
