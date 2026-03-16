import csv
import io
import logging

logger = logging.getLogger("bioaf.sample_sheet")


def _extract_fastq_paths(sample) -> tuple[str, str]:
    """Extract fastq_1 and fastq_2 GCS URIs from sample.files.

    Sorts files so R1 comes before R2 using the _R1/_R2 filename convention.
    Returns ("", "") if no FASTQ files are linked.
    """
    files = getattr(sample, "files", None) or []
    fastq_files = [f for f in files if getattr(f, "gcs_uri", None)]
    if not fastq_files:
        return ("", "")

    # Sort by filename so R1 < R2
    fastq_files.sort(key=lambda f: getattr(f, "filename", "") or getattr(f, "gcs_uri", ""))

    fastq_1 = fastq_files[0].gcs_uri if len(fastq_files) > 0 else ""
    fastq_2 = fastq_files[1].gcs_uri if len(fastq_files) > 1 else ""
    return (fastq_1, fastq_2)


class SampleSheetService:
    @staticmethod
    def generate_scrnaseq_sheet(samples: list, parameters: dict) -> str:
        """Generate nf-core/scrnaseq sample sheet CSV.

        If samples don't have linked files, falls back to input_paths in parameters.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["sample", "fastq_1", "fastq_2", "expected_cells"])

        input_paths = parameters.get("input_paths", {})

        for sample in samples:
            sample_name = sample.sample_id_external or f"sample_{sample.id}"
            paths = input_paths.get(str(sample.id), [])
            if paths:
                fastq_1 = paths[0] if len(paths) > 0 else ""
                fastq_2 = paths[1] if len(paths) > 1 else ""
            else:
                fastq_1, fastq_2 = _extract_fastq_paths(sample)
            expected_cells = parameters.get("expected_cells", 10000)
            writer.writerow([sample_name, fastq_1, fastq_2, expected_cells])

        return output.getvalue()

    @staticmethod
    def generate_rnaseq_sheet(samples: list, parameters: dict) -> str:
        """Generate nf-core/rnaseq sample sheet CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["sample", "fastq_1", "fastq_2", "strandedness"])

        input_paths = parameters.get("input_paths", {})

        for sample in samples:
            sample_name = sample.sample_id_external or f"sample_{sample.id}"
            paths = input_paths.get(str(sample.id), [])
            if paths:
                fastq_1 = paths[0] if len(paths) > 0 else ""
                fastq_2 = paths[1] if len(paths) > 1 else ""
            else:
                fastq_1, fastq_2 = _extract_fastq_paths(sample)
            strandedness = parameters.get("strandedness", "auto")
            writer.writerow([sample_name, fastq_1, fastq_2, strandedness])

        return output.getvalue()

    @staticmethod
    def generate_generic_sheet(samples: list, parameters: dict) -> str:
        """Generic fallback CSV sample sheet."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["sample", "fastq_1", "fastq_2"])

        input_paths = parameters.get("input_paths", {})

        for sample in samples:
            sample_name = sample.sample_id_external or f"sample_{sample.id}"
            paths = input_paths.get(str(sample.id), [])
            if paths:
                fastq_1 = paths[0] if len(paths) > 0 else ""
                fastq_2 = paths[1] if len(paths) > 1 else ""
            else:
                fastq_1, fastq_2 = _extract_fastq_paths(sample)
            writer.writerow([sample_name, fastq_1, fastq_2])

        return output.getvalue()

    @staticmethod
    def generate_sheet(pipeline_key: str, samples: list, parameters: dict) -> str:
        """Route to the correct sheet generator based on pipeline type."""
        if "scrnaseq" in pipeline_key:
            return SampleSheetService.generate_scrnaseq_sheet(samples, parameters)
        elif "rnaseq" in pipeline_key:
            return SampleSheetService.generate_rnaseq_sheet(samples, parameters)
        else:
            return SampleSheetService.generate_generic_sheet(samples, parameters)
