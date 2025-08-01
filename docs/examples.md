# Examples

This document contains examples of using the structx library for structured data extraction from unstructured documents.

*Generated on: 2025-07-31 20:16:34*

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
Total tokens used: 10098
Tokens by step:
- refinement: 309 tokens

- schema_generation: 1177 tokens

- guide: 446 tokens

- extraction: 8166 tokens


```json
[
  {
    "legal_terms_and_conditions": [
      {
        "term": "The Consultant shall provide the Services with reasonable skill and care."
      },
      {
        "term": "The Client must provide written feedback concerning the Consultant's proposals."
      },
      {
        "term": "The Consultant warrants that the Deliverables will conform with the requirements and be free from material defects."
      }
    ],
    "obligations_of_parties": [
      {
        "party": "Consultant",
        "obligation": "Provide the Services to the Client in accordance with the Agreement."
      },
      {
        "party": "Consultant",
        "obligation": "Deliver the Deliverables to the Client."
      },
      {
        "party": "Client",
        "obligation": "Provide written feedback to the Consultant concerning proposals and materials."
      }
    ],
    "deliverables": [
      {
        "deliverable": "Deliverables specified in Part 2 of Schedule 1",
        "due_date": "As per the timetable set out in Part 3 of Schedule 1"
      }
    ],
    "payment_terms": [
      {
        "payment_schedule": "Invoices issued from time to time during the Term or on invoicing dates set out in Part 5 of Schedule 1",
        "payment_condition": "Client must pay within 30 days following the issue of an invoice."
      }
    ]
  }
]
```

<details>
<summary>Generated Model: `ConsultancyAgreementTerms`</summary>


```json
{
  "$defs": {
    "ConsultancyAgreementTermsdeliverablesItem": {
      "description": "Organized deliverables in a sequential manner to reflect the order of completion.",
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
          "description": "Description of the deliverable.",
          "title": "Deliverable"
        },
        "due_date": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The due date for the deliverable.",
          "title": "Due Date"
        }
      },
      "title": "ConsultancyAgreementTermsdeliverablesItem",
      "type": "object"
    },
    "ConsultancyAgreementTermslegal_terms_and_conditionsItem": {
      "description": "Grouped related legal terms and conditions for clarity.",
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
      "title": "ConsultancyAgreementTermslegal_terms_and_conditionsItem",
      "type": "object"
    },
    "ConsultancyAgreementTermsobligations_of_partiesItem": {
      "description": "Clearly outlined obligations of the parties involved, easy to reference.",
      "properties": {
        "party": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The party responsible for the obligation, either 'Consultant' or 'Client'.",
          "title": "Party"
        },
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
          "description": "Description of the obligation.",
          "title": "Obligation"
        }
      },
      "title": "ConsultancyAgreementTermsobligations_of_partiesItem",
      "type": "object"
    },
    "ConsultancyAgreementTermspayment_termsItem": {
      "description": "Organized payment terms to reflect the schedule and conditions of payments.",
      "properties": {
        "payment_schedule": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The schedule of payments.",
          "title": "Payment Schedule"
        },
        "payment_condition": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Conditions under which payments are made.",
          "title": "Payment Condition"
        }
      },
      "title": "ConsultancyAgreementTermspayment_termsItem",
      "type": "object"
    }
  },
  "description": "Extract and summarize the main terms and conditions of a consultancy agreement, focusing on key obligations, deliverables, and payment terms.",
  "properties": {
    "legal_terms_and_conditions": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/ConsultancyAgreementTermslegal_terms_and_conditionsItem"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Grouped related legal terms and conditions for clarity.",
      "title": "Legal Terms And Conditions"
    },
    "obligations_of_parties": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/ConsultancyAgreementTermsobligations_of_partiesItem"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Clearly outlined obligations of the parties involved, easy to reference.",
      "title": "Obligations Of Parties"
    },
    "deliverables": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/ConsultancyAgreementTermsdeliverablesItem"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Organized deliverables in a sequential manner to reflect the order of completion.",
      "title": "Deliverables"
    },
    "payment_terms": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/ConsultancyAgreementTermspayment_termsItem"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Organized payment terms to reflect the schedule and conditions of payments.",
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
result = extractor.extract(invoice_path, query)
```

