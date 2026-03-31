"""
Process Metadata Annotations - New Format (v2)

Reads the per-municipality JSON dataset format and produces
BIO-tagged JSONL for token classification / NER training.

Input format:
    {"municipalities": [{"minutes": [{"full_text": "...", "metadata": {...}}]}]}

Output format (JSONL):
    {"text": "...", "tokens": [...], "tags": ["B-DATE", "O", ...],
     "entities": [...], "ata_id": "Alandroal_cm_002_2021-10-22", "section": "full"}

Entity types (12): DATE, TIME-START, TIME-END, LOCATION,
                   MEETING-TYPE-ORDINARY, MEETING-TYPE-EXTRAORDINARY,
                   MINUTE-NUMBER, PARTICIPANT-PRESIDENT-PRESENT, PARTICIPANT-PRESIDENT-ABSENT, 
                   PARTICIPANT-COUNCILOR-PRESENT, PARTICIPANT-COUNCILOR-ABSENT, PARTICIPANT-COUNCILOR-SUBSTITUTED

Usage:
    python convert_metadata_to_spans.py
    python convert_metadata_to_spans.py --input_dir data/citilink_metadata --output_dir data/output
"""

import os
import json
import logging
import argparse
import re
from pathlib import Path
import spacy
from tqdm import tqdm
from document_chunker import DocumentChunker
from faker import Faker
import dateparser
import random

# -----------------------------------------------------------
# Logging configuration
# -----------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------
# Language model configuration
# -----------------------------------------------------------
# Default: Portuguese model
# To switch to English, replace with "en_core_web_sm"
model = "pt_core_news_sm"

# model = "en_core_web_sm"

# Load spaCy model for tokenization and sentence splitting
try:
    nlp = spacy.load(model)
    logger.info(f"Loaded spaCy model: {model}")
except Exception:
    logger.warning(f"Could not load spaCy model. Installing...")
    import subprocess
    subprocess.call(["python", "-m", "spacy", "download", model])
    nlp = spacy.load(model)
    logger.info(f"Installed and loaded spaCy model")


# -----------------------------------------------------------
# Utility: Tokenization of dates and times
# -----------------------------------------------------------
def custom_tokenize_datetime(text):
    """
    Custom tokenizer that properly splits date and time patterns within text.
    Example: "11/09/2024" → ["11", "/", "09", "/", "2024"]
             "16:00" → ["16", ":", "00"]
    """
    pattern = r'(\d{1,2}/\d{1,2}/\d{4})|(\d{1,2}[:.]\d{2})'
    matches = list(re.finditer(pattern, text))

    tokens = []
    token_positions = []
    last_end = 0

    for match in matches:
        start, end = match.span()

        # Tokens before the matched expression
        if start > last_end:
            pre_text = text[last_end:start]
            pre_doc = nlp(pre_text)
            for token in pre_doc:
                tokens.append(token.text)
                token_positions.append(last_end + token.idx)

        matched_text = match.group()

        # Split date tokens
        if '/' in matched_text:
            day, month, year = matched_text.split('/')
            tokens.extend([day, '/', month, '/', year])
            token_positions.extend([
                start,
                start + len(day),
                start + len(day) + 1,
                start + len(day) + 1 + len(month),
                start + len(day) + 1 + len(month) + 1
            ])
        # Split time tokens
        elif ':' in matched_text or '.' in matched_text:
            sep = ':' if ':' in matched_text else '.'
            hour, minute = matched_text.split(sep)
            tokens.extend([hour, sep, minute])
            token_positions.extend([
                start,
                start + len(hour),
                start + len(hour) + 1
            ])

        last_end = end

    # Tokens after last match
    if last_end < len(text):
        post_text = text[last_end:]
        post_doc = nlp(post_text)
        for token in post_doc:
            tokens.append(token.text)
            token_positions.append(last_end + token.idx)

    return tokens, token_positions


