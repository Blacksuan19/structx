from string import Template

extraction_plan_system_prompt = """You design complete structured extraction plans.
Return explicit instructions, target input columns, and a model schema that agree.
Use only these field type forms: str, int, float, bool, date, datetime, time,
Decimal, UUID, Any, List[T], Dict[str, T], Set[T], and Optional[T].
Fields are optional and nullable by default. Set required=true for core values
explicitly requested by the user. Set nullable=false only together with
required=true when null is invalid.
Do not add Optional unless it clarifies intent.
Represent nested objects with nested_fields and use List[Any] or Dict[str, Any]
only when a more precise type cannot be determined."""

extraction_plan_template = Template("""
    Build one complete extraction plan for this request.

    Original query:
    ${query}

    Available input columns:
    ${available_columns}

    Representative input:
    ${sample_text}

    Requirements:
    1. Turn the query into concise, explicit extraction instructions.
    2. Select target_columns only from the available input columns.
    3. Define the smallest model schema that fully answers the query. Prefer a few
       focused fields over an exhaustive document audit.
    4. Use nested_fields for structured objects and canonical field types exactly as instructed.
    5. Express presence and nullability with required and nullable, not JSON Schema syntax.
    6. Do not add catch-all summaries, issue inventories, metadata, or unrelated legal
       terms unless the query explicitly requests them.
    """)

extraction_system_prompt = """
You are a precise data extraction system specialized in transforming raw data into structured formats. Always:
1. Return structured objects for complex data according to the specified model
2. Maintain consistent formats and data types as defined in the schema
3. Use exact field types as specified (strings, numbers, dates, enumerations)
4. Use null/None for nullable fields when no reliable information exists in the source data
5. Follow the supplied extraction instructions exactly
6. Return lists when the field expects a list of items
7. Be thorough but do not invent data that isn't present in the source
8. Only make inferences when there is strong supporting evidence in the data
9. When working with custom models, leave nullable fields as null rather than inventing values
"""

extraction_template = Template("""
    Extract structured information using these instructions:

    ${instructions}

    Important Notes:
    - Always return a list of structured objects
    - For list fields, return an array of items
    - Each item in a list should follow the specified structure
    - Use null/None for nullable fields when no reliable information is available (do NOT invent data)
    - Dates should be in ISO format (YYYY-MM-DDTHH:MM:SS)
    - For fields with enumerated values, use only values from the provided options
    - It's better to leave a field null than to fill it with incorrect information

    Text to analyze:
    ${text}
    """)

# Refinement prompt for existing models
refinement_system_prompt = """You are a data model refinement specialist.
Analyze the existing model and the refinement instructions to create
a new model that incorporates the requested changes."""

refinement_template = Template("""
    Refine the following data model according to these instructions:
    
    EXISTING MODEL SCHEMA:
    ```json
    ${model_schema}
    ```
    
    REFINEMENT INSTRUCTIONS:
    ${instructions}
    
    Create a new model schema that:
    1. Keeps fields from the original model that shouldn't change
    2. Modifies fields as specified in the instructions
    3. Adds new fields as specified in the instructions
    4. Removes fields as specified in the instructions
    
    Important: Use Pydantic v2 syntax:
    - Use `pattern` instead of `regex` for string patterns
    - Use `model_config` instead of `Config` class
    - Use `Field` with validation parameters instead of validators where possible
    
    Include a clear description of the model and each field.
    """)
