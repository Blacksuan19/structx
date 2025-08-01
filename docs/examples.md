# Examples

This document contains examples of using the structx library for structured data extraction from unstructured documents.

*Generated on: 2025-07-31 22:22:37*

## Setup

```python
from structx import Extractor
from pathlib import Path
import os

# Initialize the extractor
extractor = Extractor.from_litellm(
    model="gpt-4o",
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
result = extractor.extract(agreement_path, query)

# Access the extraction results
print(f"Extracted {result.success_count} items with {result.success_rate:.1f}% success rate")
print(result.data)
```

### Results:

Extracted 1 items with 100.0% success rate

### Token Usage:
Total tokens used: 18638

Tokens by step:

- refinement: 306 tokens

- schema_generation: 1205 tokens

- guide: 454 tokens

- extraction: 16673 tokens


```json
[
  {
    "legal_terms_and_conditions": {
      "term": "This agreement includes terms related to the provision of consultancy services, deliverables, intellectual property rights, payment terms, warranties, limitations of liability, termination, and subcontracting. The agreement is governed by English law and subject to the exclusive jurisdiction of English courts."
    },
    "obligations_of_parties": {
      "consultant_obligations": {
        "obligation": "The Consultant shall provide the Services with reasonable skill and care, deliver the Deliverables according to the agreed timetable, and ensure that the Deliverables conform to the specified requirements and are free from material defects."
      },
      "client_obligations": {
        "obligation": "The Client must provide feedback on the Consultant's proposals and pay the Charges within 30 days of receiving an invoice."
      }
    },
    "deliverables": {
      "deliverable": "Deliverables as specified in Part 2 of Schedule 1",
      "deadline": null
    },
    "payment_terms": {
      "payment_term": "The Client shall pay the Charges to the Consultant within 30 days of receiving an invoice. Late payments may incur interest at 8% per annum above the Bank of England base rate.",
      "due_date": null
    }
  }
]
```

<details>
<summary>Generated Model: `ConsultancyAgreementTerms`</summary>


```json
{
  "$defs": {
    "ConsultancyAgreementTermsdeliverables": {
      "description": "List of deliverables expected from the consultancy, ordered chronologically by deadline.",
      "properties": {
        "deliverable": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "A specific deliverable item.",
          "title": "Deliverable"
        },
        "deadline": {
          "anyOf": [
            {
              "format": "date",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The deadline for the deliverable.",
          "title": "Deadline"
        }
      },
      "title": "ConsultancyAgreementTermsdeliverables",
      "type": "object"
    },
    "ConsultancyAgreementTermslegal_terms_and_conditions": {
      "description": "A collection of legal terms and conditions outlined in the agreement.",
      "properties": {
        "term": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "A specific legal term or condition.",
          "title": "Term"
        }
      },
      "title": "ConsultancyAgreementTermslegal_terms_and_conditions",
      "type": "object"
    },
    "ConsultancyAgreementTermsobligations_of_parties": {
      "description": "Key obligations of the parties involved in the agreement.",
      "properties": {
        "consultant_obligations": {
          "anyOf": [
            {
              "$ref": "#/$defs/obligations_of_partiesconsultant_obligations"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Obligations specific to the consultant."
        },
        "client_obligations": {
          "anyOf": [
            {
              "$ref": "#/$defs/obligations_of_partiesclient_obligations"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Obligations specific to the client."
        }
      },
      "title": "ConsultancyAgreementTermsobligations_of_parties",
      "type": "object"
    },
    "ConsultancyAgreementTermspayment_terms": {
      "description": "Payment terms organized by due date.",
      "properties": {
        "payment_term": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "A specific payment term.",
          "title": "Payment Term"
        },
        "due_date": {
          "anyOf": [
            {
              "format": "date",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The due date for the payment term.",
          "title": "Due Date"
        }
      },
      "title": "ConsultancyAgreementTermspayment_terms",
      "type": "object"
    },
    "obligations_of_partiesclient_obligations": {
      "description": "Obligations specific to the client.",
      "properties": {
        "obligation": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "A specific obligation of the client.",
          "title": "Obligation"
        }
      },
      "title": "obligations_of_partiesclient_obligations",
      "type": "object"
    },
    "obligations_of_partiesconsultant_obligations": {
      "description": "Obligations specific to the consultant.",
      "properties": {
        "obligation": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "A specific obligation of the consultant.",
          "title": "Obligation"
        }
      },
      "title": "obligations_of_partiesconsultant_obligations",
      "type": "object"
    }
  },
  "description": "Extract and summarize the main terms and conditions of a consultancy agreement, focusing on key obligations, deliverables, and payment terms.",
  "properties": {
    "legal_terms_and_conditions": {
      "anyOf": [
        {
          "$ref": "#/$defs/ConsultancyAgreementTermslegal_terms_and_conditions"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "A collection of legal terms and conditions outlined in the agreement."
    },
    "obligations_of_parties": {
      "anyOf": [
        {
          "$ref": "#/$defs/ConsultancyAgreementTermsobligations_of_parties"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Key obligations of the parties involved in the agreement."
    },
    "deliverables": {
      "anyOf": [
        {
          "$ref": "#/$defs/ConsultancyAgreementTermsdeliverables"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "List of deliverables expected from the consultancy, ordered chronologically by deadline."
    },
    "payment_terms": {
      "anyOf": [
        {
          "$ref": "#/$defs/ConsultancyAgreementTermspayment_terms"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Payment terms organized by due date."
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
result = extractor.extract(invoice_path, query)
```

