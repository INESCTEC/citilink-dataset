#!/usr/bin/env python3
"""
CitiLink-Minutes Dataset Subset Generator

This script creates three subsets of the CitiLink-Minutes dataset:
1. metadata: Contains only metadata annotations (participants, dates, locations, etc.)
2. subjects_with_votings: Contains subjects with all annotations including voting records
3. subjects_only: Contains only core subject annotations (start, end, subject_of_discussion, theme, topics)

Usage:
    python create_subsets.py [input_file] [--output-dir OUTPUT_DIR]

Examples:
    # Process single file
    python create_subsets.py data/Alandroal.json
    
    # Process all files
    python create_subsets.py data/*.json --output-dir subsets/
"""

import json
import argparse
import os
from pathlib import Path
from typing import Dict, List, Any
import sys


def create_metadata_subset(data: Dict) -> Dict:
    """
    Extract only metadata annotations.
    Removes agenda_items and subjects, keeps only metadata fields.
    """
    subset = {
        "municipalities": []
    }
    
    for municipality in data.get("municipalities", []):
        muni_data = {
            "municipality": municipality.get("municipality"),
            "minutes": []
        }
        
        for minute in municipality.get("minutes", []):
            minute_data = {
                "minute_id": minute.get("minute_id"),
                "full_text": minute.get("full_text"),
                "metadata": minute.get("metadata", {})
            }
            muni_data["minutes"].append(minute_data)
        
        subset["municipalities"].append(muni_data)
    
    return subset


def create_subjects_only_subset(data: Dict) -> Dict:
    """
    Extract only core subject annotations (start, end, subject_of_discussion, theme, topics).
    Removes voting information and full text content.
    """
    subset = {
        "municipalities": []
    }
    
    for municipality in data.get("municipalities", []):
        muni_data = {
            "municipality": municipality.get("municipality"),
            "minutes": []
        }
        
        for minute in municipality.get("minutes", []):
            minute_data = {
                "minute_id": minute.get("minute_id"),
                "agenda_items": []
            }
            
            for item in minute.get("agenda_items", []):
                item_data = {
                    "item_id": item.get("item_id"),
                    "item_title": item.get("item_title"),
                    "subjects": []
                }
                
                for subject in item.get("subjects", []):
                    subject_data = {
                        "subject_id": subject.get("subject_id"),
                        "start": subject.get("start"),
                        "end": subject.get("end"),
                        "subject_of_discussion": subject.get("subject_of_discussion"),
                        "theme": subject.get("theme"),
                        "topics": subject.get("topics", [])
                    }
                    item_data["subjects"].append(subject_data)
                
                minute_data["agenda_items"].append(item_data)
            
            muni_data["minutes"].append(minute_data)
        
        subset["municipalities"].append(muni_data)
    
    return subset


def create_subjects_with_votings_subset(data: Dict) -> Dict:
    """
    Extract subjects with all annotations including voting records.
    Includes full_text, removes only metadata. Contains complete subject information.
    """
    subset = {
        "municipalities": []
    }
    
    for municipality in data.get("municipalities", []):
        muni_data = {
            "municipality": municipality.get("municipality"),
            "minutes": []
        }
        
        for minute in municipality.get("minutes", []):
            minute_data = {
                "minute_id": minute.get("minute_id"),
                "full_text": minute.get("full_text"),  # Include full_text
                "agenda_items": []
            }
            
            for item in minute.get("agenda_items", []):
                item_data = {
                    "item_id": item.get("item_id"),
                    "item_title": item.get("item_title"),
                    "subjects": item.get("subjects", [])  # Keep all subject data
                }
                minute_data["agenda_items"].append(item_data)
            
            muni_data["minutes"].append(minute_data)
        
        subset["municipalities"].append(muni_data)
    
    return subset


