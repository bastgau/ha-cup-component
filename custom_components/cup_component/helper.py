"""Utility functions for the Cup Component integration."""

from homeassistant.util import slugify


def create_entity_id_name(input_string: str) -> str:
    """Create a normalized entity ID name from a raw input string.

    Splits the input at the first dot, lowercases the domain part, and
    slugifies the entity name part using Home Assistant's ``slugify`` helper.

    Args:
        input_string (str): The raw entity ID string to normalise, expected to
            contain at least one dot separator (e.g. ``"sensor.My Device Name"``).

    Returns:
        str: The normalized entity ID (e.g. ``"sensor.my_device_name"``).

    Raises:
        ValueError: If the input string does not contain a dot separator.

    """

    if "." not in input_string:
        msg: str = f"Invalid entity ID format: {input_string!r}"
        raise ValueError(msg)

    # Split the string at the first "."
    first_part, second_part = input_string.split(".", 1)

    # Replace non-alphanumeric characters (except "_") with "_" in both parts
    first_part = first_part.lower()
    second_part = slugify(second_part)

    # Recombine with the first "." preserved
    return f"{first_part}.{second_part}"