### Results:

Extracted 1 items with 100.0% success rate

### Token Usage:
Total tokens used: 5932
Tokens by step:
- refinement: 1180 tokens

- schema_generation: 2744 tokens

- guide: 518 tokens

- extraction: 1490 tokens


```json
[
  {
    "Professional Name": "FIRM NAME",
    "Services": [
      {
        "Service Description": "Telephone conference with defense attorney regarding scheduling of Ms. Client\u2019s deposition",
        "Hourly Rate": 175.0,
        "Amount": 17.5
      },
      {
        "Service Description": "Meeting with Ms. Client to review file and prepare for her deposition",
        "Hourly Rate": 175.0,
        "Amount": 262.5
      },
      {
        "Service Description": "Attend the deposition of Ms. Client",
        "Hourly Rate": 175.0,
        "Amount": 700.0
      },
      {
        "Service Description": "Review and summarize deposition of Ms. Client",
        "Hourly Rate": 75.0,
        "Amount": 112.5
      },
      {
        "Service Description": "Prepare Motion for Summary Judgment, Memorandum in Support of Motion for Summary Judgment, and Affidavit of Ms. Client",
        "Hourly Rate": 175.0,
        "Amount": 525.0
      },
      {
        "Service Description": "Court run to Civil District Court to file Motion for Summary Judgment; obtain hearing date from division; walk through service to Sheriff",
        "Hourly Rate": 75.0,
        "Amount": 75.0
      }
    ],
    "Total Amount": 1692.5
  }
]
```

<details>
<summary>Generated Model: `InvoiceExtractionModel`</summary>


```json
{
  "$defs": {
    "InvoiceExtractionModelServicesItem": {
      "description": "A list of services provided, including descriptions, hourly rates, and amounts.",
      "properties": {
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
          "description": "A detailed text description of the services provided.",
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
          "format": "Must be formatted to two decimal places.",
          "title": "Hourly Rate"
        },
        "Amount": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The total amount charged for the specific service rendered.",
          "format": "Must be formatted to two decimal places.",
          "title": "Amount"
        }
      },
      "title": "InvoiceExtractionModelServicesItem",
      "type": "object"
    }
  },
  "description": "Extracts detailed information from invoices for professional services rendered, organizing data in a structured format.",
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
    "Services": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/InvoiceExtractionModelServicesItem"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "A list of services provided, including descriptions, hourly rates, and amounts.",
      "title": "Services"
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
      "description": "The total amount charged for all services rendered in the invoice.",
      "format": "Must be formatted to two decimal places.",
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
Total tokens used: 1724

Breakdown by step:
- refinement: 305 tokens

- schema_generation: 976 tokens

- guide: 443 tokens

- extraction: 0 tokens


<details>
<summary>Generated Schema</summary>


```json
{
  "$defs": {
    "ConfidentialityClauseExtractionConfidentialityClause": {
      "description": "The confidentiality clause containing specific details about confidentiality obligations.",
      "properties": {
        "DefinitionOfConfidentialInformation": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The definition of what constitutes 'Confidential Information' within the document.",
          "title": "Definitionofconfidentialinformation"
        },
        "DurationOfObligation": {
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
          "title": "Durationofobligation"
        }
      },
      "title": "ConfidentialityClauseExtractionConfidentialityClause",
      "type": "object"
    }
  },
  "description": "Extracts the confidentiality clause from legal documents, including the definition of 'Confidential Information' and the duration of the confidentiality obligation.",
  "properties": {
    "ConfidentialityClause": {
      "anyOf": [
        {
          "$ref": "#/$defs/ConfidentialityClauseExtractionConfidentialityClause"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The confidentiality clause containing specific details about confidentiality obligations."
    }
  },
  "title": "ConfidentialityClauseExtraction",
  "type": "object"
}
```

</details>
