from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

from climaps.core.data_loader import StationDataset


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES_PT = {
    0: "☀️ Céu limpo",
    1: "🌤️ Predominantemente limpo",
    2: "⛅ Parcialmente nublado",
    3: "☁️ Nublado",
    45: "🌫️ Neblina",
    48: "🌫️ Nevoeiro",
    51: "🌦️ Garoa leve",
    53: "🌦️ Garoa moderada",
    55: "🌦️ Garoa intensa",
    61: "🌧️ Chuva fraca",
    63: "🌧️ Chuva moderada",
    65: "🌧️ Chuva forte",
    80: "🌦️ Pancadas leves",
    81: "🌧️ Pancadas moderadas",
    82: "⛈️ Pancadas fortes",
    95: "⛈️ Tempestade",
    96: "⛈️ Tempestade com granizo",
    99: "⛈️ Tempestade severa",
}


@dataclass(frozen=True)
class LiveWeatherBundle:
    location_label: str
    latitude: float
    longitude: float
    current: dict[str, object]
    daily_forecast: pd.DataFrame
    dataset: StationDataset


def weather_description(code: int | float | None) -> str:
    if code is None or pd.isna(code):
        return "Condição indisponível"
    return WMO_CODES_PT.get(int(code), f"Código WMO {int(code)}")


def search_city(city_name: str, count: int = 10) -> list[dict[str, object]]:
    response = requests.get(
        GEOCODING_URL,
        params={"name": city_name.strip(), "count": count, "language": "pt", "format": "json"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("results", [])


def _parse_point_payload(payload: dict[str, object], label: str, lat: float, lon: float) -> dict[str, object]:
    cur = payload.get("current", {}) or {}
    daily = payload.get("daily", {}) or {}
    sunrise_val = (daily.get("sunrise") or [""])[0] or ""
    sunset_val = (daily.get("sunset") or [""])[0] or ""

    return {
        "local": label,
        "latitude": float(payload.get("latitude", lat)),
        "longitude": float(payload.get("longitude", lon)),
        "fuso": payload.get("timezone", "UTC"),
        "horario": cur.get("time", ""),
        "temperatura_c": cur.get("temperature_2m"),
        "sensacao_c": cur.get("apparent_temperature"),
        "umidade_pct": cur.get("relative_humidity_2m"),
        "precipitacao_mm": cur.get("precipitation"),
        "nuvens_pct": cur.get("cloud_cover"),
        "pressao_hpa": cur.get("pressure_msl"),
        "vento_kmh": cur.get("wind_speed_10m"),
        "rajadas_kmh": cur.get("wind_gusts_10m"),
        "periodo": "Dia" if cur.get("is_day", 1) == 1 else "Noite",
        "uv_max": (daily.get("uv_index_max") or [None])[0],
        "nascer_sol": sunrise_val[-5:] if sunrise_val else "-",
        "por_sol": sunset_val[-5:] if sunset_val else "-",
        "condicao": weather_description(cur.get("weather_code")),
    }


def fetch_current_point(latitude: float, longitude: float, location_label: str) -> dict[str, object]:
    """Busca o clima ao vivo de qualquer coordenada do mundo."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,"
            "precipitation,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_gusts_10m"
        ),
        "daily": "uv_index_max,sunrise,sunset",
        "forecast_days": 1,
        "timezone": "auto",
    }
    response = requests.get(FORECAST_URL, params=params, timeout=12)
    response.raise_for_status()
    return _parse_point_payload(response.json(), location_label, latitude, longitude)


def fetch_multiple_points(locations: list[tuple[str, float, float]]) -> list[dict[str, object]]:
    """Busca o clima ao vivo de várias cidades do mundo em uma única chamada."""
    if not locations:
        return []
    params = {
        "latitude": ",".join(str(lat) for _, lat, _ in locations),
        "longitude": ",".join(str(lon) for _, _, lon in locations),
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,"
            "precipitation,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_gusts_10m"
        ),
        "daily": "uv_index_max,sunrise,sunset",
        "forecast_days": 1,
        "timezone": "auto",
    }
    response = requests.get(FORECAST_URL, params=params, timeout=15)
    response.raise_for_status()
    raw = response.json()
    items = raw if isinstance(raw, list) else [raw]
    return [
        _parse_point_payload(item, label, lat, lon)
        for (label, lat, lon), item in zip(locations, items)
    ]


def fetch_live_weather(
    latitude: float,
    longitude: float,
    location_name: str,
    past_days: int = 30,
    forecast_days: int = 7,
) -> LiveWeatherBundle:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code",
        "hourly": "temperature_2m,precipitation",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
        "past_days": past_days,
        "forecast_days": forecast_days,
        "timezone": "auto",
    }
    response = requests.get(FORECAST_URL, params=params, timeout=15)
    response.raise_for_status()
    payload = response.json()

    raw_current = payload.get("current", {})
    current = {
        "horario": raw_current.get("time", ""),
        "temperatura_c": raw_current.get("temperature_2m"),
        "sensacao_c": raw_current.get("apparent_temperature"),
        "umidade_pct": raw_current.get("relative_humidity_2m"),
        "precipitacao_mm": raw_current.get("precipitation"),
        "vento_kmh": raw_current.get("wind_speed_10m"),
        "condicao": weather_description(raw_current.get("weather_code")),
    }

    raw_daily = payload.get("daily", {})
    daily_df = pd.DataFrame(
        {
            "data": pd.to_datetime(raw_daily.get("time", [])),
            "temp_max_c": pd.to_numeric(raw_daily.get("temperature_2m_max", []), errors="coerce"),
            "temp_min_c": pd.to_numeric(raw_daily.get("temperature_2m_min", []), errors="coerce"),
            "precipitacao_mm": pd.to_numeric(raw_daily.get("precipitation_sum", []), errors="coerce"),
            "condicao": [weather_description(c) for c in raw_daily.get("weather_code", [])],
        }
    )

    raw_hourly = payload.get("hourly", {})
    dt_series = pd.to_datetime(raw_hourly.get("time", []), errors="coerce")
    temp_series = pd.to_numeric(raw_hourly.get("temperature_2m", []), errors="coerce")
    rain_series = pd.to_numeric(raw_hourly.get("precipitation", []), errors="coerce")

    df = (
        pd.DataFrame(
            {
                "data": dt_series.floor("D"),
                "hora": dt_series.hour * 100,
                "precipitacao_mm": rain_series,
                "temp_max_c": temp_series,
                "temp_min_c": temp_series,
                "data_hora": dt_series,
                "hora_num": dt_series.hour,
                "mes": dt_series.month,
                "dia": dt_series.floor("D"),
            }
        )
        .dropna(subset=["data_hora"])
        .sort_values("data_hora")
        .reset_index(drop=True)
    )

    now_local = pd.to_datetime(raw_current.get("time")) if raw_current.get("time") else pd.Timestamp.now()
    df_observed = df[df["data_hora"] <= now_local].copy()
    if df_observed.empty:
        df_observed = df

    metadata = {
        "nome": location_name.upper(),
        "codigo_estacao": "OPEN-METEO",
        "latitude": str(latitude),
        "longitude": str(longitude),
    }
    dataset = StationDataset(
        metadata=metadata,
        data=df_observed,
        source=Path(f"api_open_meteo_{location_name.replace(' ', '_')}.json"),
    )

    return LiveWeatherBundle(
        location_label=location_name,
        latitude=latitude,
        longitude=longitude,
        current=current,
        daily_forecast=daily_df,
        dataset=dataset,
    )
