"""
Utility functions for model operations.
"""

from typing import Dict, List, Literal, Type

from pydantic import BaseModel


class ModelUtils:
    """
    Utility functions for working with Pydantic models.
    """

    @staticmethod
    def extract_model_schema_info(model: Type[BaseModel]) -> str:
        """
        Extract model schema information for prompts.

        Args:
            model: Pydantic model to extract info from

        Returns:
            Formatted string with model field descriptions
        """
        model_schema = model.model_json_schema()
        model_schema_info = ""

        # Include field descriptions to help with extraction
        for field, details in model_schema.get("properties", {}).items():
            field_type = details.get("type", "unknown")
            field_desc = details.get("description", "")
            if "enum" in details:
                field_desc += (
                    f" Possible values: {', '.join(map(str, details['enum']))}"
                )
            model_schema_info += f"- {field} ({field_type}): {field_desc}\n"

        return model_schema_info

    @staticmethod
    def create_model_context(
        model: Type[BaseModel], instruction_type: Literal["text", "document"] = "text"
    ) -> str:
        """
        Create contextual information for custom model extraction.

        Args:
            model: Pydantic model to create context for
            instruction_type: Type of instruction ("text" or "document")

        Returns:
            Formatted context string for prompts
        """
        model_schema_info = ModelUtils.extract_model_schema_info(model)

        if not model_schema_info.strip():
            return ""

        if instruction_type == "document":
            return (
                f"\nModel fields and descriptions:\n{model_schema_info}\n"
                f"Ensure all applicable fields are populated with relevant information from the document."
            )
        else:
            return (
                f"\nModel fields and descriptions:\n{model_schema_info}\n"
                f"Ensure all applicable fields are populated with relevant information from the text."
            )

    @staticmethod
    def extract_field_characteristics(model: Type[BaseModel]) -> List[str]:
        """
        Extract data characteristics from model properties.

        Args:
            model: Pydantic model to analyze

        Returns:
            List of field characteristic descriptions
        """
        model_schema = model.model_json_schema()
        model_properties = model_schema.get("properties", {})
        data_characteristics = []

        for prop_name, prop_info in model_properties.items():
            prop_description = prop_info.get("description", "")
            prop_type = prop_info.get("type", "")
            enum_values = prop_info.get("enum", [])

            if prop_description:
                if enum_values:
                    data_characteristics.append(
                        f"{prop_name} ({prop_type}): {prop_description}. "
                        f"Possible values: {', '.join(map(str, enum_values))}"
                    )
                else:
                    data_characteristics.append(
                        f"{prop_name} ({prop_type}): {prop_description}"
                    )
            else:
                data_characteristics.append(f"{prop_name} ({prop_type})")

        return data_characteristics

    @staticmethod
    def extract_structural_requirements(model: Type[BaseModel]) -> Dict[str, str]:
        """
        Extract structural requirements from model.

        Args:
            model: Pydantic model to analyze

        Returns:
            Dictionary mapping field names to types
        """
        model_schema = model.model_json_schema()
        model_properties = model_schema.get("properties", {})
        structural_requirements = {}

        for prop_name, prop_info in model_properties.items():
            if "type" in prop_info:
                structural_requirements[prop_name] = prop_info["type"]

        return structural_requirements

    @staticmethod
    def get_model_description(model: Type[BaseModel]) -> str:
        """
        Get a descriptive name for the model.

        Args:
            model: Pydantic model to describe

        Returns:
            Model description string
        """
        model_schema = model.model_json_schema()
        return (
            model_schema.get("description", "")
            or model_schema.get("title", "")
            or model.__name__
        )