### Results:

Extracted 6 items with 100.0% success rate

### Token Usage:
Total tokens used: 3323

Tokens by step:

- refinement: 376 tokens

- schema_generation: 1005 tokens

- guide: 519 tokens

- extraction: 1423 tokens


```json
[
  {
    "Professional Name": "JJJ",
    "Service Description": "Telephone conference with defense attorney regarding scheduling of Ms. Client\u2019s deposition",
    "Hourly Rate": 175.0,
    "Total Amount": 17.5
  },
  {
    "Professional Name": "JJJ",
    "Service Description": "Meeting with Ms. Client to review file and prepare for her deposition",
    "Hourly Rate": 175.0,
    "Total Amount": 262.5
  },
  {
    "Professional Name": "JJJ",
    "Service Description": "Attend the deposition of Ms. Client",
    "Hourly Rate": 175.0,
    "Total Amount": 700.0
  },
  {
    "Professional Name": "MLT",
    "Service Description": "Review and summarize deposition of Ms. Client",
    "Hourly Rate": 75.0,
    "Total Amount": 112.5
  },
  {
    "Professional Name": "JJJ",
    "Service Description": "Prepare Motion for Summary Judgment, Memorandum in Support of Motion for Summary Judgment, and Affidavit of Ms. Client",
    "Hourly Rate": 175.0,
    "Total Amount": 525.0
  },
  {
    "Professional Name": "MLT",
    "Service Description": "Court run to Civil District Court to file Motion for Summary Judgment; obtain hearing date from division; walk through service to Sheriff",
    "Hourly Rate": 75.0,
    "Total Amount": 75.0
  }
]
```

<details>
<summary>Generated Model: `InvoiceExtractionModel`</summary>


```json
{
  "description": "Extracts details from an invoice for professional services rendered.",
  "properties": {
    "Professional Name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The name of the individual or entity providing the service.",
      "title": "Professional Name"
    },
    "Service Description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "A detailed description of the services provided.",
      "title": "Service Description"
    },
    "Hourly Rate": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The rate charged per hour for the services.",
      "title": "Hourly Rate"
    },
    "Total Amount": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The total amount charged for the services rendered.",
      "title": "Total Amount"
    }
  },
  "title": "InvoiceExtractionModel",
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
Total tokens used: 3031

Tokens by step:

- refinement: 286 tokens

- schema_generation: 2325 tokens

- guide: 420 tokens

- extraction: 0 tokens


<details>
<summary>Generated Schema</summary>


```json
{
  "description": "Extracts the confidentiality clause from legal documents, including the definition of 'Confidential Information' and the duration of the confidentiality obligation.",
  "properties": {
    "confidentiality_clause": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The full text of the confidentiality clause.",
      "title": "Confidentiality Clause"
    },
    "confidential_information_definition": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The definition of 'Confidential Information' as specified in the document.",
      "title": "Confidential Information Definition"
    },
    "confidentiality_duration": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The duration for which the confidentiality obligation is in effect.",
      "title": "Confidentiality Duration"
    }
  },
  "title": "ConfidentialityClauseExtraction",
  "type": "object"
}
```

</details>
