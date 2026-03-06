import csv
import io
import logging

logger = logging.getLogger("bioaf.sample_sheet")


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
            fastq_1 = paths[0] if len(paths) > 0 else ""
            fastq_2 = paths[1] if len(paths) > 1 else ""
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
            fastq_1 = paths[0] if len(paths) > 0 else ""
            fastq_2 = paths[1] if len(paths) > 1 else ""
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
            fastq_1 = paths[0] if len(paths) > 0 else ""
            fastq_2 = paths[1] if len(paths) > 1 else ""
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
