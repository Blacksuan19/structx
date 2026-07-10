"""
Content analysis helpers for schema generation.
"""

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from structx.utils.file_reader import FileReader


class ContentAnalyzer:
    """
    Analyzes content types and extracts samples for schema generation.
    """

    @staticmethod
    def detect_content_type_and_context(df: pd.DataFrame) -> str:
        """
        Detect content type and provide context for better model generation.

        Args:
            df: DataFrame to analyze

        Returns:
            String describing the content type and context
        """
        # Check if this is file-based extraction
        is_file_based = "pdf_path" in df.columns or "source" in df.columns

        if not is_file_based:
            return "tabular data with structured columns"

        # Analyze file types and provide context
        file_types = set()
        file_examples = []

        for idx, row in df.iterrows():
            if idx >= 5:  # Limit analysis to first 5 files
                break

            if "pdf_path" in row and pd.notna(row["pdf_path"]):
                file_types.add("PDF")
                file_examples.append(Path(row["pdf_path"]).name)
            elif "source" in row and pd.notna(row["source"]):
                source_path = Path(row["source"])
                ext = source_path.suffix.lower()
                if ext in [".pdf"]:
                    file_types.add("PDF")
                elif ext in [".docx", ".doc"]:
                    file_types.add("Word document")
                elif ext in [".txt", ".md"]:
                    file_types.add("Text document")
                else:
                    file_types.add(f"{ext} file")
                file_examples.append(source_path.name)

        context_info = f"document(s) of type: {', '.join(file_types)}"
        if file_examples:
            context_info += f". Examples: {', '.join(file_examples[:3])}"
            if len(file_examples) > 3:
                context_info += f" and {len(file_examples) - 3} more"

        return context_info

    @staticmethod
    def extract_content_sample_for_schema(
        df: pd.DataFrame, max_chars: int = 2000
    ) -> str:
        """
        Extract content samples from files to inform schema generation.

        Args:
            df: DataFrame containing file information
            max_chars: Maximum characters per sample

        Returns:
            String containing sample content for schema generation
        """
        samples = []

        for idx, row in df.iterrows():
            if idx >= 3:  # Limit to first 3 files for sampling
                break

            # Check if this is a file-based row
            if "source" in row and pd.notna(row["source"]):
                source_path = Path(row["source"])
                if source_path.exists():
                    samples.append(
                        FileReader.extract_text_sample(source_path, max_chars)
                    )
            elif "pdf_path" in row and pd.notna(row["pdf_path"]):
                samples.append(
                    FileReader.extract_text_sample(row["pdf_path"], max_chars)
                )
            else:
                # This is likely traditional tabular data
                # Convert row data to string representation
                row_text = " | ".join(
                    [f"{col}: {val}" for col, val in row.items() if pd.notna(val)]
                )
                samples.append(row_text[:max_chars])

        return "\n\n---SAMPLE SEPARATOR---\n\n".join(samples)

    @staticmethod
    def suggest_column_mappings(
        model_properties: Dict[str, Any],
        data_columns: List[str],
        field_descriptions: Dict[str, Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        """
        Create intelligent mapping suggestions between model fields and data columns.

        Args:
            model_properties: Properties from the model schema
            data_columns: Available column names in the dataset
            field_descriptions: Descriptions and types for model fields

        Returns:
            Dictionary mapping model field names to potential column names
        """
        mapping_suggestions = {}

        for field_name in model_properties.keys():
            potential_columns = []

            # Find columns that might match this field based on name similarity
            field_terms = set(field_name.lower().replace("_", " ").split())
            field_description = (
                field_descriptions.get(field_name, {}).get("description", "").lower()
            )
            field_desc_terms = set(
                field_description.replace(",", " ").replace(".", " ").split()
            )

            for column in data_columns:
                col_terms = set(column.lower().replace("_", " ").split())

                # Check for direct matches or substring matches
                if (
                    field_name.lower() in column.lower()
                    or column.lower() in field_name.lower()
                    or any(term in column.lower() for term in field_terms)
                    or any(term in column.lower() for term in field_desc_terms)
                ):
                    potential_columns.append(column)

            # If no matches found through name/description similarity, suggest all columns
            # as the field might be extracted from any text column
            if not potential_columns:
                # Add text columns or if not found, just add all columns
                text_columns = [
                    col
                    for col in data_columns
                    if "text" in col.lower() or "description" in col.lower()
                ]
                potential_columns = text_columns if text_columns else data_columns

            mapping_suggestions[field_name] = potential_columns

        return mapping_suggestions
