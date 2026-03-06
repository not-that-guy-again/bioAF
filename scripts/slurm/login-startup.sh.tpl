#!/bin/bash
set -euo pipefail

# bioAF SLURM Login Node Startup Script
# Rendered by Terraform templatefile()

MUNGE_KEY_SECRET="${munge_key_secret}"
PROJECT_ID="${project_id}"
CONTROLLER_HOSTNAME="${controller_hostname}"
FILESTORE_IP="${filestore_ip}"
RAW_BUCKET="${raw_bucket}"
WORKING_BUCKET="${working_bucket}"
RESULTS_BUCKET="${results_bucket}"

echo "=== bioAF SLURM Login Node Setup ==="

# Install packages
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq slurm-client munge nfs-common gcsfuse \
    python3-pip python3-venv wget curl git singularity-container

# Retrieve munge key from Secret Manager
echo "Fetching munge key from Secret Manager..."
gcloud secrets versions access latest --secret="$MUNGE_KEY_SECRET" --project="$PROJECT_ID" | base64 -d > /etc/munge/munge.key
chown munge:munge /etc/munge/munge.key
chmod 400 /etc/munge/munge.key

# Start munge
systemctl enable munge
systemctl start munge

# Copy slurm.conf from controller (assumed shared via NFS or pre-baked)
# For now, write a client-compatible slurm.conf pointing to the controller
cat > /etc/slurm/slurm.conf <<SLURMCONF
ClusterName=bioaf
SlurmctldHost=$CONTROLLER_HOSTNAME
AuthType=auth/munge
SLURMCONF

# Mount Filestore NFS
echo "Mounting Filestore NFS..."
mkdir -p /home /shared
mount -o rw,hard,timeo=600,retrans=3 "$FILESTORE_IP:/bioaf_shared" /shared
echo "$FILESTORE_IP:/bioaf_shared /shared nfs rw,hard,timeo=600,retrans=3 0 0" >> /etc/fstab

# Mount GCS buckets via gcsfuse
echo "Mounting GCS buckets..."
mkdir -p /data/raw /data/working /data/results
gcsfuse --implicit-dirs "$RAW_BUCKET" /data/raw
gcsfuse --implicit-dirs "$WORKING_BUCKET" /data/working
gcsfuse --implicit-dirs "$RESULTS_BUCKET" /data/results

# Install Miniconda
if [ ! -d /opt/miniconda3 ]; then
    echo "Installing Miniconda..."
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
    bash /tmp/miniconda.sh -b -p /opt/miniconda3
    rm /tmp/miniconda.sh
fi
export PATH="/opt/miniconda3/bin:$PATH"

# Install bioaf-scrna conda environment
if [ ! -d /opt/miniconda3/envs/bioaf-scrna ]; then
    echo "Creating bioaf-scrna conda environment..."
    if [ -f /shared/environments/bioaf-scrna.yml ]; then
        conda env create -f /shared/environments/bioaf-scrna.yml
    fi
fi

# Install R and Bioconductor packages
echo "Installing R..."
apt-get install -y -qq r-base r-base-dev libcurl4-openssl-dev libssl-dev libxml2-dev
if [ -f /shared/environments/r-bioaf.R ]; then
    Rscript /shared/environments/r-bioaf.R
fi

# Install Nextflow
if [ ! -f /usr/local/bin/nextflow ]; then
    echo "Installing Nextflow..."
    curl -s https://get.nextflow.io | bash
    mv nextflow /usr/local/bin/
fi

# Install Snakemake
pip3 install --quiet snakemake

echo "=== bioAF SLURM Login Node Setup Complete ==="
