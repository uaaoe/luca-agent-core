from langchain_core.tools import tool
from app.tools.registry import registry


@registry.register
@tool
def get_weather_forecast(city: str) -> str:
    """Get the current weather forecast for a given city."""
    # Tool assertion: validate input before network calls
    assert city and isinstance(city, str), "Sanity Check: City must be a non-empty string"

    result = f"The weather in {city} is 26°C, mostly sunny."

    # Sanity Check: Ensure output contract is satisfied
    assert len(result) > 0, "Tool produced empty output"
    return result
