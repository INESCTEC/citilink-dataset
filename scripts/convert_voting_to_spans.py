#!/usr/bin/env python3
"""
Convert CitiLink Voting annotations to span-annotated JSONL

Reads the hierarchical CitiLink dataset format from data/citilink-dataset/ and produces
span JSONL with event_id for multi-vote support.

Output format (spans JSONL):
    {"id": "Alandroal_cm_002_2021-10-22_1",
     "text": "...",
     "spans": [{"start": 50, "end": 70, "label": "VOTER-FAVOR", "text": "A CÂMARA", "event_id": 1}],
     "municipality": "M01",
     "document_id": "Alandroal_cm_002_2021-10-22",
     "subject_id": "Alandroal_cm_002_2021-10-22_1"}

Entity types (13): SUBJECT, VOTING, VOTER-FAVOR, VOTER-AGAINST, VOTER-ABSTENTION,
                   VOTER-ABSENT, COUNTING-UNANIMITY, COUNTING-MAJORITY, COUNT-FAVOR,
                   COUNT-AGAINST, COUNT-ABSTENTION, COUNT-BLANK, VOTING-METHOD

Usage:
    python scripts/convert_citilink_to_spans.py
    python scripts/convert_citilink_to_spans.py --input data/citilink-dataset/ --output-dir data/citilink_spans
"""

import argparse
import json
import logging
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_INPUT_DIR = Path("data/citilink-dataset")
DEFAULT_OUTPUT_DIR = Path("data/citilink_spans_v2")
DEFAULT_SPLIT_INFO = Path("data/split_info.json")

MUNICIPALITY_NAME_TO_ID = {
    "Alandroal": "M01",
    "Campomaior": "M02",
    "Covilha": "M03",
    "Fundao": "M04",
    "Guimaraes": "M05",
    "Porto": "M06",
}

# 13 entity types
ENTITY_LABELS = {
    "SUBJECT", "VOTING",
    "VOTER-FAVOR", "VOTER-AGAINST", "VOTER-ABSTENTION", "VOTER-ABSENT",
    "COUNTING-UNANIMITY", "COUNTING-MAJORITY",
    "COUNT-FAVOR", "COUNT-AGAINST", "COUNT-ABSTENTION", "COUNT-BLANK",
    "VOTING-METHOD",
}

# Regex to detect aggregate count spans (e.g., "7 votos a favor")
# Only used for in_favor/against/abstention in secret ballot events.
COUNT_PATTERN = re.compile(r'^\d+\s+voto', re.IGNORECASE)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_count_span(text: str) -> bool:
    """
    Detect whether a voter span is an aggregate count (e.g., '7 votos a favor')
    vs a named voter (e.g., 'A CÂMARA MUNICIPAL').

    Only used for in_favor/against/abstention in secret ballot events.
    voters.blank always maps to COUNT-BLANK directly (no regex needed).
    Non-secret ballot subjects always use named VOTER-* labels.
    """
    return bool(COUNT_PATTERN.match(text.strip()))


def make_span(text: str, label: str, abs_start: int, abs_end: int,
              event_id: int, subject_start: int) -> Dict[str, Any]:
    """Create a span dict with subject-relative offsets."""
    return {
        "start": abs_start - subject_start,
        "end": abs_end - subject_start,
        "label": label,
        "text": text,
        "event_id": event_id,
    }


# ============================================================================
# VOTING EVENT CONVERSION
# ============================================================================

