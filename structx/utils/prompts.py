from string import Template

query_refinement_system_prompt = """You are a data structuring specialist.
Analyze queries to determine the inherent structure of the data
and provide clear requirements for extraction."""

query_refinement_template = Template(
    """
    Analyze and expand the following query to ensure structured extraction.
    Consider:
    1. What are the inherent characteristics of the data?
    2. What structural patterns would best represent it?
    3. How should multiple related items be organized?
    4. Are there nested relationships or hierarchies?
    5. What data types would best represent each piece?

    Query: ${query}

    """
)


schema_system_prompt = """You are a schema design specialist.
Create detailed schemas that capture complex data structures."""

schema_template = Template(
    """
    Design a data extraction schema that enforces structured organization.
    
    Refined Query: ${refined_query} 
    
    Data Characteristics:
    ${data_characteristics}
    
    Structural Requirements:
    ${structural_requirements}
    
    Organization Principles:
    ${organization_principles}
    
    Sample text:
    ${sample_text}
    
    Important:
    1. Create structured objects for complex information
    2. Define appropriate data types
    3. Include nested models where needed
    4. Maintain consistent patterns
    5. Preserve relationships
    """
)


guide_system_prompt = """You are a data modeling specialist.
Create clear patterns for organizing complex, nested data structures.
Provide patterns as simple string descriptions and identify the correct target columns to analyze."""


guide_template = Template(
    """
    Create guidelines for structured data extraction based on these characteristics:
    ${data_characteristics}

    here is the list of available columns in the dataset:
    ${available_columns}
    
    Provide:
    1. Structural patterns as key-value pairs of string descriptions
    2. Relationship rules as a list of clear instructions
    3. Organization principles as a list of guidelines
    4. Target columns (target_columns) as a list of column names that contain the text to analyze
    
    The target_columns field is very important - it must contain only column names that actually exist in the dataset.
    If unsure, use the first column or the 'text' column if available.
    Keep all values as simple strings.
    """
)

# Specialized template for custom model extraction
custom_model_guide_template = Template(
    """
    Create guidelines for structured data extraction based on these model field characteristics:
    ${data_characteristics}

    These are the available columns in the dataset:
    ${available_columns}
    
    The extraction needs to fill these model fields:
    ${model_fields}
    
    Here are suggested column mappings for each model field:
    ${column_suggestions}
    
    Provide:
    1. Structural patterns describing how each field should be extracted
    2. Relationship rules as a list of clear instructions for extracting each required field
    3. Organization principles for populating the model consistently
    4. Target columns (target_columns) as a list of data columns that should be analyzed
    
    For target_columns:
    - Include all columns from the suggested mappings that are likely to contain relevant information
    - If text/description columns exist, include them
    - Only include column names that actually exist in the dataset
    - Do not omit any columns that might contain information needed for the model fields

    For relationship_rules:
    - Include explicit rules for mapping specific columns to model fields
    - Specify how to extract each field from the appropriate column(s)
    - Include rules for handling special field types (dates, numbers, enumerations)
    - Specify that fields should be left as null/None when no reliable information exists
    - Add rules to prevent invented or fabricated values for any field

    Keep all values as simple strings.
    """
)


extraction_system_prompt = """
You are a precise data extraction system specialized in transforming raw data into structured formats. Always:
1. Return structured objects for complex data according to the specified model
2. Maintain consistent formats and data types as defined in the schema
3. Use exact field types as specified (strings, numbers, dates, enumerations)
4. Use null/None for fields when no reliable information exists in the source data
5. Follow structural patterns exactly as specified
6. Return lists when the field expects a list of items
7. Be thorough but do not invent data that isn't present in the source
8. Only make inferences when there is strong supporting evidence in the data
9. When working with custom models, leave fields as null rather than inventing values
"""

extraction_template = Template(
    """
    Extract structured information following these guidelines:
    
    Query: ${query} 
    Patterns: ${patterns}
    Rules: ${rules}

    Important Notes:
    - Always return a list of structured objects
    - For list fields, return an array of items
    - Each item in a list should follow the specified structure
    - Use null/None when no reliable information is available (do NOT invent data)
    - Dates should be in ISO format (YYYY-MM-DDTHH:MM:SS)
    - For fields with enumerated values, use only values from the provided options
    - It's better to leave a field null than to fill it with incorrect information

    Text to analyze:
    ${text}
    """
)

# Refinement prompt for existing models
refinement_system_prompt = """You are a data model refinement specialist.
Analyze the existing model and the refinement instructions to create
a new model that incorporates the requested changes."""

refinement_template = Template(
    """
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
    """
)
