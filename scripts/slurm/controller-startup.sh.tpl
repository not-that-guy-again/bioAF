#!/bin/bash
set -euo pipefail

# bioAF SLURM Controller Startup Script
# Rendered by Terraform templatefile()

MUNGE_KEY_SECRET="${munge_key_secret}"
PROJECT_ID="${project_id}"
CONTROLLER_HOSTNAME="${controller_hostname}"
STANDARD_MAX_NODES="${standard_partition_nodes}"
INTERACTIVE_MAX_NODES="${interactive_partition_nodes}"
STANDARD_INSTANCE_TYPE="${standard_instance_type}"
INTERACTIVE_INSTANCE_TYPE="${interactive_instance_type}"

echo "=== bioAF SLURM Controller Setup ==="

# Install SLURM packages
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq slurm-wlm slurmctld slurmdbd munge mariadb-server python3-pip

# Retrieve munge key from Secret Manager
echo "Fetching munge key from Secret Manager..."
gcloud secrets versions access latest --secret="$MUNGE_KEY_SECRET" --project="$PROJECT_ID" | base64 -d > /etc/munge/munge.key
chown munge:munge /etc/munge/munge.key
chmod 400 /etc/munge/munge.key

# Start munge
systemctl enable munge
systemctl start munge

# Configure MariaDB for SLURM accounting
systemctl enable mariadb
systemctl start mariadb
mysql -e "CREATE DATABASE IF NOT EXISTS slurm_acct_db;"
mysql -e "CREATE USER IF NOT EXISTS 'slurm'@'localhost' IDENTIFIED BY 'slurmdbpass';"
mysql -e "GRANT ALL ON slurm_acct_db.* TO 'slurm'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

# Write slurmdbd.conf
cat > /etc/slurm/slurmdbd.conf <<SLURMDBDCONF
AuthType=auth/munge
DbdHost=localhost
DbdPort=6819
SlurmUser=slurm
StorageType=accounting_storage/mysql
StorageHost=localhost
StorageLoc=slurm_acct_db
StorageUser=slurm
StoragePass=slurmdbpass
LogFile=/var/log/slurm/slurmdbd.log
PidFile=/run/slurmdbd.pid
SLURMDBDCONF
chown slurm:slurm /etc/slurm/slurmdbd.conf
chmod 600 /etc/slurm/slurmdbd.conf

# Write slurm.conf
cat > /etc/slurm/slurm.conf <<SLURMCONF
ClusterName=bioaf
SlurmctldHost=$CONTROLLER_HOSTNAME

# Authentication
AuthType=auth/munge
CryptoType=crypto/munge

# Accounting
AccountingStorageType=accounting_storage/slurmdbd
AccountingStorageHost=localhost
AccountingStoragePort=6819
JobAcctGatherType=jobacct_gather/cgroup
JobAcctGatherFrequency=30

# Scheduling
SchedulerType=sched/backfill
SelectType=select/cons_tres
SelectTypeParameters=CR_Core_Memory

# Logging
SlurmctldLogFile=/var/log/slurm/slurmctld.log
SlurmdLogFile=/var/log/slurm/slurmd.log
SlurmctldPidFile=/run/slurmctld.pid
SlurmdPidFile=/run/slurmd.pid

# Process tracking
ProctrackType=proctrack/cgroup
TaskPlugin=task/cgroup

# Suspend/Resume for cloud scaling
SuspendProgram=/usr/local/bin/slurm-suspend.sh
ResumeProgram=/usr/local/bin/slurm-resume.sh
SuspendTime=600
ResumeTimeout=300
TreeWidth=65535

# Partitions
PartitionName=standard Nodes=bioaf-slurm-standard-[0-$((STANDARD_MAX_NODES - 1))] MaxTime=7-00:00:00 Default=YES State=UP
PartitionName=interactive Nodes=bioaf-slurm-interactive-[0-$((INTERACTIVE_MAX_NODES - 1))] MaxTime=1-00:00:00 State=UP

# Node definitions (cloud nodes, initially DOWN)
NodeName=bioaf-slurm-standard-[0-$((STANDARD_MAX_NODES - 1))] State=CLOUD CPUs=8 RealMemory=52000
NodeName=bioaf-slurm-interactive-[0-$((INTERACTIVE_MAX_NODES - 1))] State=CLOUD CPUs=4 RealMemory=15000
SLURMCONF

# Write cgroup.conf
cat > /etc/slurm/cgroup.conf <<CGROUPCONF
CgroupAutomount=yes
ConstrainCores=yes
ConstrainRAMSpace=yes
ConstrainSwapSpace=yes
CGROUPCONF

# Create log directory
mkdir -p /var/log/slurm
chown slurm:slurm /var/log/slurm

# Start slurmdbd first (accounting needs to be available)
systemctl enable slurmdbd
systemctl start slurmdbd
sleep 5

# Create the cluster in accounting
sacctmgr -i add cluster bioaf 2>/dev/null || true
sacctmgr -i add account bioaf-default Description="Default bioAF account" Organization=bioaf 2>/dev/null || true

# Start slurmctld
systemctl enable slurmctld
systemctl start slurmctld

echo "=== bioAF SLURM Controller Setup Complete ==="
