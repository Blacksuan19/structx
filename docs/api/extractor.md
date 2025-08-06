# Extractor

The `Extractor` class is the main interface for structured data extraction.

## API Requirements

**All methods require keyword arguments.** The `*` in method signatures indicates that all parameters after it must be passed as keyword arguments:

```python
# ✅ Correct usage
result = extractor.extract(data="file.pdf", query="extract information")
result = extractor.extract_queries(data="file.pdf", queries=["query1", "query2"])
model = extractor.get_schema(data="file.pdf", query="extract information")
refined = extractor.refine_data_model(model=ExistingModel, refinement_instructions="add field")

# ❌ Incorrect usage - will raise TypeError
result = extractor.extract("file.pdf", "extract information")
result = extractor.extract_queries("file.pdf", ["query1", "query2"])
```

## Architecture Overview

<details>
<summary>View Architecture Diagram</summary>

```mermaid
graph TB
    subgraph "User Interface"
        A[Extractor Class]
        A1[extract] 
        A2[extract_queries]
        A3[extract_async]
        A4[refine_data_model]
    end
    
    subgraph "Core Processing Modules"
        B[LLM Core]
        C[Model Utils]
        D[Data Content Processor]
        E[Model Operations]
        F[Extraction Engine]
    end
    
    subgraph "File Processing Pipeline"
        G[File Reader]
        H[Format Detection]
        I[Document Conversion]
        J[PDF Generation]
        K[Multimodal Processing]
    end
    
    subgraph "LLM Integration"
        L[Instructor Client]
        M[LiteLLM Support]
        N[Provider Abstraction]
        O[Token Tracking]
    end
    
    subgraph "Output Management"
        P[Result Manager]
        Q[Type Safety]
        R[Error Handling]
        S[Usage Statistics]
    end
    
    A --> A1
    A --> A2
    A --> A3
    A --> A4
    
    A1 --> B
    A1 --> G
    B --> L
    G --> H
    H --> I
    I --> J
    J --> K
    
    B --> C
    B --> D
    C --> E
    E --> F
    F --> P
    
    L --> M
    M --> N
    N --> O
    P --> Q
    P --> R
    P --> S
```

</details>

::: structx.Extractor
    options:
      show_bases: false
      heading_level: 2