# -----------------------------------------------------------
# End time correction in closing segments
# -----------------------------------------------------------
def extract_entities_from_metadata(metadata):
    """
    Extract structured metadata entities (e.g., date, times, participants)
    from the nested metadata dictionary of each document.
    All offsets are global (relative to full_text).
    """
    entities = []

    # ---- Date ----
    if "date" in metadata and metadata["date"]:
        date_info = metadata["date"]
        entities.append({
            "type": "DATE",
            "begin": date_info.get("start", date_info.get("begin", 0)),
            "end": date_info.get("end", 0),
            "text": date_info["text"],
            "metadata_type": "Date",
            "attributes": {}
        })

    # ---- Begin time ----
    if "begin_time" in metadata and metadata["begin_time"]:
        time_info = metadata["begin_time"]
        entities.append({
            "type": "TIME-START",
            "begin": time_info.get("start", time_info.get("begin", 0)),
            "end": time_info.get("end", 0),
            "text": time_info["text"],
            "metadata_type": "Time",
            "attributes": {"Time": "start"}
        })

    # ---- End time ----
    # Offsets are global (relative to full_text), so no segment correction needed.
    if "end_time" in metadata and metadata["end_time"]:
        end_time_info = metadata["end_time"]
        entities.append({
            "type": "TIME-END",
            "begin": end_time_info.get("start", end_time_info.get("begin", 0)),
            "end": end_time_info.get("end", 0),
            "text": end_time_info["text"],
            "metadata_type": "Time",
            "attributes": {"Time": "end"}
        })

    # ---- Location ----
    if "location" in metadata and metadata["location"]:
        location_info = metadata["location"]
        entities.append({
            "type": "LOCATION",
            "begin": location_info.get("start", location_info.get("begin", 0)),
            "end": location_info.get("end", 0),
            "text": location_info["text"],
            "metadata_type": "Location",
            "attributes": {}
        })

    # ---- Meeting type ----
    if "meeting_type" in metadata and metadata["meeting_type"]:
        meeting_info = metadata["meeting_type"]
        # New format may carry type directly in a "type" sub-field
        meeting_text = meeting_info.get("type", meeting_info["text"]).lower()
        display_text = meeting_info["text"]

        # Normalize entity type according to meeting type
        if "extraordinária" in meeting_text or "extraordinary" in meeting_text:
            entity_type = "MEETING-TYPE-EXTRAORDINARY"
        elif "ordinária" in meeting_text or "ordinary" in meeting_text:
            entity_type = "MEETING-TYPE-ORDINARY"
        else:
            entity_type = "MEETING-TYPE-ORDINARY"  # default fallback

        entities.append({
            "type": entity_type,
            "begin": meeting_info.get("start", meeting_info.get("begin", 0)),
            "end": meeting_info.get("end", 0),
            "text": display_text,
            "metadata_type": "Meeting type",
            "attributes": {"MeetingType": meeting_text}
        })

    # ---- Minute ID (meeting number) ----
    # Supports both "minute_id" (old format) and "minute_number" (new format)
    minute_id_info = metadata.get("minute_number") or metadata.get("minute_id")
    if minute_id_info:
        entities.append({
            "type": "MINUTE-NUMBER",
            "begin": minute_id_info.get("start", minute_id_info.get("begin", 0)),
            "end": minute_id_info.get("end", 0),
            "text": minute_id_info["text"],
            "metadata_type": "Minute number",
            "attributes": {}
        })

    # ---- Participants ----
    if "participants" in metadata and metadata["participants"]:
        for participant in metadata["participants"]:
            part_start = participant.get("start", participant.get("begin"))
            if part_start is None or "end" not in participant:
                continue

            participant_type = participant.get("type", "").lower()
            present = participant.get("present", "present")

            # Map textual participant type to normalized label
            # Supports both old format ("vice-president", "vereador") and
            # new format ("vice_president", "councilors", "staff", "public")
            if any(t in participant_type for t in ["vice-president", "vice_president", "vereador"]):
                entity_type = "PARTICIPANT-COUNCILOR"
            elif "president" in participant_type:
                entity_type = "PARTICIPANT-PRESIDENT"
            elif any(t in participant_type for t in ["staff", "funcionário"]):
                continue
            elif any(t in participant_type for t in ["public", "público"]):
                continue  # skip public attendees
            elif "councilor" in participant_type:
                entity_type = "PARTICIPANT-COUNCILOR"
            else:
                entity_type = "PARTICIPANT-COUNCILOR"  # default fallback

            entities.append({
                "type": entity_type,
                "begin": part_start,
                "end": participant["end"],
                "text": participant["name"],
                "metadata_type": "Participants",
                "attributes": {
                    "ParticipantType": participant_type,
                    "Presence": present,
                    "Party": participant.get("party", "")
                }
            })

    return entities


