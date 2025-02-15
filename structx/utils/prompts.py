from string import Template

query_analysis_system_prompt = """You are a precise data extraction analyst.
Analyze queries to determine which column contains the target text
and what information needs to be extracted."""


query_analysis_template = Template(
    """
    Analyze the following query and determine:
    1. Which column contains the text to analyze
    2. What needs to be extracted from that text

    Query: ${query}
    Available columns: $available_columns
    """
)

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
Provide patterns as simple string descriptions."""


guide_template = Template(
    """
    Create guidelines for structured data extraction based on these characteristics:
    ${data_characteristics}
    Provide:
    1. Structural patterns as key-value pairs of string descriptions
    2. Relationship rules as a list of clear instructions
    3. Organization principles as a list of guidelines
    Keep all values as simple strings.
    """
)


extraction_system_prompt = """You are a precise data extraction system. Always:
1. Return structured objects for complex data
2. Maintain consistent formats
3. Use exact field types as specified
4. Never omit required fields
5. Follow structural patterns exactly
6. Return lists when the field expects a list of items"""

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
    - Dates should be in ISO format (YYYY-MM-DDTHH:MM:SS)
    
    Text to analyze:
    ${text}
    """
)
