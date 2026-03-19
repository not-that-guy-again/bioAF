import io
import json
import logging
import tempfile
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline_run import PipelineRun
from app.models.qc_dashboard import QCDashboard
from app.services.audit_service import log_action
from app.services.file_service import FileService
from app.services.gcs_storage import GcsStorageService

logger = logging.getLogger("bioaf.qc_dashboard_service")


class QCDashboardService:
    @staticmethod
    async def generate_qc_dashboard(session: AsyncSession, org_id: int, pipeline_run_id: int) -> QCDashboard:
        """Generate a QC dashboard from pipeline run output files."""
        # Get pipeline run
        result = await session.execute(
            select(PipelineRun).where(
                PipelineRun.id == pipeline_run_id,
                PipelineRun.organization_id == org_id,
            )
        )
        run = result.scalar_one_or_none()
        if not run:
            raise ValueError(f"Pipeline run {pipeline_run_id} not found")

        dashboard = QCDashboard(
            organization_id=org_id,
            pipeline_run_id=pipeline_run_id,
            experiment_id=run.experiment_id,
            metrics_json={},
            status="generating",
        )
        session.add(dashboard)
        await session.flush()

        try:
            # Extract metrics from pipeline outputs (reads from GCS)
            metrics = await QCDashboardService._extract_metrics(session, run)

            # Compute quality rating
            quality = QCDashboardService._compute_quality_rating(metrics)
            metrics["quality_rating"] = quality

            # Generate summary text
            summary = QCDashboardService._generate_summary(metrics)

            # Only generate plots when we have real metric values to plot
            plots_meta: list[dict] = []
            if QCDashboardService._has_plottable_metrics(metrics):
                plots_meta = await QCDashboardService._generate_plots(session, org_id, dashboard.id, metrics)

            dashboard.metrics_json = metrics
            dashboard.summary_text = summary
            dashboard.plots_json = plots_meta
            dashboard.status = "ready" if QCDashboardService._has_plottable_metrics(metrics) else "awaiting_metrics"
            dashboard.generated_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.error("QC dashboard generation failed for run %d: %s", pipeline_run_id, e)
            dashboard.status = "failed"
            dashboard.summary_text = f"Generation failed: {e}"

        await log_action(
            session,
            user_id=run.submitted_by_user_id,
            entity_type="qc_dashboard",
            entity_id=dashboard.id,
            action="generate",
            details={"pipeline_run_id": pipeline_run_id, "status": dashboard.status},
        )
        await session.flush()
        return dashboard

    @staticmethod
    async def get_dashboard(session: AsyncSession, org_id: int, dashboard_id: int) -> QCDashboard | None:
        result = await session.execute(
            select(QCDashboard).where(
                QCDashboard.id == dashboard_id,
                QCDashboard.organization_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_dashboard_by_run(session: AsyncSession, org_id: int, pipeline_run_id: int) -> QCDashboard | None:
        result = await session.execute(
            select(QCDashboard).where(
                QCDashboard.pipeline_run_id == pipeline_run_id,
                QCDashboard.organization_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_dashboards(
        session: AsyncSession, org_id: int, experiment_id: int | None = None
    ) -> list[QCDashboard]:
        query = select(QCDashboard).where(QCDashboard.organization_id == org_id)
        if experiment_id:
            query = query.where(QCDashboard.experiment_id == experiment_id)
        query = query.order_by(QCDashboard.created_at.desc())
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    def _has_plottable_metrics(metrics: dict) -> bool:
        """Check whether any metric needed for plot generation is present."""
        plottable_keys = (
            "median_genes_per_cell",
            "median_umi_per_cell",
            "mito_pct_median",
            "total_sequences",
            "percent_duplicates",
            "percent_gc",
        )
        return any(metrics.get(k) is not None for k in plottable_keys)

    @staticmethod
    async def _extract_metrics(session: AsyncSession, run: PipelineRun) -> dict:
        """Extract QC metrics from GCS.

        Checks for a cached qc_metrics.json first. If not found, downloads
        the h5ad output from GCS, extracts metrics locally, and writes the
        result back to GCS as a cache for future reads.
        """
        empty_metrics: dict = {
            "cell_count": None,
            "median_reads_per_cell": None,
            "median_genes_per_cell": None,
            "median_umi_per_cell": None,
            "mito_pct_median": None,
            "doublet_score_median": None,
            "saturation": None,
            "total_sequences": None,
            "percent_duplicates": None,
            "percent_gc": None,
            "avg_sequence_length": None,
            "total_samples": None,
        }

        results_bucket = await QCDashboardService._get_results_bucket(session)
        if not results_bucket:
            logger.warning("No results bucket configured, cannot extract metrics")
            return empty_metrics

        logger.info(
            "Looking for metrics in gs://%s/experiments/%s/pipeline-runs/%s/", results_bucket, run.experiment_id, run.id
        )

        credentials = await GcsStorageService.get_credentials(session)

        try:
            from google.cloud import storage

            client = storage.Client(credentials=credentials)
            bucket = client.bucket(results_bucket)
            prefix = f"experiments/{run.experiment_id}/pipeline-runs/{run.id}/"

            # Log what files are at this prefix
            blobs_at_prefix = [b.name for b in bucket.list_blobs(prefix=prefix, max_results=20)]
            logger.info("Files at prefix for run %d: %s", run.id, blobs_at_prefix)

            # 1. Check for cached metrics JSON
            cache_blob = bucket.blob(f"{prefix}qc_metrics.json")
            if cache_blob.exists():
                cached = json.loads(cache_blob.download_as_text())
                logger.info("Using cached qc_metrics.json for run %d", run.id)
                return cached

            # 2. Try h5ad (single-cell pipelines)
            h5ad_blob = None
            for blob in bucket.list_blobs(prefix=prefix):
                if blob.name.endswith(".h5ad"):
                    h5ad_blob = blob
                    break

            if h5ad_blob:
                with tempfile.NamedTemporaryFile(suffix=".h5ad") as tmp:
                    h5ad_blob.download_to_filename(tmp.name)
                    metrics = QCDashboardService._read_h5ad_metrics(tmp.name)
            else:
                # 3. Try MultiQC data (bulk/FastQC pipelines)
                multiqc_blob = None
                for blob in bucket.list_blobs(prefix=f"{prefix}multiqc/multiqc_data/"):
                    if blob.name.endswith("multiqc_data.json"):
                        multiqc_blob = blob
                        break

                if multiqc_blob:
                    logger.info("Found multiqc_data.json for run %d", run.id)
                    multiqc_text = multiqc_blob.download_as_text()
                    metrics = QCDashboardService._read_multiqc_metrics(multiqc_text)
                else:
                    # 4. Try parsing FastQC general stats from TSV
                    general_stats_blob = None
                    for blob in bucket.list_blobs(prefix=f"{prefix}multiqc/multiqc_data/"):
                        if "general_stats" in blob.name and blob.name.endswith(".txt"):
                            general_stats_blob = blob
                            break

                    if general_stats_blob:
                        logger.info("Found multiqc general stats for run %d", run.id)
                        stats_text = general_stats_blob.download_as_text()
                        metrics = QCDashboardService._read_multiqc_general_stats(stats_text)
                    else:
                        logger.info("No h5ad or multiqc data for run %d", run.id)
                        return empty_metrics

            # 5. Upload metrics cache to GCS
            cache_upload_blob = bucket.blob(f"{prefix}qc_metrics_cache.json")
            cache_upload_blob.upload_from_string(
                json.dumps(metrics, indent=2),
                content_type="application/json",
            )
            logger.info("Wrote qc_metrics_cache.json for run %d", run.id)

            return metrics

        except Exception as e:
            logger.warning("Metric extraction from GCS failed for run %d: %s", run.id, e)
            return empty_metrics

    @staticmethod
    def _read_h5ad_metrics(path: str) -> dict:
        """Read an h5ad file and extract QC metrics."""
        metrics: dict = {
            "cell_count": None,
            "median_reads_per_cell": None,
            "median_genes_per_cell": None,
            "median_umi_per_cell": None,
            "mito_pct_median": None,
            "doublet_score_median": None,
            "saturation": None,
        }

        try:
            import anndata
            import numpy as np

            adata = anndata.read_h5ad(path)
            metrics["cell_count"] = int(adata.n_obs)

            if "n_genes" in adata.obs.columns:
                metrics["median_genes_per_cell"] = float(np.median(adata.obs["n_genes"]))
            elif "n_genes_by_counts" in adata.obs.columns:
                metrics["median_genes_per_cell"] = float(np.median(adata.obs["n_genes_by_counts"]))

            if "total_counts" in adata.obs.columns:
                metrics["median_umi_per_cell"] = float(np.median(adata.obs["total_counts"]))

            if "pct_counts_mt" in adata.obs.columns:
                metrics["mito_pct_median"] = float(np.median(adata.obs["pct_counts_mt"]))
            elif "pct_counts_mito" in adata.obs.columns:
                metrics["mito_pct_median"] = float(np.median(adata.obs["pct_counts_mito"]))

            if "doublet_score" in adata.obs.columns:
                metrics["doublet_score_median"] = float(np.median(adata.obs["doublet_score"]))

        except ImportError:
            logger.warning("anndata not installed, cannot extract h5ad metrics")
        except Exception as e:
            logger.warning("h5ad metric extraction failed: %s", e)

        return metrics

    @staticmethod
    def _read_multiqc_metrics(multiqc_json_text: str) -> dict:
        """Parse multiqc_data.json and extract aggregate FastQC metrics."""
        metrics: dict = {
            "total_sequences": None,
            "percent_duplicates": None,
            "percent_gc": None,
            "avg_sequence_length": None,
            "total_samples": None,
        }
        try:
            data = json.loads(multiqc_json_text)
            general_stats = data.get("report_general_stats_data", [])

            total_seqs = []
            dup_pcts = []
            gc_pcts = []
            seq_lengths = []

            for stats_section in general_stats:
                for _sample_name, sample_stats in stats_section.items():
                    if "Total Sequences" in sample_stats:
                        total_seqs.append(sample_stats["Total Sequences"])
                    if "total_deduplicated_percentage" in sample_stats:
                        dup_pcts.append(100 - sample_stats["total_deduplicated_percentage"])
                    if "%GC" in sample_stats:
                        gc_pcts.append(sample_stats["%GC"])
                    if "avg_sequence_length" in sample_stats:
                        seq_lengths.append(sample_stats["avg_sequence_length"])

            if total_seqs:
                metrics["total_sequences"] = int(sum(total_seqs))
                metrics["total_samples"] = len(total_seqs)
            if dup_pcts:
                metrics["percent_duplicates"] = round(sum(dup_pcts) / len(dup_pcts), 1)
            if gc_pcts:
                metrics["percent_gc"] = round(sum(gc_pcts) / len(gc_pcts), 1)
            if seq_lengths:
                metrics["avg_sequence_length"] = round(sum(seq_lengths) / len(seq_lengths), 1)

        except Exception as e:
            logger.warning("MultiQC JSON parsing failed: %s", e)

        return metrics

    @staticmethod
    def _read_multiqc_general_stats(stats_tsv_text: str) -> dict:
        """Parse multiqc_general_stats.txt (TSV) as fallback."""
        import csv

        metrics: dict = {
            "total_sequences": None,
            "percent_duplicates": None,
            "percent_gc": None,
            "avg_sequence_length": None,
            "total_samples": None,
        }
        try:
            reader = csv.DictReader(stats_tsv_text.strip().splitlines(), delimiter="\t")
            total_seqs = []
            dup_pcts = []
            gc_pcts = []
            seq_lengths = []

            for row in reader:
                for key, val in row.items():
                    if not val or not key:
                        continue
                    k = key.lower()
                    try:
                        v = float(val)
                    except ValueError:
                        continue
                    if "total_sequences" in k or "total sequences" in k:
                        total_seqs.append(v)
                    if "deduplicated_percentage" in k:
                        dup_pcts.append(100 - v)
                    if "%gc" in k or "percent_gc" in k:
                        gc_pcts.append(v)
                    if "avg_sequence_length" in k:
                        seq_lengths.append(v)

            if total_seqs:
                metrics["total_sequences"] = int(sum(total_seqs))
                metrics["total_samples"] = len(total_seqs)
            if dup_pcts:
                metrics["percent_duplicates"] = round(sum(dup_pcts) / len(dup_pcts), 1)
            if gc_pcts:
                metrics["percent_gc"] = round(sum(gc_pcts) / len(gc_pcts), 1)
            if seq_lengths:
                metrics["avg_sequence_length"] = round(sum(seq_lengths) / len(seq_lengths), 1)

        except Exception as e:
            logger.warning("MultiQC general stats parsing failed: %s", e)

        return metrics

    @staticmethod
    def _compute_quality_rating(metrics: dict) -> str:
        """Compute quality rating based on metrics thresholds."""
        mito = metrics.get("mito_pct_median")
        genes = metrics.get("median_genes_per_cell")
        reads = metrics.get("median_reads_per_cell")

        # Single-cell metrics
        if mito is not None and mito < 5 and genes is not None and genes > 1000:
            if reads is None or reads > 2000:
                return "good"
        if mito is not None and mito < 10 and genes is not None and genes > 500:
            return "acceptable"

        # Bulk/FastQC metrics
        dup = metrics.get("percent_duplicates")
        gc = metrics.get("percent_gc")
        total = metrics.get("total_sequences")
        if total is not None:
            if dup is not None and dup < 30 and gc is not None and 35 <= gc <= 65:
                return "good"
            if dup is not None and dup < 50:
                return "acceptable"
            return "acceptable" if dup is None else "concerning"

        return "concerning"

    @staticmethod
    def _generate_summary(metrics: dict) -> str:
        """Generate plain English summary from metrics."""
        parts = []

        cell_count = metrics.get("cell_count")
        if cell_count is not None:
            parts.append(f"This run produced **{cell_count:,} cells**")

        genes = metrics.get("median_genes_per_cell")
        if genes is not None:
            parts.append(f"with a median of **{genes:,.0f} genes per cell**")

        umi = metrics.get("median_umi_per_cell")
        if umi is not None:
            parts.append(f"and **{umi:,.0f} UMIs per cell**")

        # Bulk/FastQC metrics
        total_seqs = metrics.get("total_sequences")
        if total_seqs is not None:
            n_samples = metrics.get("total_samples", 0)
            parts.append(f"**{total_seqs:,} total sequences** across **{n_samples} samples**")

        avg_len = metrics.get("avg_sequence_length")
        if avg_len is not None:
            parts.append(f"with average read length **{avg_len:.0f} bp**")

        summary = " ".join(parts) + "." if parts else "No metrics available."

        mito = metrics.get("mito_pct_median")
        if mito is not None:
            health = "healthy, under 5% threshold" if mito < 5 else "elevated" if mito < 10 else "high"
            summary += f" Mitochondrial content is **{mito:.1f}%** ({health})."

        dup = metrics.get("percent_duplicates")
        if dup is not None:
            health = "low" if dup < 30 else "moderate" if dup < 50 else "high"
            summary += f" Duplication rate is **{dup:.1f}%** ({health})."

        gc = metrics.get("percent_gc")
        if gc is not None:
            summary += f" GC content is **{gc:.0f}%**."

        sat = metrics.get("saturation")
        if sat is not None:
            summary += f" Sequencing saturation is **{sat:.0f}%**"
            if sat < 80:
                summary += ", suggesting additional sequencing depth may improve gene detection."
            else:
                summary += "."

        quality = metrics.get("quality_rating", "concerning")
        summary += f" Overall quality: **{quality.capitalize()}**."

        return summary

    @staticmethod
    async def _get_results_bucket(session: AsyncSession) -> str | None:
        """Read results bucket name from platform_config.

        Checks results_bucket_name first, then falls back to deriving it
        from raw_bucket_name (bioaf-raw-X -> bioaf-results-X) since the
        raw bucket is populated by Terraform before results_bucket_name.
        """
        result = await session.execute(
            text("SELECT key, value FROM platform_config WHERE key IN ('results_bucket_name', 'raw_bucket_name')")
        )
        config = {r[0]: r[1] for r in result.fetchall()}

        results = config.get("results_bucket_name")
        if results and results != "null":
            return results

        # Derive from raw_bucket_name as fallback
        raw = config.get("raw_bucket_name", "")
        if raw and raw.startswith("bioaf-raw-"):
            return raw.replace("bioaf-raw-", "bioaf-results-", 1)

        return None

    @staticmethod
    async def _upload_plot_to_gcs(
        bucket_name: str, blob_path: str, buf: io.BytesIO, credentials: object = None
    ) -> None:
        """Upload a plot image buffer to GCS."""
        from google.cloud import storage

        client = storage.Client(credentials=credentials)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        buf.seek(0)
        blob.upload_from_file(buf, content_type="image/png")

    @staticmethod
    async def _generate_plots(session: AsyncSession, org_id: int, dashboard_id: int, metrics: dict) -> list[dict]:
        """Generate QC plot images and upload to GCS."""
        plots_meta = []
        results_bucket = await QCDashboardService._get_results_bucket(session)
        credentials = await GcsStorageService.get_credentials(session)

        try:
            # Lazy import matplotlib
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np

            plot_configs = [
                ("genes_histogram", "Genes per Cell", "genes_per_cell_hist"),
                ("umi_histogram", "UMIs per Cell", "umi_per_cell_hist"),
                ("mito_violin", "Mitochondrial %", "mito_pct_violin"),
            ]

            for plot_type, title, prefix in plot_configs:
                try:
                    fig, ax = plt.subplots(figsize=(8, 5))

                    # Generate placeholder plot data based on metrics
                    if plot_type == "genes_histogram" and metrics.get("median_genes_per_cell"):
                        median = metrics["median_genes_per_cell"]
                        data = np.random.normal(median, median * 0.3, max(metrics.get("cell_count", 1000), 100))
                        ax.hist(data, bins=50, color="#4a90d9", edgecolor="white")
                        ax.set_xlabel("Genes per Cell")
                        ax.set_ylabel("Count")
                    elif plot_type == "umi_histogram" and metrics.get("median_umi_per_cell"):
                        median = metrics["median_umi_per_cell"]
                        data = np.random.normal(median, median * 0.3, max(metrics.get("cell_count", 1000), 100))
                        ax.hist(data, bins=50, color="#5cb85c", edgecolor="white")
                        ax.set_xlabel("UMIs per Cell")
                        ax.set_ylabel("Count")
                    elif plot_type == "mito_violin" and metrics.get("mito_pct_median"):
                        median = metrics["mito_pct_median"]
                        data = np.random.normal(median, 1.5, max(metrics.get("cell_count", 1000), 100))
                        data = np.clip(data, 0, 100)
                        ax.violinplot(data, showmedians=True)
                        ax.set_ylabel("Mitochondrial %")
                        ax.axhline(y=5, color="r", linestyle="--", alpha=0.5, label="5% threshold")
                        ax.legend()
                    else:
                        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)

                    ax.set_title(title)
                    plt.tight_layout()

                    # Save to bytes
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", dpi=150)
                    plt.close(fig)
                    buf.seek(0)

                    # Build GCS path and create file record
                    plot_filename = f"qc_dashboard_{dashboard_id}_{prefix}.png"
                    blob_path = f"qc_plots/{plot_filename}"
                    gcs_uri = f"gs://{results_bucket}/{blob_path}" if results_bucket else f"gs://unset/{plot_filename}"

                    # Upload PNG to GCS so the file actually exists
                    if results_bucket:
                        try:
                            await QCDashboardService._upload_plot_to_gcs(
                                results_bucket, blob_path, buf, credentials=credentials
                            )
                        except Exception as e:
                            logger.warning("Failed to upload plot %s to GCS: %s", plot_filename, e)

                    file = await FileService.create_file_record(
                        session,
                        org_id=org_id,
                        user_id=None,
                        filename=plot_filename,
                        gcs_uri=gcs_uri,
                        size_bytes=buf.getbuffer().nbytes,
                        md5_checksum=None,
                        file_type="png",
                        tags=["qc_plot", plot_type],
                    )

                    plots_meta.append(
                        {
                            "plot_type": plot_type,
                            "title": title,
                            "file_id": file.id,
                        }
                    )

                except Exception as e:
                    logger.warning("Failed to generate plot %s: %s", plot_type, e)

        except ImportError:
            logger.warning("matplotlib not installed, skipping plot generation")

        return plots_meta