def save_subset(subset: Dict, output_path: Path, subset_name: str) -> None:
    """Save subset to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(subset, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Created {subset_name}: {output_path}")


def process_file(input_file: Path, output_dir: Path, subset_names: List[str] = None) -> None:
    """Process a single input file and create specified subsets."""
    print(f"\nProcessing: {input_file}")
    
    # Load data
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"✗ Error loading {input_file}: {e}")
        return
    
    # Get base filename
    base_name = input_file.stem  # e.g., "Alandroal"
    
    # Define all available subsets
    all_subsets = {
        "metadata": create_metadata_subset,
        "subjects_only": create_subjects_only_subset,
        "subjects_with_votings": create_subjects_with_votings_subset
    }
    
    # Determine which subsets to create
    if subset_names is None:
        # Create all subsets
        subsets_to_create = all_subsets
    else:
        # Create only specified subsets
        subsets_to_create = {name: all_subsets[name] for name in subset_names if name in all_subsets}
        
        # Warn about invalid subset names
        invalid = set(subset_names) - set(all_subsets.keys())
        if invalid:
            print(f"⚠ Warning: Unknown subset(s): {', '.join(invalid)}")
    
    if not subsets_to_create:
        print("✗ No valid subsets specified")
        return
    
    # Create subsets
    created_subsets = {}
    for subset_name, subset_func in subsets_to_create.items():
        subset_data = subset_func(data)
        created_subsets[subset_name] = subset_data
        
        output_file = output_dir / subset_name / f"{base_name}.json"
        save_subset(subset_data, output_file, subset_name)
    
    # Print statistics
    print_statistics(data, created_subsets, base_name)


def print_statistics(original: Dict, subsets: Dict, name: str) -> None:
    """Print statistics about the original and subset data."""
    def get_size(data):
        return len(json.dumps(data, ensure_ascii=False))
    
    original_size = get_size(original)
    
    print(f"\n📊 Statistics for {name}:")
    print(f"  Original size: {original_size:,} bytes")
    
    for subset_name, subset_data in subsets.items():
        subset_size = get_size(subset_data)
        reduction = (1 - subset_size / original_size) * 100
        print(f"  {subset_name}: {subset_size:,} bytes ({reduction:.1f}% reduction)")


def main():
    parser = argparse.ArgumentParser(
        description="Create subsets of CitiLink-Minutes dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Subset Descriptions:
  metadata              Only metadata annotations (participants, dates, locations, etc.)
  subjects_only         Core subject annotations (start, end, theme, topics) without voting
  subjects_with_votings Complete subject annotations including voting records and full_text

Examples:
  # Create all subsets
  python create_subsets.py data/Alandroal.json
  
  # Create only metadata subset
  python create_subsets.py data/Alandroal.json --subset metadata
  
  # Create multiple specific subsets
  python create_subsets.py data/*.json --subset metadata subjects_only
  
  # Custom output directory
  python create_subsets.py data/*.json --output-dir my_subsets/
        """
    )
    
    parser.add_argument(
        'input_files',
        nargs='+',
        type=Path,
        help='Input JSON file(s) to process'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('subsets'),
        help='Output directory for subsets (default: subsets/)'
    )
    
    parser.add_argument(
        '--subset',
        nargs='+',
        choices=['metadata', 'subjects_only', 'subjects_with_votings'],
        help='Specific subset(s) to create (default: all subsets)'
    )
    
    args = parser.parse_args()
    
    # Process each input file
    print("=" * 60)
    print("CitiLink-Minutes Dataset Subset Generator")
    print("=" * 60)
    
    if args.subset:
        print(f"Creating subset(s): {', '.join(args.subset)}")
    else:
        print("Creating all subsets")
    
    for input_file in args.input_files:
        if not input_file.exists():
            print(f"✗ File not found: {input_file}")
            continue
        
        process_file(input_file, args.output_dir, args.subset)
    
    print("\n" + "=" * 60)
    print("✓ Subset generation complete!")
    print(f"Output directory: {args.output_dir.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