def generate_chunks_from_segment(segment_text, segment_offset, label, entities, ata_id):
    """
    Divide a text segment (opening or closing) into smaller overlapping chunks
    for training efficiency. Each chunk inherits only the entities overlapping
    with its character span, with adjusted offsets.
    """
    if not segment_text.strip():
        return []

    # Create chunker with 600-char chunks and 200-char overlap
    chunker = DocumentChunker(chunk_size=600, chunk_overlap=200)
    chunks = chunker.chunk_document(segment_text)
    result = []

    search_from = 0
    for chunk in chunks:
        # Use search_from to find the correct occurrence of this chunk,
        # not always the first — overlapping chunks share a prefix with
        # earlier chunks, so find() without a start offset returns the
        # wrong position for every chunk after the first.
        chunk_start_in_segment = segment_text.find(chunk, search_from)
        if chunk_start_in_segment == -1:
            continue

        chunk_end_in_segment = chunk_start_in_segment + len(chunk)
        # Advance search cursor: next chunk starts at or after this chunk's
        # start + 1 so overlapping chunks are found at their real position.
        search_from = chunk_start_in_segment + 1
        chunk_entities = []

        # Identify all entities that overlap with this chunk
        for entity in entities:
            entity_begin = entity["begin"] - segment_offset
            entity_end = entity["end"] - segment_offset

            # Check if entity overlaps with current chunk
            if not (entity_end <= chunk_start_in_segment or entity_begin >= chunk_end_in_segment):
                adjusted_begin = max(0, entity_begin - chunk_start_in_segment)
                adjusted_end = min(len(chunk), entity_end - chunk_start_in_segment)

                if adjusted_begin < adjusted_end:
                    chunk_entities.append({
                        "type": entity["type"],
                        "begin": adjusted_begin,
                        "end": adjusted_end,
                        "text": chunk[adjusted_begin:adjusted_end],
                        "metadata_type": entity["metadata_type"],
                        "attributes": entity["attributes"]
                    })

        # Add chunk to the result, even if no entities were found
        result.append({
            "text": chunk,
            "entities": chunk_entities,
            "ata_id": ata_id,
            "section": label
        })

    return result


def extract_metadata_entities(minute):
    """
    Extract metadata entities from a single minute entry (new format).

    Each minute has a 'full_text' field and a 'metadata' block with date,
    times, location, meeting_type, and participants. All entity offsets are
    global (relative to full_text). Returns chunked document dicts for BIO tagging.
    """
    documents = []

    metadata = minute.get("metadata", {})
    if not metadata:
        logger.warning("Minute entry has no 'metadata' block — skipping")
        return documents

    # Document unique identifier: prefer document_id, then minute_number text, then fallback
    minute_number = metadata.get("minute_number", {})
    ata_id = (
        metadata.get("document_id")
        or (minute_number.get("text") if minute_number else None)
        or "unknown"
    )

    # Full text of the minute — all entity offsets are relative to this
    full_text = minute.get("full_text", "")

    if not full_text:
        logger.warning(f"No full_text found in minute {ata_id}")
        return documents

    # Extract all metadata-based entities (offsets are already global)
    metadata_entities = extract_entities_from_metadata(metadata)

    # Generate chunks over the full text with offset 0
    chunks = generate_chunks_from_segment(
        full_text, 0, "full", metadata_entities, ata_id
    )
    documents.extend(chunks)

    return documents

def create_token_classification_examples(documents):
    """
    Convert processed documents into token classification examples
    compatible with transformer-based NER models.

    Each document becomes a training instance with:
    - tokens (from spaCy or custom tokenizer)
    - BIO tags (B- / I- / O-)
    - metadata entities
    - document identifiers and section type

    """
    examples = []

    for doc in documents:

        text = doc["text"]
        entities = doc["entities"]

        # Skip chunks with no entities
        if not entities:
            continue

        # Tokenize text, splitting correctly around time/date expressions
        tokens, token_positions = custom_tokenize_datetime(text)
        tags = ["O"] * len(tokens)

        # --------------------------------------------------------
        # Map entities to tokens → assign BIO (Begin / Inside / Outside) tags
        # --------------------------------------------------------
        for entity in entities:
            entity_begin = entity["begin"]
            entity_end = entity["end"]
            entity_type = entity["type"]

            # Handle presence status (e.g., PRESENT, ABSENT)
            presenca = entity.get("attributes", {}).get("Presence")
            if presenca:
                presenca_norm = presenca.strip().lower()
                if presenca_norm in ["present", "presente"]:
                    entity_type = f"{entity_type}-PRESENT"
                elif presenca_norm in ["absent", "ausente"]:
                    entity_type = f"{entity_type}-ABSENT"
                elif presenca_norm in ["substituted", "substituido"]:
                    entity_type = f"{entity_type}-SUBSTITUTED"

            # Identify token indices overlapping with the entity
            entity_tokens = []
            for i, token_pos in enumerate(token_positions):
                if i < len(tokens):
                    token_start = token_pos
                    token_end = token_pos + len(tokens[i])

                    # Check if token overlaps with entity span
                    if not (token_end <= entity_begin or token_start >= entity_end):
                        entity_tokens.append(i)

            # Assign BIO tags to overlapping tokens
            if entity_tokens:
                for i, token_idx in enumerate(entity_tokens):
                    if i == 0:
                        tags[token_idx] = f"B-{entity_type}"
                    else:
                        tags[token_idx] = f"I-{entity_type}"

        # --------------------------------------------------------
        # Create a complete example for this document
        # --------------------------------------------------------
        example = {
            "text": text,
            "tokens": tokens,
            "tags": tags,
            "entities": entities,
            "ata_id": doc.get("ata_id"),
            "section": doc.get("section")
        }
        examples.append(example)

    return examples


