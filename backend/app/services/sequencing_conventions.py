"""Sequencer-model conventions used to infer defaults for Libraries.

`infer_i5_orientation` maps a raw `instrument_model` string (as recorded on
`SequencingBatch.instrument_model`) to the i5 orientation convention that
the sequencer's demultiplexer expects.

Conventions follow Illumina's published guidance — NovaSeq, NextSeq, iSeq,
and HiSeq 3000/4000 use reverse_complement i5; MiSeq and HiSeq 2500/2000
use forward i5. Unknown models return ``None`` so the caller can preserve
the null value.
"""

from __future__ import annotations


_REVERSE_COMPLEMENT_PREFIXES = (
    "novaseq",
    "nextseq",
    "iseq",
    "hiseq 3",
    "hiseq 4",
)

_FORWARD_PREFIXES = (
    "miseq",
    "hiseq 2",
    "hiseq 1",
    "hiseq",  # bare "HiSeq" with no numeric suffix defaults to forward
)


def infer_i5_orientation(instrument_model: str | None) -> str | None:
    """Return "forward" or "reverse_complement" or None for unknown models."""
    if not instrument_model:
        return None
    needle = instrument_model.strip().lower()
    for prefix in _REVERSE_COMPLEMENT_PREFIXES:
        if needle.startswith(prefix):
            return "reverse_complement"
    for prefix in _FORWARD_PREFIXES:
        if needle.startswith(prefix):
            return "forward"
    return None


# Expected cross-library contamination from index hopping, by sequencer model.
# Patterned flow cells (NovaSeq, NextSeq 2000) misassign a small percentage of
# reads across libraries on the same lane; non-patterned machines are lower.
# Values are percentages (0.5 == 0.5%).
_CONTAMINATION_BY_PREFIX: list[tuple[str, str]] = [
    ("nextseq 2", "1.000"),
    ("nextseq 1", "1.000"),
    ("novaseq", "0.500"),
    ("hiseq 3", "0.200"),
    ("hiseq 4", "0.200"),
    ("miseq", "0.050"),
    ("iseq", "0.050"),
    ("nextseq", "0.500"),
]


def infer_expected_contamination_pct(instrument_model: str | None) -> str | None:
    """Return a string-formatted Numeric(5,3) default, or None for unknown models."""
    if not instrument_model:
        return None
    needle = instrument_model.strip().lower()
    for prefix, pct in _CONTAMINATION_BY_PREFIX:
        if needle.startswith(prefix):
            return pct
    return None
