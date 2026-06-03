import requests
from dotenv import load_dotenv
from langchain.tools import tool

from SenkuNoChinou.models.mcpSchema import WeatherInput

load_dotenv()

_WTTR_BASE = "https://wttr.in"


def get_weather(location: str, days: int = 1) -> str:
    """
    Get current weather and forecast for a location.

    Description: Fetches real-time weather conditions and forecast using wttr.in.
    No API key required.

    Args:
        location: City name or location (e.g. Mumbai, Delhi, London).
        days: Forecast days 1-3. Default 1 (current conditions only).

    Returns:
        Weather report as formatted text.
    """
    days = max(1, min(days, 3))
    try:
        response = requests.get(
            f"{_WTTR_BASE}/{location}",
            params={"format": "j1"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return f"Could not fetch weather for '{location}': {e}"

    current = data["current_condition"][0]
    lines = [
        f"Weather for {location}",
        f"Condition : {current['weatherDesc'][0]['value']}",
        f"Temp      : {current['temp_C']}°C (feels like {current['FeelsLikeC']}°C)",
        f"Humidity  : {current['humidity']}%",
        f"Wind      : {current['windspeedKmph']} km/h {current['winddir16Point']}",
        f"Visibility: {current['visibility']} km",
    ]

    if days > 1:
        lines.append("\nForecast:")
        for day in data["weather"][:days]:
            lines.append(
                f"  {day['date']} — "
                f"↑{day['maxtempC']}°C ↓{day['mintempC']}°C  "
                f"{day['hourly'][4]['weatherDesc'][0]['value']}"
            )

    return "\n".join(lines)


weather_lc_tool = tool(get_weather, args_schema=WeatherInput)
