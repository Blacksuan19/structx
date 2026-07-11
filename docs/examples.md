# Examples

This document contains examples of using the structx library for structured data extraction from unstructured documents.

*Generated on: 2026-07-10 23:07:27*

## Setup

```python
from structx import Extractor
from pathlib import Path
import os

# Initialize the extractor
extractor = Extractor.from_litellm(
    model="openai/gpt-4o",
    api_key="your-api-key"
)
```

## Sample Documents

The following examples use a legal document (consultancy agreement) and a receipt (invoice).
1. Consultancy Agreement: `scripts/example_input/free-consultancy-agreement.docx`
2. Invoice PDF: `scripts/example_input/S0305SampleInvoice.pdf`

## Example 1: Extracting Key Terms from a Legal Agreement

This example demonstrates extracting key information from a DOCX file containing a consultancy agreement.

```python
# Define the path to the document
agreement_path = Path("scripts/example_input/free-consultancy-agreement.docx")

# Define the extraction query
query = "summarize the main terms and conditions of this consultancy agreement, focusing on the key obligations, deliverables, and payment terms."
result = extractor.extract(data=agreement_path, query=query)

# Access the extraction results
print(f"Processed {result.success_count} rows with {result.success_rate:.1f}% success rate")
print(result.data)
```

### Results:

Processed 1 rows with 100.0% success rate

### Token Usage:
Total tokens used: 11127

Tokens by step:

- schema_generation: 1431 tokens

- extraction: 9696 tokens


```json
[
  {
    "key_obligations": [
      "The Consultant must provide Services with reasonable skill and care or as per standards expected from a leading service provider in the industry.",
      "The Client must provide feedback on Consultant's proposals promptly."
    ],
    "deliverables": [
      "Deliverables to be delivered by the Consultant as specified in Part 2 of Schedule 1.",
      "Consultant to ensure Deliverables conform with requirements and are free from material defects."
    ],
    "payment_terms": [
      "The Client must pay Charges to the Consultant as invoiced, within 30 days of receipt.",
      "Interest on overdue payments will be charged at the rate of 8% per annum above the Bank of England base rate.",
      "Invoices may be issued at various specified times, including after services are delivered or in advance."
    ]
  }
]
```

<details>
<summary>Generated Model: `ConsultancyAgreementTerms`</summary>


```json
{
  "description": "Extracted main terms including obligations, deliverables, and payment terms from a consultancy agreement.",
  "properties": {
    "key_obligations": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Key obligations of the consultant and client as outlined in the agreement.",
      "title": "Key Obligations"
    },
    "deliverables": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Deliverables expected from the consultant as outlined in the document.",
      "title": "Deliverables"
    },
    "payment_terms": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Terms related to payment including schedule and conditions.",
      "title": "Payment Terms"
    }
  },
  "title": "ConsultancyAgreementTerms",
  "type": "object"
}
```

</details>

## Example 2: Extracting Details from an Invoice PDF

This example showcases extracting structured data from a PDF invoice, including line items.

```python
# Define the path to the PDF
invoice_path = Path("scripts/example_input/S0305SampleInvoice.pdf")

# Define the extraction query
query = "this is an invoice for professional services rendered, extract the professional name, service description, hourly rate and total amount."
result = extractor.extract(data=invoice_path, query=query)
```

### Results:

Processed 6 rows with 100.0% success rate

### Token Usage:
Total tokens used: 5769

Tokens by step:

- schema_generation: 4286 tokens

- extraction: 1483 tokens


```json
[
  {
    "professional_name": "JJJ",
    "service_description": "Telephone conference with defense attorney regarding scheduling of Ms. Client\u2019s deposition",
    "hourly_rate": "175",
    "total_amount": "17.5"
  },
  {
    "professional_name": "JJJ",
    "service_description": "Meeting with Ms. Client to review file and prepare for her deposition",
    "hourly_rate": "175",
    "total_amount": "262.5"
  },
  {
    "professional_name": "JJJ",
    "service_description": "Attend the deposition of Ms. Client",
    "hourly_rate": "175",
    "total_amount": "700"
  },
  {
    "professional_name": "MLT",
    "service_description": "Review and summarize deposition of Ms. Client",
    "hourly_rate": "75",
    "total_amount": "112.5"
  },
  {
    "professional_name": "JJJ",
    "service_description": "Prepare Motion for Summary Judgment, Memorandum in Support of Motion for Summary Judgment, and Affidavit of Ms. Client",
    "hourly_rate": "175",
    "total_amount": "525"
  },
  {
    "professional_name": "MLT",
    "service_description": "Court run to Civil District Court to file Motion for Summary Judgment; obtain hearing date from division; walk through service to Sheriff",
    "hourly_rate": "75",
    "total_amount": "75"
  }
]
```

<details>
<summary>Generated Model: `ProfessionalServiceInvoice`</summary>


```json
{
  "description": "Model to extract details of professional services from invoices, including professional name, service description, hourly rate, and total amount.",
  "properties": {
    "professional_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The name of the professional who rendered the service.",
      "title": "Professional Name"
    },
    "service_description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Description of the professional service rendered.",
      "title": "Service Description"
    },
    "hourly_rate": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "pattern": "^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Hourly rate charged for the service.",
      "title": "Hourly Rate"
    },
    "total_amount": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "pattern": "^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Total amount charged for the services rendered in the invoice.",
      "title": "Total Amount"
    }
  },
  "title": "ProfessionalServiceInvoice",
  "type": "object"
}
```

</details>

## Example 3: Preview Generated Schema for Legal Clauses

This example shows how to generate and inspect a schema for extracting specific clauses from a legal document without performing a full extraction.

```python
# Generate schema for a specific legal clause
query = "extract the confidentiality clause, including the definition of confidential information and the duration of the obligation."
agreement_path = Path("scripts/example_input/free-consultancy-agreement.docx")
DataModel = extractor.get_schema(query=query, data=agreement_path)

# Print schema
print(DataModel.model_json_schema())
```

### Token Usage for Schema Generation Process:

### Token Usage:
Total tokens used: 5697

Tokens by step:

- schema_generation: 5697 tokens


<details>
<summary>Generated Schema</summary>


```json
{
  "$defs": {
    "ConfidentialityClauseExtractionconfidentiality_clause": {
      "description": "Structured representation of the confidentiality clause.",
      "properties": {
        "title": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The title of the confidentiality clause.",
          "title": "Title"
        },
        "definition_of_confidential_information": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Text defining 'Confidential Information' within the clause.",
          "title": "Definition Of Confidential Information"
        },
        "duration_of_obligation": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Duration for which the confidentiality obligation is valid.",
          "title": "Duration Of Obligation"
        }
      },
      "title": "ConfidentialityClauseExtractionconfidentiality_clause",
      "type": "object"
    }
  },
  "description": "Extraction model to retrieve confidentiality clauses from consultancy agreements, focusing on the definition of confidential information and the duration of obligations.",
  "properties": {
    "pdf_path": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The file path of the PDF document containing the confidentiality clause.",
      "title": "Pdf Path"
    },
    "confidentiality_clause": {
      "anyOf": [
        {
          "$ref": "#/$defs/ConfidentialityClauseExtractionconfidentiality_clause"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Structured representation of the confidentiality clause."
    }
  },
  "title": "ConfidentialityClauseExtraction",
  "type": "object"
}
```

</details>
