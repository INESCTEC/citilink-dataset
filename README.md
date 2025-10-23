# CitiLink-Minutes: A Multilayer Annotated Dataset of Municipal Meeting Minutes

**[Try our interactive Dataset Dashboard](https://dataset.citilink.inesctec.pt)**

(The demo is password-protected. To access the platform, please visit this [link](https://rdm.inesctec.pt/dataset/cs-2025-007) and request access to the dataset.)
## Description

The CitiLink-Minutes Dataset is a comprehensive collection of Portuguese municipal council meeting minutes, providing structured and annotated data from local government proceedings. This dataset contains **over a million tokens** with comprehensive multilayer annotations covering (1) **metadata**, (2) **subjects of discussion**, and (3) **voting outcomes**, totaling **over 38,000 individual annotations** across six Portuguese municipalities.

**What this project does:**
This dataset provides researchers, data scientists, and civic tech developers with access to structured municipal governance data, enabling analysis of local government decision-making, voting patterns, policy discussions, and civic participation across different Portuguese municipalities.

**Who it is for:**
- Researchers studying local governance and public administration
- Data scientists working on natural language processing and text mining
- Civic tech developers building transparency and accountability tools
- Political scientists analyzing voting behavior and policy trends
- Journalists investigating municipal government activities

**The problem it solves:**
Municipal meeting minutes are typically published as unstructured PDF or text documents, making it difficult to extract insights, perform comparative analysis, or track specific topics across time and municipalities. This dataset transforms these documents into a structured, queryable format with rich metadata and annotations, including participant information, voting records, agenda items, discussion themes, and temporal data.

## Project Status

This project is currently **completed and stable**. The dataset represents a snapshot of municipal meeting minutes from the covered municipalities. Updates may be released periodically to include additional meetings or municipalities.

## Dataset Statistics

| **Municipality** | **Tokens** | **Entities** | **Relations** |
|------------------|------------|--------------|---------------|
| Alandroal        | 51,987     | 2,902        | 1,796         |
| Campo Maior      | 161,889    | 4,187        | 1,474         |
| Covilhã          | 235,381    | 4,518        | 2,585         |
| Fundão           | 189,128    | 1,915        | 983           |
| Guimarães        | 206,361    | 3,547        | 2,154         |
| Porto            | 151,766    | 3,306        | 2,170         | 
| **Total**        | **1,016,825** | **20,375** | **11,162**   |

**Key Metrics:**
- **Tokens**: Total number of words/tokens in meeting minutes
- **Entities**: Annotated entities (participants, dates, locations, organizations, etc.)
- **Relations**: Annotated relationships between entities (voting records, participations, etc.)

## Dataset Structure

The dataset is organized into 6 JSON files, one per municipality:

```
data/
├── Alandroal.json
├── Campomaior.json
├── Covilha.json
├── Fundao.json
├── Guimaraes.json
└── Porto.json
```

### JSON Schema

Each JSON file follows this hierarchical structure:

```json
{
  "municipalities": [
    {
      "municipality": "string",           // Municipality name
      "minutes": [
        {
          "minute_id": "string",        // Unique identifier (format: Municipality_cm_XXX_YYYY-MM-DD)
          "full_text": "string",          // Complete meeting minutes text
          "personal_info": [
            "text": "string",
            "start": number,
            "end": number
          ],
          "metadata": {
            "municipality": "string",
            "year": "string",
            "minute_number": {
              "text": "string",
              "start": number,            // Character offset in full_text
              "end": number
            },
            "date": {
              "text": "string",
              "start": number,
              "end": number
            },
            "location": {
              "text": "string",
              "start": number,
              "end": number
            },
            "meeting_type": {
              "text": "string",
              "start": number,
              "end": number,
              "type": "string"           // e.g., "ordinary", "extraordinary"
            },
            "begin_time": {
              "text": "string",
              "start": number,
              "end": number
            },
            "end_time": {
              "text": "string",
              "start": number,
              "end": number
            },
            "participants": [
              {
                "name": "string",
                "type": "string",         // e.g., "president", "vice_president", "councilors", "staff"
                "start": number,
                "end": number,
                "party": "string",        // Political party affiliation
                "present": "string"       // "present" or "absent"
              }
            ]
          },
          "agenda_items": [
            {
              "item_id": number,          // Sequential agenda item number
              "item_title": "string",     // Agenda item title
              "subjects": [
                {
                  "subject_id": "string",
                  "text": "string",       // Discussion text
                  "start": number,
                  "end": number,
                  "subject": {
                    "text": "string",
                    "start": number,
                    "end": number
                  },
                  "voting": [
                    {
                      "voters": {
                        "in_favor": [
                          {
                            "text": "string",
                            "start": number,
                            "end": number
                          }
                        ],
                        "against": [],
                        "abstention": []
                      },
                      "non_voters": [],
                      "global_tally": {
                        "text": "string",
                        "start": number,
                        "end": number,
                        "type": "string"  // e.g., "unanimous", "majority"
                      },
                      "voting_evidence": {
                        "text": "string",
                        "start": number,
                        "end": number
                      }
                    }
                  ],
                  "theme": "string",      // Subject theme/summary
                  "topics": [             // Categorized topics
                    "string"
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### Data Format

The CitiLink-Minutes dataset is provided in JSON format.

| **Field** | **Description** |
|-----------|-----------------|
| `municipality` | Name of the municipality (e.g., "Alandroal", "Porto") |
| `minute_id` | Unique identifier for each meeting minute (format: `Municipality_cm_XXX_YYYY-MM-DD`) |
| `full_text` | Complete text of the meeting minutes. Format: utf-8, not tokenized, includes newlines |
| `personal_info` | List of anonymised personal information identifiers |
| `metadata` | Structured metadata containing meeting information (date, location, participants, etc.) |
| `year` | Year of the meeting |
| `minute_number` | Official minute number with character offsets in `full_text` |
| `date` | Meeting date with character offsets |
| `location` | Meeting location with character offsets |
| `meeting_type` | Type of meeting (e.g., "ordinary", "extraordinary") with character offsets |
| `begin_time` | Meeting start time with character offsets |
| `end_time` | Meeting end time with character offsets |
| `participants` | List of meeting participants with roles, party affiliations, and attendance status |
| `name` | Participant name |
| `type` | Participant role (e.g., "president", "vice_president", "councilors", "staff") |
| `party` | Political party affiliation |
| `present` | Attendance status ("present" or "absent") |
| `start` | Begin offset in the document. Format: number of characters starting at 0. Newlines and escaped symbols count as one character |
| `end` | End offset in the document. Format: number of characters |
| `agenda_items` | List of agenda items discussed in the meeting |
| `item_id` | Sequential agenda item number |
| `item_title` | Title of the agenda item |
| `subjects` | List of discussion subjects within an agenda item |
| `subject_id` | Unique identifier for the subject |
| `text` | Full text of the subject discussion |
| `subject` | Summary or key point of the subject with character offsets |
| `voting` | List of voting records for the subject |
| `voters` | Structured voting information (in_favor, against, abstention) |
| `in_favor` | List of voters who voted in favor |
| `against` | List of voters who voted against |
| `abstention` | List of voters who abstained |
| `non_voters` | List of participants who did not vote |
| `global_tally` | Overall voting result with character offsets |
| `type` | Result type (e.g., "unanimous", "majority") |
| `voting_evidence` | Textual evidence of the voting outcome with character offsets |
| `theme` | Subject theme or summary |
| `topics` | List of categorized topics for the subject |

**Note:** Character offsets (`start` and `end`) reference positions in the `full_text` field, enabling precise text extraction and span-based annotations.

### Data Anonymization

**Important:** Personal identifiable information (PII) in this dataset has been anonymized to protect privacy. Each asterisk character (`*`) represents one character from the original text.

**Examples:**
- Names: `******************` (18 characters in original name)
- Document numbers: `***` or `*****`
- Identification numbers: `*************`

Political figures holding public office (e.g., mayors, councilors) are **not anonymized** as they are public figures, but staff members and private citizens are anonymized.

### Annotation Guidelines

Detailed annotation instructions, including the annotation procedures quality control measures, and complete schema definitions are available in the document `docs/citilink_annotation_guidelines.pdf`. This guide provides comprehensive information about:

- The annotation process and methodology
- Inter-annotator agreement protocols
- Guidelines for identifying and labeling metadata, participants, voting records, and topics
- Quality assurance procedures
- Schema definitions for all data fields

Researchers and users interested in understanding the dataset structure in depth or replicating the annotation process should consult this document.

## Installation

### Sample Dataset

A **sample dataset** is available in the `sample_data/` folder, containing one municipal meeting minute per municipality (6 total documents).

### Full Dataset

The complete dataset (120 municipal meeting minutes across 6 municipalities) is protected by a Data Use Agreement and will be made available through the following DOI once the associated research paper is accepted for publication:

**DOI:** [https://doi.org/10.25747/7KG6-1K22](https://doi.org/10.25747/7KG6-1K22)

The full dataset contains 20 minutes per municipality with over a million tokens and 38,000+ annotations. Please visit the DOI link to access the complete dataset and review the usage terms.

## Usage

### Dataset Subsets

To facilitate different use cases and reduce data processing overhead, we provide a script to create three specialized subsets of the dataset:

#### Available Subsets

1. **`metadata`** - Contains only metadata annotations
   - Includes: participants, dates, locations, meeting types, times, full_text
   - Excludes: agenda items, subjects, voting records
   - Use case: Analyzing meeting patterns, participant attendance, temporal trends

2. **`subjects_only`** - Contains core subject annotations
   - Includes: subject_id, start, end, subject, theme, topics
   - Excludes: full text, metadata, voting records
   - Use case: Topic classification, Topic Segmentation, QA systems

3. **`subjects_with_votings`** - Contains complete subject annotations
   - Includes: all subject fields including voting records and full_text
   - Excludes: metadata
   - Use case: Voting pattern analysis, decision-making research, subject-focused analysis

#### Creating Subsets

Use the provided `create_subsets.py` script to generate subsets:

```bash
# Generate all subsets for a single municipality
python create_subsets.py data/Alandroal.json

# Generate all subsets for all municipalities
python create_subsets.py data/*.json

# Generate only specific subset(s)
python create_subsets.py data/Alandroal.json --subset metadata
python create_subsets.py data/*.json --subset subjects_only subjects_with_votings

# Specify custom output directory
python create_subsets.py data/*.json --output-dir my_subsets/
```

The script will create the following directory structure:

```
subsets/
├── metadata/
│   ├── Alandroal.json
│   ├── Campomaior.json
│   └── ...
├── subjects_only/
│   ├── Alandroal.json
│   ├── Campomaior.json
│   └── ...
└── subjects_with_votings/
    ├── Alandroal.json
    ├── Campomaior.json
    └── ...
```

**Benefits:**
- Reduced file sizes (30-80% smaller depending on subset)
- Faster loading and processing times
- Focus on specific annotation layers for targeted analysis
- Maintains original dataset structure for compatibility

### Dataset Split

The dataset includes a **temporal train/validation/test split** designed to simulate real-world deployment scenarios. Documents were ordered chronologically and divided into:

- **Training set**: 60% (72 documents) - Earlier minutes
- **Validation set**: 20% (24 documents) - Middle period
- **Test set**: 20% (24 documents) - Most recent minutes

This temporal split ensures that the most recent minutes are reserved for testing, enabling realistic evaluation of model performance on future data. The split information is available in `data/split_info.json`.

**Loading the split:**

```python
import json

# Load split information
with open('data/split_info.json', 'r') as f:
    split_info = json.load(f)

print(f"Train: {split_info['train_count']} documents")
print(f"Val: {split_info['val_count']} documents")
print(f"Test: {split_info['test_count']} documents")

# Example: Load training data
train_files = split_info['train_files']
# Use these filenames to filter your dataset
```

### Loading the Data

**Python:**
```python
import json

# Load a municipality's data
with open('data/Alandroal.json', 'r', encoding='utf-8') as f:
    alandroal_data = json.load(f)

# Access documents
documents = alandroal_data['municipalities'][0]['minutes']

# Or load a subset
with open('subsets/subjects_only/Alandroal.json', 'r', encoding='utf-8') as f:
    subjects_data = json.load(f)
```

### Query Examples

Here are practical examples of what you can extract from this dataset using Python:

#### 1. Get all meeting dates from a municipality

```python
import json

with open('data/Alandroal.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

dates = [doc['metadata']['date']['text'] 
         for doc in data['municipalities'][0]['minutes']]
print(dates)  # ['18/01/2023', '28/09/2022', ...]
```

#### 2. Get all participants who attended meetings

```python
attendees = []
for doc in data['municipalities'][0]['minutes']:
    for participant in doc['metadata']['participants']:
        if participant['present'] == 'present':
            attendees.append(participant['name'])

# Get unique attendees
unique_attendees = list(set(attendees))
```

#### 3. Get all agenda item titles from all meetings

```python
agenda_titles = []
for doc in data['municipalities'][0]['minutes']:
    for item in doc['agenda_items']:
        agenda_titles.append(item['item_title'])
```

#### 4. Find all unanimous voting decisions

```python
unanimous_votes = []
for doc in data['municipalities'][0]['minutes']:
    for item in doc['agenda_items']:
        for subject in item['subjects']:
            for vote in subject.get('voting', []):
                if vote['global_tally']['type'] == 'unanimous':
                    unanimous_votes.append({
                        'minute_id': doc['minute_id'],
                        'subject': subject.get('theme', ''),
                        'vote': vote
                    })
```

#### 5. Get all subjects discussed on a specific topic (e.g., "Environment")

```python
environment_subjects = []
for doc in data['municipalities'][0]['minutes']:
    for item in doc['agenda_items']:
        for subject in item['subjects']:
            if 'Environment' in subject.get('topics', []):
                environment_subjects.append({
                    'minute_id': doc['minute_id'],
                    'theme': subject['theme'],
                    'text': subject['text']
                })
```

## Baselines

The associated research paper establishes baseline performance for three key tasks using this dataset. Metadata and Voting Identification tasks were evaluated using both **encoder-based models** and **LLM-based approaches** with Gemini 2.5 Pro, while Topic Classification employs a **Gradient Boosting ensemble with Active Learning**.

**Fine-tuned Models:** All fine-tuned BERTimbau models for the tasks described below are publicly available in [HuggingFace](https://huggingface.co/collections/liaad/citilink-68f7916f31b9588c4fe2f43b).

### 1. Metadata Identification

Extracting structured metadata from meeting minutes, including participants, dates, locations, meeting types, and temporal information.

**Approaches:**
- **Encoder**: [Portuguese BERT (BERTimbau)](https://huggingface.co/neuralmind/bert-base-portuguese-cased) fine-tuned for token classification
- **LLM**: Gemini 2.5 Pro with structured extraction prompts

**Example Prompt** (Metadata Extraction):
```
Tarefa: Extrair metadados de atas municipais portuguesas a partir do texto fornecido.

Metadados a extrair (classes):
- minute_id: número da ata (texto exato que aparece com "ATA N.º <n>").
- date: data da reunião (formato original como aparece no texto, ex.: "17 DE NOVEMBRO DE 2021").
- meeting_type: tipo de reunião (ex.: "ORDINÁRIA", "EXTRAORDINÁRIA").
- location: local onde decorre a reunião (texto exato, incluindo determinantes ou preposições, ex.: "no Edifício dos Paços do Concelho").
- begin_time: hora de início (texto exato, ex.: "nove horas e trinta minutos" ou "10.35 horas").
- end_time: hora de fim (texto exato, ex.: "dez horas e cinquenta minutos" ou "16:00 horas").
- participant: participante nomeado na abertura, com atributos:
    - type: um de {"president","councillors"} (sem inventar categorias novas)
    - present: "present"|"absent"|"substituted" quando claramente indicado (ex.: "Faltou ...")

Regras:
- Usar o texto exato ("extraction_text") tal como aparece. Não parafrasear.
- Não sobrepor entidades. Se um excerto já foi usado para "minute_id", não o reutilizar para outra entidade.
- Não inventar valores. Se uma classe não estiver presente no texto fornecido, omitir.
- A atribuição de offsets (início/fim) deve corresponder ao texto exato no input.
- Respeitar acentos, maiúsculas/minúsculas e pontuação como no original.
```

### 2. Voting Identification

Identifying voting events, participants' votes, and voting outcomes within meeting discussions.

**Approaches:**
- **Encoder**: [Portuguese BERT (BERTimbau)](https://huggingface.co/neuralmind/bert-base-portuguese-cased) fine-tuned for Named Entity Recognition
- **LLM**: Gemini 2.5 Pro with voting-specific extraction prompt

**Example Prompt** (Voting Extraction):
```
Extract all voting entities from Portuguese municipal council meeting minutes.
Entity Types:
- VOTER-FAVOR: Participants who voted in favor
- VOTER-AGAINST: Participants who voted against
- VOTER-ABSTENTION: Participants who abstained
- VOTER-ABSENT: Participants who were absent
- SUBJECT: The subject being voted on
- VOTING: Voting action expressions (deliberou, votou, etc.)
- COUNTING-MAJORITY: Expressions indicating majority voting (por maioria)
- COUNTING-UNANIMITY: Expressions indicating unanimous voting (por unanimidade)
Extract the exact text spans as they appear in the document.
```

### 3. Topic Classification

Categorizing discussion subjects into thematic topics (e.g., Environment, Education, Infrastructure).

**Approaches:**
- **Encoder**: [Portuguese BERT (BERTimbau)](https://huggingface.co/neuralmind/bert-base-portuguese-cased) fine-tuned for multi-label classification
- **LLM**: Gemini 2.5 Pro with a Topic Classication prompt

**Example Prompt** (Topic Classification):
```
You are an expert in classifying Portuguese municipal council meeting minutes.
Available Topics (you MUST choose ONLY from this list):
{labels_str}
Examples from Training Data:
{examples_str}
Now, classify this new text:
{text}
Instructions:
1. Read the text carefully
2. Identify ALL topics that are discussed or mentioned (like in the examples above)
3. Return ONLY the topic names, separated by commas
4. Use the EXACT names from the available topics list
5. If multiple topics apply, list all of them
6. If no topics clearly apply, return "Nenhum"
Your Response (topic names only, comma-separated):
```

**Note:** Detailed baseline results, evaluation metrics, and implementation details are provided in the associated research paper.

## License

[CC-BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/deed.en)

This work is licensed under the Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License.

**You are free to:**
- Share — copy and redistribute the material in any medium or format

**Under the following terms:**
- Attribution — You must give appropriate credit
- NonCommercial — You may not use the material for commercial purposes
- NoDerivatives — If you remix, transform, or build upon the material, you may not distribute the modified material

## Documentation and Resources

- **[Citilink](https://citilink.inesctec.pt/)**
- **[Demo](https://citilink.inesctec.pt/dataset-demo/)**
 - **[Annotation Guidelines:](docs/citilink_annotation_guidelines.pdf)** (detailed annotation instructions and schema)

### Citation

If you use this dataset in your research, please cite:

```bibtex
@dataset{citilink2025,
  author       = {Ricardo Campos and Ana Filipa Pacheco and Ana Luísa Fernandes and Inês Cantante and Rute Rebouças and Luís Filipe Cunha and José Isidro and José Evans and Miguel Marques and Rodrigo Batista and Evelin Amorim and Alípio Jorge and Nuno Guimarães and Sérgio Nunes and António Leal and Purificação Silvano},
  title        = {CitiLink-Minutes: A Multilayer Annotated Dataset of Municipal Meeting Minutes},
  year         = {2025},
  doi          = {https://doi.org/10.25747/7KG6-1K22},
  institution  = {INESC TEC}
}
```

## Credits and Acknowledgements

This dataset was developed by **[INESCTEC  (Institute for Systems and Computer Engineering, Technology and Science)](https://www.inesctec.pt)**, specifically by the **[NLP](https://nlp.inesctec.pt/)** research group, part of the **[LIAAD (Laboratory of Artificial Intelligence and Decision Support)](https://www.inesctec.pt/pt/centros/LIAAD)** center.

### Affiliated Institutions

- [University of Beira Interior (UBI)](https://www.ubi.pt/en/)
- [University of Porto (UP)](https://www.up.pt/portal/en/)

### Acknowledgements

- The municipalities of Alandroal, Campo Maior, Covilhã, Fundão, Guimarães, and Porto for making their meeting minutes publicly available
- All contributors who participated in the data annotation and validation process

## Contacts

For support, questions, or collaboration inquiries:

citilink@inesctec.pt

For bug reports or feature requests:
- Open an issue in the [GitHub repository](https://github.com/INESCTEC/citilink-dataset/issues)

---
