#!/bin/sh
# Start the SSH server. Host keys live in the data volume, so they stay the same after a
# redeploy (otherwise every visitor would see a scary "host key changed" warning).
set -e

mkdir -p /data/ssh
chmod 700 /data/ssh
[ -f /data/ssh/ssh_host_ed25519_key ] || ssh-keygen -q -t ed25519 -N "" -f /data/ssh/ssh_host_ed25519_key
[ -f /data/ssh/ssh_host_rsa_key ] || ssh-keygen -q -t rsa -b 3072 -N "" -f /data/ssh/ssh_host_rsa_key

# The app runs as "streakr" and must be able to write the database. The ssh folder stays
# root-only, so the app (and anyone using it) can never read the host keys.
chown streakr /data

mkdir -p /run/sshd
exec /usr/sbin/sshd -D -e
