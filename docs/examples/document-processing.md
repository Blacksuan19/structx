# Document Processing

This example demonstrates how to extract structured information from various
document types.

## Processing PDF Documents

First, install the PDF dependencies:

```bash
pip install structx[pdf]
```

Then extract data from PDF files:

```python
from structx import Extractor

# Initialize extractor
extractor = Extractor.from_litellm(
    model="gpt-4o-mini",
    api_key="your-api-key"
)

# Extract from PDF
result = extractor.extract(
    data="annual_report.pdf",
    query="""
    extract financial metrics including:
    - revenue
    - profit
    - growth rate
    - key performance indicators
    """,
    chunk_size=2000,  # Larger chunks for financial documents
    overlap=200       # Ensure context is maintained
)

print(f"Extracted {result.success_count} financial metrics")
for item in result.data:
    print(f"Revenue: {item.revenue}")
    print(f"Profit: {item.profit}")
    print(f"Growth: {item.growth_rate}")
    print(f"KPIs: {item.key_performance_indicators}")
```

## Processing Word Documents

First, install the DOCX dependencies:

```bash
pip install structx[docx]
```

Then extract data from Word files:

```python
# Extract from DOCX
result = extractor.extract(
    data="project_report.docx",
    query="""
    extract project information including:
    - project name
    - start date
    - end date
    - key milestones
    - team members
    - budget
    """,
    chunk_size=1500,
    overlap=150
)

print(f"Extracted {result.success_count} project details")
for item in result.data:
    print(f"Project: {item.project_name}")
    print(f"Duration: {item.start_date} to {item.end_date}")
    print(f"Budget: {item.budget}")
    print(f"Team: {', '.join(item.team_members)}")
    print(f"Milestones: {item.key_milestones}")
```

## Processing Multiple Documents

```python
import os
import pandas as pd
from tqdm import tqdm

def process_document_folder(folder_path, query):
    """Process all documents in a folder"""
    results = []
    files = [f for f in os.listdir(folder_path) if f.endswith(('.pdf', '.docx', '.txt'))]

    for file in tqdm(files, desc="Processing documents"):
        file_path = os.path.join(folder_path, file)
        try:
            result = extractor.extract(
                data=file_path,
                query=query
            )

            # Add file information
            for item in result.data:
                item_dict = item.model_dump()
                item_dict['source_file'] = file
                results.append(item_dict)

        except Exception as e:
            print(f"Error processing {file}: {e}")

    # Combine all results
    return pd.DataFrame(results)

# Process all documents in a folder
documents_df = process_document_folder(
    "documents/",
    "extract key dates, people mentioned, and organizations"
)

print(f"Processed {len(documents_df)} entries from multiple documents")
print(documents_df.head())

# Analyze results
print("\nMost mentioned organizations:")
print(documents_df['organizations'].explode().value_counts().head(10))

print("\nDate distribution:")
documents_df['key_dates'] = pd.to_datetime(documents_df['key_dates'])
print(documents_df['key_dates'].dt.year.value_counts().sort_index())
```

## Document Comparison

```python
def compare_documents(doc1_path, doc2_path, query):
    """Compare information extracted from two documents"""
    # Extract from first document
    result1 = extractor.extract(
        data=doc1_path,
        query=query
    )

    # Extract from second document
    result2 = extractor.extract(
        data=doc2_path,
        query=query
    )

    # Convert to DataFrames
    df1 = pd.DataFrame([item.model_dump() for item in result1.data])
    df2 = pd.DataFrame([item.model_dump() for item in result2.data])

    # Add source column
    df1['source'] = os.path.basename(doc1_path)
    df2['source'] = os.path.basename(doc2_path)

    # Combine results
    combined = pd.concat([df1, df2])

    return combined

# Compare two versions of a document
comparison = compare_documents(
    "documents/report_v1.pdf",
    "documents/report_v2.pdf",
    "extract key findings, recommendations, and metrics"
)

print("Document comparison:")
print(comparison.groupby('source')['key_findings'].count())

# Find differences in recommendations
from difflib import SequenceMatcher

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

recommendations1 = set(comparison[comparison['source'] == 'report_v1.pdf']['recommendations'].explode())
recommendations2 = set(comparison[comparison['source'] == 'report_v2.pdf']['recommendations'].explode())

print("\nUnique to version 1:")
for rec in recommendations1 - recommendations2:
    print(f"- {rec}")

print("\nUnique to version 2:")
for rec in recommendations2 - recommendations1:
    print(f"- {rec}")
```

## Document Summarization

```python
def summarize_document(doc_path):
    """Extract a structured summary from a document"""
    result = extractor.extract(
        data=doc_path,
        query="""
        extract document summary including:
        - title
        - authors
        - publication date
        - key topics
        - main findings
        - executive summary
        """
    )

    if result.success_count > 0:
        return result.data[0]
    else:
        return None

# Summarize a document
summary = summarize_document("documents/research_paper.pdf")

if summary:
    print(f"Title: {summary.title}")
    print(f"Authors: {', '.join(summary.authors)}")
    print(f"Published: {summary.publication_date}")
    print(f"Topics: {', '.join(summary.key_topics)}")
    print("\nExecutive Summary:")
    print(summary.executive_summary)
```
