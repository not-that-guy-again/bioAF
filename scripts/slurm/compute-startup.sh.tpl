#!/bin/bash
set -euo pipefail

# bioAF SLURM Compute Node Startup Script
# Rendered by Terraform templatefile()

MUNGE_KEY_SECRET="${munge_key_secret}"
PROJECT_ID="${project_id}"
CONTROLLER_HOSTNAME="${controller_hostname}"
FILESTORE_IP="${filestore_ip}"
RAW_BUCKET="${raw_bucket}"
WORKING_BUCKET="${working_bucket}"
RESULTS_BUCKET="${results_bucket}"

echo "=== bioAF SLURM Compute Node Setup ==="

# Install packages
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq slurmd munge nfs-common gcsfuse

# Retrieve munge key from Secret Manager
echo "Fetching munge key from Secret Manager..."
gcloud secrets versions access latest --secret="$MUNGE_KEY_SECRET" --project="$PROJECT_ID" | base64 -d > /etc/munge/munge.key
chown munge:munge /etc/munge/munge.key
chmod 400 /etc/munge/munge.key

# Start munge
systemctl enable munge
systemctl start munge

# Write slurm.conf (client config pointing to controller)
cat > /etc/slurm/slurm.conf <<SLURMCONF
ClusterName=bioaf
SlurmctldHost=$CONTROLLER_HOSTNAME
AuthType=auth/munge
ProctrackType=proctrack/cgroup
TaskPlugin=task/cgroup
SLURMCONF

# Write cgroup.conf
cat > /etc/slurm/cgroup.conf <<CGROUPCONF
CgroupAutomount=yes
ConstrainCores=yes
ConstrainRAMSpace=yes
ConstrainSwapSpace=yes
CGROUPCONF

# Mount Filestore NFS
echo "Mounting Filestore NFS..."
mkdir -p /shared
mount -o rw,hard,timeo=600,retrans=3 "$FILESTORE_IP:/bioaf_shared" /shared
echo "$FILESTORE_IP:/bioaf_shared /shared nfs rw,hard,timeo=600,retrans=3 0 0" >> /etc/fstab

# Mount GCS buckets via gcsfuse
echo "Mounting GCS buckets..."
mkdir -p /data/raw /data/working /data/results
gcsfuse --implicit-dirs "$RAW_BUCKET" /data/raw
gcsfuse --implicit-dirs "$WORKING_BUCKET" /data/working
gcsfuse --implicit-dirs "$RESULTS_BUCKET" /data/results

# Sync conda environments from shared path
if [ -d /shared/miniconda3 ]; then
    ln -sf /shared/miniconda3 /opt/miniconda3
    export PATH="/opt/miniconda3/bin:$PATH"
fi

# Create log directory
mkdir -p /var/log/slurm
chown slurm:slurm /var/log/slurm

# Start slurmd
systemctl enable slurmd
systemctl start slurmd

echo "=== bioAF SLURM Compute Node Setup Complete ==="