def load_json_files_from_directory(directory_path):
    """
    Load all JSON files from the input directory.

    Each file represents one municipality and must follow the new format:
      {"municipalities": [{"minutes": [...]}]}

    Returns a dict mapping municipality_name → list of minutes.
    """
    municipality_minutes = {}
    directory = Path(directory_path)

    for json_file in directory.glob("*.json"):
        # Derive municipality name from filename (e.g. "alandroal_2021.json" → "alandroal")
        municipality_name = json_file.stem.split("_")[0]

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # New format: top-level key is "municipalities"
            if isinstance(data, dict) and "municipalities" in data:
                all_minutes = []
                for muni_entry in data["municipalities"]:
                    minutes = muni_entry.get("minutes", [])
                    # Inject municipality name into each minute's metadata
                    for minute in minutes:
                        meta = minute.get("metadata", {})
                        if "municipality" not in meta:
                            meta["municipality"] = municipality_name
                    all_minutes.extend(minutes)

                municipality_minutes[municipality_name] = all_minutes
                logger.info(f"{json_file.name}: {len(all_minutes)} minutes")
            else:
                logger.warning(f"{json_file.name}: missing 'municipalities' key — skipping")

        except Exception as e:
            logger.error(f"Error loading {json_file}: {str(e)}")

    return municipality_minutes


def process_municipality_minutes(minutes, municipality_name=None):
    """
    Main processing function for each municipality.

    Iterates over all minutes in a municipality, converts them into
    BIO-tagged examples, and returns a single combined list.
    No train/val/test split is applied.
    """
    all_documents = []

    logger.info(f"Processing {len(minutes)} minutes for {municipality_name}")

    for minute in tqdm(minutes, desc=f"Processing {municipality_name}"):
        try:
            docs = extract_metadata_entities(minute)
            all_documents.extend(docs)
        except Exception as e:
            metadata = minute.get("metadata", {})
            minute_id = metadata.get("document_id", "unknown")
            logger.error(f"Error processing minute {minute_id}: {str(e)}")

    logger.info(f"Total documents extracted: {len(all_documents)}")

    examples = create_token_classification_examples(all_documents)

    # Deduplication
    seen = set()
    deduplicated = []
    for ex in examples:
        key = (ex["ata_id"], ex["text"])
        if key not in seen:
            seen.add(key)
            deduplicated.append(ex)

    logger.info(f"Final examples after deduplication: {len(deduplicated)}")
    return deduplicated

def save_jsonl(path, examples):
    """Write examples normally."""
    with open(path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def main():
    """Main execution function — orchestrates the full dataset processing pipeline."""
    parser = argparse.ArgumentParser(description="Process metadata annotations from per-municipality JSON format")
    parser.add_argument("--input_dir", type=str, default="src/metadata_identification/Dataset/",
                        help="Path to directory containing JSON files (one per municipality)")
    parser.add_argument("--output_dir", type=str, default="data/metadata",
                        help="Output directory for processed datasets")

    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    # Load input JSON files (new format: municipalities[] > minutes[])
    municipality_data = load_json_files_from_directory(args.input_dir)
    if not municipality_data:
        logger.error("No JSON files found in the input directory")
        return

    logger.info(f"Found {len(municipality_data)} municipalities: {list(municipality_data.keys())}")

    combined_examples = []

    # ------------------------------------------------------------------
    # Process each municipality
    # ------------------------------------------------------------------
    for municipality_name, minutes in municipality_data.items():
        logger.info(f"\n=== Processing {municipality_name} ===")

        municipality_clean = (
            municipality_name.lower()
            .replace(" ", "_")
            .replace("ç", "c")
            .replace("ã", "a")
        )

        examples = process_municipality_minutes(minutes, municipality_name)

        # Save per-municipality JSONL
        if examples:
            out_path = os.path.join(args.output_dir, f"{municipality_clean}.jsonl")
            save_jsonl(out_path, examples)
            logger.info(f"Saved {len(examples)} examples → {out_path}")

        combined_examples.extend(examples)

    # ------------------------------------------------------------------
    # Save combined output
    # ------------------------------------------------------------------
    combined_path = os.path.join(args.output_dir, "combined.jsonl")
    save_jsonl(combined_path, combined_examples)

    logger.info("\n=== Processing completed successfully ===")
    logger.info(f"Total examples (all municipalities): {len(combined_examples)}")


if __name__ == "__main__":
    main()