#!/usr/bin/env bash
# scripts/vm_add_swap.sh — give the VM a swapfile.
#
# WHY THIS EXISTS
# The VM is a 4 GB e2-medium with NO swap. On 2026-08-15 15:02 the kernel
# OOM-killed metatron-server.service (3.6 GB RSS) outright; systemd restarted it
# five seconds later, which is why it looked like nothing had happened. With zero
# swap there is no soft failure mode available to the kernel: the moment memory
# runs out it SIGKILLs the largest process, and the largest process is the server.
#
# Swap does not create memory. It buys the kernel somewhere to put cold pages so
# that a spike degrades into slowness instead of a kill. That is the whole goal.
#
# RUN THIS ON THE VM, NOT THE MAC:
#   gcloud compute ssh metatron-vm --zone=us-central1-a \
#     --project=metatron-ai-499810 --tunnel-through-iap
#   cd ~/multi-model-mcp && sudo bash scripts/vm_add_swap.sh
#
# Idempotent: re-running when swap already exists reports and exits 0.
set -euo pipefail

SWAPFILE=/swapfile
SIZE_MB=2048          # 2 GB. Disk was 4.5 GB free of 20 GB when this was written —
                      # check `df -h /` before raising it.

if [ "$(id -u)" -ne 0 ]; then
  echo "Must run as root: sudo bash $0" >&2
  exit 1
fi

if swapon --show | grep -q .; then
  echo "Swap already active — nothing to do:"
  swapon --show
  exit 0
fi

avail_mb=$(df -m --output=avail / | tail -1 | tr -d ' ')
need_mb=$(( SIZE_MB + 1024 ))     # leave 1 GB of headroom on the root disk
if [ "$avail_mb" -lt "$need_mb" ]; then
  echo "Not enough disk: ${avail_mb}MB free, need ${need_mb}MB. Free space or lower SIZE_MB." >&2
  exit 1
fi

echo "Creating ${SIZE_MB}MB swapfile at ${SWAPFILE}..."
fallocate -l "${SIZE_MB}M" "$SWAPFILE" 2>/dev/null || \
  dd if=/dev/zero of="$SWAPFILE" bs=1M count="$SIZE_MB" status=none
chmod 600 "$SWAPFILE"
mkswap "$SWAPFILE" >/dev/null
swapon "$SWAPFILE"

# Survive reboot. GCE images do not persist swapon across boots on their own.
if ! grep -q "^${SWAPFILE}" /etc/fstab; then
  echo "${SWAPFILE} none swap sw 0 0" >> /etc/fstab
  echo "Added to /etc/fstab so it survives a reboot."
fi

# Prefer reclaiming page cache over swapping app pages; on a server, swapping the
# Python heap out is what makes latency fall off a cliff. 10 keeps swap as an
# emergency valve rather than routine behaviour.
sysctl -w vm.swappiness=10 >/dev/null
grep -q "^vm.swappiness" /etc/sysctl.conf || echo "vm.swappiness=10" >> /etc/sysctl.conf

echo
echo "Done:"
free -m
