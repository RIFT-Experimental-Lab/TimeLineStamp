#!/data/data/com.termux/files/usr/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
    printf 'Usage: sh enable-ssh.sh /path/to/id_ed25519.pub PHONE_WIFI_IPV4\n' >&2
    exit 2
fi

public_key_file="$1"
wifi_ip="$2"
if [ ! -f "$public_key_file" ]; then
    printf 'Public key not found: %s\n' "$public_key_file" >&2
    exit 1
fi

python - "$public_key_file" "$wifi_ip" <<'PY'
import base64
import binascii
import ipaddress
import sys
from pathlib import Path

key_file, address = sys.argv[1:]
try:
    ip = ipaddress.IPv4Address(address)
except ipaddress.AddressValueError as exc:
    raise SystemExit("Enter a valid phone Wi-Fi IPv4 address") from exc
private_lans = [ipaddress.IPv4Network(network) for network in
                ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
if not any(ip in network for network in private_lans):
    raise SystemExit("Enter the phone's private Wi-Fi IPv4 address")
key = Path(key_file).read_text(encoding="utf-8").strip()
parts = key.split()
if len(parts) < 2 or parts[0] != "ssh-ed25519":
    raise SystemExit("An ssh-ed25519 public key is required")
try:
    decoded = base64.b64decode(parts[1], validate=True)
except (binascii.Error, ValueError) as exc:
    raise SystemExit("Invalid public key") from exc
if len(decoded) != 51:
    raise SystemExit("Invalid Ed25519 public key length")
if "\n" in key or "\r" in key:
    raise SystemExit("The public key must be one line")
PY

if ! command -v sshd >/dev/null 2>&1; then
    pkg install -y openssh
fi
ssh-keygen -lf "$public_key_file" >/dev/null
ssh-keygen -A

umask 077
mkdir -p "$HOME/.ssh" "$HOME/.config/timelinestamp"
chmod 700 "$HOME/.ssh"
authorized="$HOME/.ssh/authorized_keys"
touch "$authorized"
chmod 600 "$authorized"
if ! grep -Fqx "$(cat "$public_key_file")" "$authorized"; then
    printf '\n' >> "$authorized"
    cat "$public_key_file" >> "$authorized"
    printf '\n' >> "$authorized"
fi
cat > "$HOME/.config/timelinestamp/sshd_config.new" <<EOF
Port 8022
AddressFamily inet
ListenAddress $wifi_ip
HostKey ${PREFIX}/etc/ssh/ssh_host_ed25519_key
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
AuthenticationMethods publickey
PermitEmptyPasswords no
AllowAgentForwarding no
AllowTcpForwarding no
X11Forwarding no
PermitTunnel no
Subsystem sftp internal-sftp
EOF
chmod 600 "$HOME/.config/timelinestamp/sshd_config.new"
sshd -t -f "$HOME/.config/timelinestamp/sshd_config.new"
mv "$HOME/.config/timelinestamp/sshd_config.new" "$HOME/.config/timelinestamp/sshd_config"
printf 'TIMELINESTAMP_SSH_BIND=%s\n' "$wifi_ip" > "$HOME/.config/timelinestamp/ssh.env.new"
chmod 600 "$HOME/.config/timelinestamp/ssh.env.new"
mv "$HOME/.config/timelinestamp/ssh.env.new" "$HOME/.config/timelinestamp/ssh.env"
printf 'SSH configured for %s:8022 (public key only).\n' "$wifi_ip"
printf 'Restart the phone, or run the boot script to start SSH.\n'
printf 'Phone SSH user: %s\n' "$(whoami)"
printf 'Phone host key fingerprint:\n'
ssh-keygen -lf "${PREFIX}/etc/ssh/ssh_host_ed25519_key.pub"