def convert_voting_event(
    voting: Dict[str, Any],
    subject_start: int,
    event_id: int,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Convert a single voting event to a list of span dicts.

    All offsets in the input are absolute to minute.full_text; we subtract
    subject_start to make them relative to subject.text.

    Args:
        voting: A voting event dict from the dataset.
        subject_start: Character offset of the parent subject in full_text.
        event_id: 1-indexed event identifier.

    Returns:
        (spans, warnings)
    """
    spans = []
    warnings = []
    has_vote_type = bool(voting.get("vote_type"))

    # voting_evidence → VOTING
    ve = voting.get("voting_evidence")
    if ve and ve.get("text"):
        spans.append(make_span(ve["text"], "VOTING", ve["start"], ve["end"],
                               event_id, subject_start))

    # vote_type → VOTING-METHOD (structural field at voting event level)
    vt = voting.get("vote_type")
    if vt and isinstance(vt, dict) and vt.get("text"):
        spans.append(make_span(vt["text"], "VOTING-METHOD", vt["start"], vt["end"],
                               event_id, subject_start))

    # voters
    voters = voting.get("voters", {})

    # voters.blank → COUNT-BLANK (always aggregate, no regex needed)
    for v in voters.get("blank", []):
        if v.get("text"):
            spans.append(make_span(v["text"], "COUNT-BLANK", v["start"], v["end"],
                                   event_id, subject_start))

    # voters.in_favor → VOTER-FAVOR or COUNT-FAVOR
    for v in voters.get("in_favor", []):
        if not v.get("text"):
            continue
        if has_vote_type and is_count_span(v["text"]):
            label = "COUNT-FAVOR"
        else:
            label = "VOTER-FAVOR"
        spans.append(make_span(v["text"], label, v["start"], v["end"],
                               event_id, subject_start))

    # voters.against → VOTER-AGAINST or COUNT-AGAINST
    for v in voters.get("against", []):
        if not v.get("text"):
            continue
        if has_vote_type and is_count_span(v["text"]):
            label = "COUNT-AGAINST"
        else:
            label = "VOTER-AGAINST"
        spans.append(make_span(v["text"], label, v["start"], v["end"],
                               event_id, subject_start))

    # voters.abstention → VOTER-ABSTENTION or COUNT-ABSTENTION
    for v in voters.get("abstention", []):
        if not v.get("text"):
            continue
        if has_vote_type and is_count_span(v["text"]):
            label = "COUNT-ABSTENTION"
        else:
            label = "VOTER-ABSTENTION"
        spans.append(make_span(v["text"], label, v["start"], v["end"],
                               event_id, subject_start))

    # non_voters → VOTER-ABSENT
    for v in voting.get("non_voters", []):
        if v.get("text"):
            spans.append(make_span(v["text"], "VOTER-ABSENT", v["start"], v["end"],
                                   event_id, subject_start))

    # global_tally → COUNTING-UNANIMITY or COUNTING-MAJORITY
    tally = voting.get("global_tally")
    if tally and tally.get("text"):
        tally_type = tally.get("type", "")
        if tally_type == "unanimous":
            label = "COUNTING-UNANIMITY"
        elif tally_type == "majority":
            label = "COUNTING-MAJORITY"
        else:
            # Fallback: check text content
            text_lower = tally["text"].lower()
            if "unanim" in text_lower or "todos" in text_lower:
                label = "COUNTING-UNANIMITY"
            else:
                label = "COUNTING-MAJORITY"
            warnings.append(
                f"Unknown global_tally type '{tally_type}', "
                f"inferred {label} from text '{tally['text']}'"
            )
        spans.append(make_span(tally["text"], label, tally["start"], tally["end"],
                               event_id, subject_start))

    return spans, warnings


# ============================================================================
# SUBJECT CONVERSION
# ============================================================================

def convert_subject_to_span_example(
    subject: Dict[str, Any],
    minute: Dict[str, Any],
    municipality_name: str,
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Convert a single subject to a span-annotated example dict.

    Args:
        subject: Subject dict from the dataset.
        minute: Parent minute dict (for full_text validation).
        municipality_name: Capitalized municipality name.

    Returns:
        (example_dict, warnings) or (None, warnings) if invalid.
    """
    warnings = []
    subject_id = subject["subject_id"]
    subject_text = subject["text"]
    subject_start = subject["start"]
    subject_end = subject["end"]
    municipality_id = MUNICIPALITY_NAME_TO_ID.get(municipality_name, municipality_name)
    minute_id = minute["minute_id"]

    if not subject_text.strip():
        warnings.append(f"{subject_id}: empty text, skipping")
        return None, warnings

    # Validate subject text against full_text
    full_text = minute["full_text"]
    expected_text = full_text[subject_start:subject_end]
    if subject_text != expected_text:
        if subject_text.strip() != expected_text.strip():
            warnings.append(
                f"{subject_id}: subject text doesn't match "
                f"full_text[{subject_start}:{subject_end}]"
            )

    spans = []

    # SUBJECT span from subject.subject field (the voted-on matter, not entire text)
    subj_field = subject.get("subject")
    if subj_field and subj_field.get("text"):
        spans.append(make_span(
            subj_field["text"], "SUBJECT",
            subj_field["start"], subj_field["end"],
            1, subject_start
        ))

    # Process voting events
    voting_events = subject.get("voting", [])
    for idx, voting in enumerate(voting_events):
        event_id = idx + 1  # 1-indexed
        event_spans, event_warnings = convert_voting_event(
            voting, subject_start, event_id
        )
        spans.extend(event_spans)
        warnings.extend(event_warnings)

    # Validate all span offsets against subject text
    for span in spans:
        s, e = span["start"], span["end"]
        if s < 0 or e > len(subject_text):
            warnings.append(
                f"{subject_id}: out-of-bounds {span['label']} "
                f"[{s}:{e}] in text of length {len(subject_text)}"
            )
            continue
        actual = subject_text[s:e]
        if actual != span["text"]:
            warnings.append(
                f"{subject_id}: {span['label']} text mismatch at [{s}:{e}]: "
                f"expected {span['text']!r}, got {actual!r}"
            )

    # Sort spans by start position
    spans.sort(key=lambda s: (s["start"], s["end"]))

    return {
        "id": subject_id,
        "text": subject_text,
        "spans": spans,
        "municipality": municipality_id,
        "document_id": minute_id,
        "subject_id": subject_id,
    }, warnings


# ============================================================================
# SPLIT ASSIGNMENT
# ============================================================================

def load_split_info(split_info_file: Path) -> Dict[str, Set[str]]:
    """
    Load document-level splits from split_info.json.

    The file maps minute_id + ".json" to train/val/test splits.
    """
    with open(split_info_file, 'r', encoding='utf-8') as f:
        split_data = json.load(f)

    splits = {
        "train": set(split_data["train_files"]),
        "dev": set(split_data["val_files"]),
        "test": set(split_data["test_files"]),
    }

    logger.info(f"Split info: train={len(splits['train'])}, "
                f"dev={len(splits['dev'])}, test={len(splits['test'])} documents")
    return splits


def get_split_for_minute(minute_id: str, splits: Dict[str, Set[str]]) -> Optional[str]:
    """Determine which split a minute belongs to."""
    key = minute_id + ".json"
    for split_name, doc_set in splits.items():
        if key in doc_set:
            return split_name
    return None


# ============================================================================
# MAIN CONVERSION
# ============================================================================

def convert_dataset(
    input_dir: Path,
    splits: Dict[str, Set[str]],
) -> Tuple[Dict[str, List[Dict]], Dict[str, Any], List[str]]:
    """
    Convert all municipality files from the new CitiLink format to span JSONL.

    Returns:
        (examples_by_split, statistics, all_warnings)
    """
    examples = {"train": [], "dev": [], "test": []}
    stats: Dict[str, Any] = {
        "subjects_total": 0,
        "subjects_with_voting": 0,
        "subjects_multi_vote": 0,
        "subjects_secret_ballot": 0,
        "subjects_no_voting": 0,
        "entities_by_label": Counter(),
        "municipalities": {},
        "unmatched_minutes": [],
    }
    all_warnings: List[str] = []

    # Try all_municipalities.json first, then individual files
    all_file = input_dir / "all_municipalities.json"
    if all_file.exists():
        logger.info(f"Loading {all_file}...")
        with open(all_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        all_municipalities = data["municipalities"]
    else:
        logger.info(f"Loading individual municipality files from {input_dir}...")
        all_municipalities = []
        for json_file in sorted(input_dir.glob("*.json")):
            if json_file.name == "all_municipalities.json":
                continue
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            all_municipalities.extend(data["municipalities"])

    for municipality_data in all_municipalities:
        municipality_name = municipality_data["municipality"]
        municipality_id = MUNICIPALITY_NAME_TO_ID.get(
            municipality_name, municipality_name
        )
        muni_subjects = 0
        muni_examples = 0

        for minute in municipality_data["minutes"]:
            minute_id = minute["minute_id"]
            split_name = get_split_for_minute(minute_id, splits)

            if split_name is None:
                if minute_id not in stats["unmatched_minutes"]:
                    stats["unmatched_minutes"].append(minute_id)
                    logger.warning(f"Document {minute_id} not in split_info — skipping")
                continue

            for agenda_item in minute.get("agenda_items", []):
                for subject in agenda_item.get("subjects", []):
                    stats["subjects_total"] += 1
                    muni_subjects += 1

                    voting_events = subject.get("voting", [])
                    if voting_events:
                        stats["subjects_with_voting"] += 1
                    else:
                        stats["subjects_no_voting"] += 1
                    if len(voting_events) >= 2:
                        stats["subjects_multi_vote"] += 1
                    if any(v.get("vote_type") for v in voting_events):
                        stats["subjects_secret_ballot"] += 1

                    example, warnings = convert_subject_to_span_example(
                        subject, minute, municipality_name
                    )
                    all_warnings.extend(warnings)

                    if example is not None:
                        examples[split_name].append(example)
                        muni_examples += 1
                        for span in example["spans"]:
                            stats["entities_by_label"][span["label"]] += 1

        stats["municipalities"][municipality_id] = {
            "name": municipality_name,
            "subjects": muni_subjects,
            "examples": muni_examples,
        }

        total = sum(len(v) for v in examples.values())
        logger.info(f"  {municipality_name} ({municipality_id}): "
                     f"{muni_subjects} subjects → {muni_examples} examples "
                     f"({total} total)")

    return examples, stats, all_warnings


# ============================================================================
# OUTPUT
# ============================================================================

def save_jsonl(examples: List[Dict], output_file: Path):
    """Save examples to JSONL file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    logger.info(f"  Saved {len(examples)} examples to {output_file}")


def save_statistics(
    stats: Dict[str, Any],
    examples: Dict[str, List[Dict]],
    warnings: List[str],
    output_dir: Path,
):
    """Save conversion statistics to JSON."""
    total = sum(len(v) for v in examples.values())

    def analyze_split(split_examples: List[Dict]) -> Dict:
        entity_counts = Counter()
        municipality_counts = Counter()
        multi_vote = 0
        for ex in split_examples:
            event_ids = set()
            for span in ex["spans"]:
                entity_counts[span["label"]] += 1
                event_ids.add(span.get("event_id", 1))
            municipality_counts[ex["municipality"]] += 1
            if len(event_ids) > 1:
                multi_vote += 1
        return {
            "num_examples": len(split_examples),
            "total_entities": sum(entity_counts.values()),
            "entity_type_counts": dict(entity_counts),
            "municipality_distribution": dict(municipality_counts),
            "multi_vote_examples": multi_vote,
        }

    output = {
        "conversion_info": {
            "timestamp": datetime.now().isoformat(),
            "script": "convert_new_citilink_to_spans.py",
            "entity_types": sorted(ENTITY_LABELS),
            "num_entity_types": len(ENTITY_LABELS),
        },
        "dataset_statistics": {
            "subjects_total": stats["subjects_total"],
            "subjects_with_voting": stats["subjects_with_voting"],
            "subjects_no_voting": stats["subjects_no_voting"],
            "subjects_multi_vote": stats["subjects_multi_vote"],
            "subjects_secret_ballot": stats["subjects_secret_ballot"],
            "entities_by_label": dict(stats["entities_by_label"]),
            "total_entities": sum(stats["entities_by_label"].values()),
            "municipalities": stats["municipalities"],
        },
        "splits": {
            split: analyze_split(exs)
            for split, exs in examples.items()
        },
        "split_ratios": {
            s: len(examples[s]) / total if total else 0
            for s in ["train", "dev", "test"]
        },
        "warnings_count": len(warnings),
        "unmatched_minutes": stats["unmatched_minutes"],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    stats_file = output_dir / "statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"  Saved statistics to {stats_file}")

    if warnings:
        warnings_file = output_dir / "conversion_warnings.txt"
        with open(warnings_file, 'w', encoding='utf-8') as f:
            for w in warnings:
                f.write(w + '\n')
        logger.info(f"  Saved {len(warnings)} warnings to {warnings_file}")

    return output


# ============================================================================
# VALIDATION
# ============================================================================

def validate_examples(examples: Dict[str, List[Dict]]) -> Tuple[bool, List[str]]:
    """Validate all converted examples."""
    errors = []
    total_spans = 0

    for split_name, split_examples in examples.items():
        for ex in split_examples:
            for span in ex["spans"]:
                total_spans += 1

                if span["label"] not in ENTITY_LABELS:
                    errors.append(f"{ex['id']}: unknown label {span['label']}")

                if span["start"] < 0 or span["end"] > len(ex["text"]):
                    errors.append(
                        f"{ex['id']}: {span['label']} out of bounds "
                        f"[{span['start']}:{span['end']}] (text len={len(ex['text'])})"
                    )
                    continue

                actual = ex["text"][span["start"]:span["end"]]
                if actual != span["text"]:
                    errors.append(
                        f"{ex['id']}: {span['label']} text mismatch at "
                        f"[{span['start']}:{span['end']}]: "
                        f"{actual!r} != {span['text']!r}"
                    )

                if span.get("event_id", 0) < 1:
                    errors.append(
                        f"{ex['id']}: {span['label']} invalid event_id={span.get('event_id')}"
                    )

    if errors:
        logger.error(f"Validation failed: {len(errors)} errors in {total_spans} spans")
        for e in errors[:20]:
            logger.error(f"  {e}")
        if len(errors) > 20:
            logger.error(f"  ... and {len(errors) - 20} more")
    else:
        logger.info(f"Validation passed: {total_spans} spans OK across "
                     f"{sum(len(v) for v in examples.values())} examples")

    return len(errors) == 0, errors


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Convert new CitiLink dataset to span-annotated JSONL (v2)"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_DIR,
                        help=f"Input directory (default: {DEFAULT_INPUT_DIR})")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--split-info", type=Path, default=DEFAULT_SPLIT_INFO,
                        help=f"Split info file (default: {DEFAULT_SPLIT_INFO})")
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("NEW CITILINK TO SPAN FORMAT CONVERSION (v2)")
    logger.info("=" * 80)
    logger.info(f"Input:      {args.input}")
    logger.info(f"Output:     {args.output_dir}")
    logger.info(f"Split info: {args.split_info}")
    logger.info(f"Entity types: {len(ENTITY_LABELS)} ({', '.join(sorted(ENTITY_LABELS))})")
    logger.info("")

    if not args.input.exists():
        logger.error(f"Input directory not found: {args.input}")
        return 1
    if not args.split_info.exists():
        logger.error(f"Split info file not found: {args.split_info}")
        return 1

    splits = load_split_info(args.split_info)

    logger.info("Converting...")
    examples, stats, warnings = convert_dataset(args.input, splits)

    total = sum(len(examples[s]) for s in ["train", "dev", "test"])
    if total == 0:
        logger.error("No examples converted!")
        return 1

    logger.info("")
    logger.info("Validating...")
    valid, validation_errors = validate_examples(examples)

    logger.info("")
    logger.info("Saving...")
    for split_name in ["train", "dev", "test"]:
        save_jsonl(examples[split_name], args.output_dir / f"{split_name}.jsonl")
    final_stats = save_statistics(stats, examples, warnings, args.output_dir)

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("CONVERSION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total examples:      {total}")
    logger.info(f"  Train:             {len(examples['train'])} ({len(examples['train'])/total:.1%})")
    logger.info(f"  Dev:               {len(examples['dev'])} ({len(examples['dev'])/total:.1%})")
    logger.info(f"  Test:              {len(examples['test'])} ({len(examples['test'])/total:.1%})")
    logger.info(f"  With voting:       {stats['subjects_with_voting']}")
    logger.info(f"  No voting:         {stats['subjects_no_voting']}")
    logger.info(f"  Multi-vote:        {stats['subjects_multi_vote']}")
    logger.info(f"  Secret ballot:     {stats['subjects_secret_ballot']}")
    logger.info("")
    logger.info("Entities by type:")
    for label in sorted(stats["entities_by_label"]):
        count = stats["entities_by_label"][label]
        logger.info(f"  {label:25} {count:5d}")
    logger.info(f"  {'TOTAL':25} {sum(stats['entities_by_label'].values()):5d}")
    if warnings:
        logger.info(f"\nWarnings: {len(warnings)} (see {args.output_dir}/conversion_warnings.txt)")
    logger.info(f"\nValidation: {'PASSED' if valid else 'FAILED'}")
    logger.info(f"Output: {args.output_dir}/{{train,dev,test}}.jsonl")
    logger.info("=" * 80)

    return 0 if valid else 1


if __name__ == "__main__":
    sys.exit(main())
