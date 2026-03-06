# Computational Biologist User Guide

This guide covers the bioAF workflow for computational biologists who run pipelines, manage notebooks, and analyze data.

## Getting Started

Log in with your credentials. Your account has the **comp_bio** role, giving you access to pipelines, notebooks, packages, and environments.

## Pipeline Catalog

Navigate to **Pipeline Catalog** to browse available pipelines:
- **nf-core/scrnaseq** - Single-cell RNA-seq processing
- **nf-core/rnaseq** - Bulk RNA-seq alignment and quantification
- **nf-core/atacseq** - ATAC-seq analysis
- Custom pipelines added by your admin

Each pipeline shows its description, required inputs, and default parameters.

## Running Pipelines

1. Select a pipeline from the catalog
2. Click **Launch**
3. Configure parameters:
   - Select the experiment and samples
   - Set compute resources (CPUs, memory)
   - Override default parameters as needed
4. Click **Submit**

Monitor runs from **Pipeline Runs**:
- View real-time progress and logs
- See per-stage completion status
- Access output files when complete

## Notebook Sessions

Navigate to **Compute** to manage notebook sessions:

1. Click **Launch Notebook**
2. Select environment type: JupyterHub or RStudio
3. Choose compute resources
4. Select a software environment (conda/pip/CRAN packages)

Sessions auto-stop after idle timeout (configurable). You'll receive a notification when a session is about to stop.

## Packages and Environments

### Packages (Sidebar > Packages)

Browse and search installed packages across conda, pip, CRAN, and Bioconductor channels. View version details and dependencies.

### Environments (Sidebar > Environments)

Manage reproducible software environments:
- Create new environments with specific package versions
- Clone existing environments
- Export environment definitions (environment.yml, requirements.txt)
- Environments are shared across the team

## Data Management

Navigate to **Data** for file management:
- Browse uploaded files and pipeline outputs
- Download individual files or datasets
- Organize files by experiment and project

## Results and Visualization

From **Results**:
- View QC dashboards with quality metrics per pipeline run
- Launch cellxgene for interactive single-cell exploration
- Browse publication-quality plots
- Search across all results with the global search

## Notebook Templates

Access pre-configured analysis templates from **Templates**:
- Standard analysis workflows
- Customizable parameters
- Auto-populated with your experiment data

## Tips

- Use the **Home** dashboard to see active pipeline runs and notebook sessions
- Check **Activity Feed** for team-wide events
- Set notification preferences for pipeline completions and failures
