from dataclasses import dataclass  # Importa dataclass para estruturar o pacote de retorno da API
from pathlib import Path  # Usado para criar um Path simbólico identificando a origem dos dados da API

import pandas as pd  # Manipulação de séries temporais e DataFrames
import requests  # Biblioteca para fazer requisições HTTP à API Open-Meteo

from climaps.core.data_loader import StationDataset  # Reaproveita a estrutura StationDataset usada pelo resto do app
from climaps.core.analysis import (  # Índices meteorológicos e classificações
    calculate_dew_point,
    calculate_heat_index,
    classify_air_quality,
    classify_uv,
    evaluate_storm_risk,
)
from climaps.ui_styles import format_datetime_friendly  # Formata datas/horas no padrão brasileiro amigável


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"  # Endpoint público de busca de cidades por nome (Open-Meteo)
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"  # Endpoint público de previsão e clima atual (Open-Meteo)
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"  # Endpoint de qualidade do ar e queimadas (Open-Meteo)
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"  # Endpoint histórico de reanálise ERA5 desde 1940 (Open-Meteo)

WMO_CODES_PT = {  # Dicionário que traduz códigos meteorológicos padrão WMO (Organização Meteorológica Mundial) para português + emoji
    0: "☀️ Céu limpo",  # Código 0: céu limpo
    1: "🌤️ Predominantemente limpo",  # Código 1: quase sem nuvens
    2: "⛅ Parcialmente nublado",  # Código 2: parcialmente nublado
    3: "☁️ Nublado",  # Código 3: encoberto
    45: "🌫️ Neblina",  # Código 45: neblina
    48: "🌫️ Nevoeiro",  # Código 48: nevoeiro com deposição
    51: "🌦️ Garoa leve",  # Código 51: chuvisco fraco
    53: "🌦️ Garoa moderada",  # Código 53: chuvisco moderado
    55: "🌦️ Garoa intensa",  # Código 55: chuvisco forte
    61: "🌧️ Chuva fraca",  # Código 61: chuva leve
    63: "🌧️ Chuva moderada",  # Código 63: chuva moderada
    65: "🌧️ Chuva forte",  # Código 65: chuva intensa
    80: "🌦️ Pancadas leves",  # Código 80: pancadas de chuva fracas
    81: "🌧️ Pancadas moderadas",  # Código 81: pancadas de chuva moderadas
    82: "⛈️ Pancadas fortes",  # Código 82: pancadas violentas
    95: "⛈️ Tempestade",  # Código 95: trovoada
    96: "⛈️ Tempestade com granizo",  # Código 96: tempestade com granizo leve
    99: "⛈️ Tempestade severa",  # Código 99: tempestade com granizo forte
}  # Fecha o dicionário de códigos WMO


@dataclass(frozen=True)  # Classe imutável que agrupa tudo o que é retornado ao carregar uma cidade
class LiveWeatherBundle:  # Estrutura completa de dados ao vivo, previsão e histórico recente
    location_label: str  # Nome amigável do local
    latitude: float  # Latitude do ponto consultado
    longitude: float  # Longitude do ponto consultado
    current: dict[str, object]  # Dicionário com as condições atuais
    daily_forecast: pd.DataFrame  # Tabela com previsão diária (ex.: 7 dias)
    dataset: StationDataset  # Histórico horário recente convertido para o formato padrão StationDataset


def weather_description(code: int | float | None) -> str:  # Converte um código numérico WMO em texto legível
    if code is None or pd.isna(code):  # Se o código for None ou NaN
        return "Condição indisponível"  # Retorna texto padrão de indisponibilidade
    return WMO_CODES_PT.get(int(code), f"Código WMO {int(code)}")  # Busca no dicionário ou exibe o número bruto se não mapeado


def search_city(city_name: str, count: int = 10) -> list[dict[str, object]]:  # Busca cidades pelo nome na API de geocodificação
    response = requests.get(  # Faz uma requisição HTTP GET
        GEOCODING_URL,  # URL de geocodificação
        params={"name": city_name.strip(), "count": count, "language": "pt", "format": "json"},  # Parâmetros: nome, limite, idioma e formato
        timeout=10,  # Tempo máximo de espera de 10 segundos
    )  # Finaliza chamada GET
    response.raise_for_status()  # Lança exceção HTTP caso o status da resposta indique erro (4xx ou 5xx)
    return response.json().get("results", [])  # Converte a resposta JSON e retorna a lista "results" (ou lista vazia)


def fetch_air_quality(latitude: float, longitude: float) -> dict[str, object]:
    """Consulta dados de qualidade do ar e concentração de material particulado na Open-Meteo."""
    try:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone,dust",
        }
        response = requests.get(AIR_QUALITY_URL, params=params, timeout=10)
        response.raise_for_status()
        cur = response.json().get("current", {}) or {}
        us_aqi = cur.get("us_aqi")
        pm2_5 = cur.get("pm2_5")
        return {
            "us_aqi": us_aqi,
            "european_aqi": cur.get("european_aqi"),
            "pm2_5": pm2_5,
            "pm10": cur.get("pm10"),
            "co": cur.get("carbon_monoxide"),
            "no2": cur.get("nitrogen_dioxide"),
            "o3": cur.get("ozone"),
            "dust": cur.get("dust"),
            "info": classify_air_quality(us_aqi, pm2_5),
        }
    except Exception as exc:
        return {
            "us_aqi": None,
            "european_aqi": None,
            "pm2_5": None,
            "pm10": None,
            "co": None,
            "no2": None,
            "o3": None,
            "dust": None,
            "info": classify_air_quality(None, None),
            "erro": str(exc),
        }


def _parse_point_payload(payload: dict[str, object], label: str, lat: float, lon: float) -> dict[str, object]:  # Extrai e padroniza o JSON de um ponto
    cur = payload.get("current", {}) or {}  # Obtém o bloco "current" do JSON (garantindo dicionário mesmo se vier None)
    daily = payload.get("daily", {}) or {}  # Obtém o bloco "daily" do JSON
    hourly = payload.get("hourly", {}) or {}  # Obtém o bloco "hourly" do JSON
    sunrise_val = (daily.get("sunrise") or [""])[0] or ""  # Pega a primeira string de nascer do sol (se existir)
    sunset_val = (daily.get("sunset") or [""])[0] or ""  # Pega a primeira string de pôr do sol (se existir)

    temp_c = cur.get("temperature_2m")
    humid = cur.get("relative_humidity_2m")
    press = cur.get("pressure_msl")
    wind = cur.get("wind_speed_10m")
    gust = cur.get("wind_gusts_10m")
    rain = cur.get("precipitation")
    uv_max = (daily.get("uv_index_max") or [None])[0]

    dew_point = calculate_dew_point(temp_c, humid)
    hi_c, hi_desc, hi_level = calculate_heat_index(temp_c, humid)
    storm_risk = evaluate_storm_risk(press, humid, wind, gust, rain)
    uv_info = classify_uv(uv_max)

    # Previsão horária (próximas 48 horas)
    hourly_times = hourly.get("time", [])
    hourly_temps = hourly.get("temperature_2m", [])
    hourly_probs = hourly.get("precipitation_probability", [])
    hourly_rains = hourly.get("precipitation", [])
    hourly_codes = hourly.get("weather_code", [])

    forecast_hourly = []
    if hourly_times and hourly_temps:
        for t, temp, prob, p_rain, code in zip(
            hourly_times[:48], hourly_temps[:48], hourly_probs[:48], hourly_rains[:48], hourly_codes[:48]
        ):
            forecast_hourly.append(
                {
                    "data_hora_raw": t,
                    "hora_label": t[-5:],
                    "temperatura_c": temp,
                    "prob_chuva_pct": prob if prob is not None else 0,
                    "chuva_mm": p_rain if p_rain is not None else 0.0,
                    "condicao": weather_description(code),
                }
            )

    # Previsão diária (próximos 14 dias)
    daily_times = daily.get("time", [])
    daily_tmax = daily.get("temperature_2m_max", [])
    daily_tmin = daily.get("temperature_2m_min", [])
    daily_probs = daily.get("precipitation_probability_max", [])
    daily_sums = daily.get("precipitation_sum", [])
    daily_codes = daily.get("weather_code", [])

    forecast_daily = []
    if daily_times and daily_tmax:
        for d, tmax, tmin, prob, psum, code in zip(
            daily_times[:14], daily_tmax[:14], daily_tmin[:14], daily_probs[:14], daily_sums[:14], daily_codes[:14]
        ):
            dia_str = f"{d[8:10]}/{d[5:7]}" if len(d) >= 10 else d
            forecast_daily.append(
                {
                    "data_raw": d,
                    "data_label": dia_str,
                    "temp_max_c": tmax,
                    "temp_min_c": tmin,
                    "prob_chuva_pct": prob if prob is not None else 0,
                    "chuva_mm": psum if psum is not None else 0.0,
                    "condicao": weather_description(code),
                }
            )

    return {  # Retorna um dicionário plano com chaves em português para a interface
        "local": label,  # Nome de exibição do local
        "latitude": float(payload.get("latitude", lat)),  # Latitude retornada pela grade da API (ou a solicitada)
        "longitude": float(payload.get("longitude", lon)),  # Longitude retornada pela grade da API (ou a solicitada)
        "fuso": payload.get("timezone", "UTC"),  # Fuso horário local detectado pela API
        "horario_raw": cur.get("time", ""),  # Horário ISO bruto
        "horario": format_datetime_friendly(cur.get("time", "")),  # Data/hora da medição atual formatada
        "temperatura_c": temp_c,  # Temperatura a 2 metros de altura (°C)
        "sensacao_c": cur.get("apparent_temperature"),  # Sensação térmica (°C)
        "umidade_pct": humid,  # Umidade relativa do ar (%)
        "precipitacao_mm": rain,  # Precipitação atual (mm)
        "nuvens_pct": cur.get("cloud_cover"),  # Cobertura de nuvens (%)
        "pressao_hpa": press,  # Pressão atmosférica ao nível do mar (hPa)
        "vento_kmh": wind,  # Velocidade do vento a 10 metros (km/h)
        "rajadas_kmh": gust,  # Rajadas de vento a 10 metros (km/h)
        "periodo": "Dia" if cur.get("is_day", 1) == 1 else "Noite",  # Converte flag is_day (1/0) para "Dia" ou "Noite"
        "uv_max": uv_max,  # Índice UV máximo previsto para o dia
        "uv_info": uv_info,  # Classificação UV (OMS)
        "nascer_sol": sunrise_val[-5:] if sunrise_val else "-",  # Extrai apenas "HH:MM" dos últimos 5 caracteres
        "por_sol": sunset_val[-5:] if sunset_val else "-",  # Extrai apenas "HH:MM" dos últimos 5 caracteres
        "condicao": weather_description(cur.get("weather_code")),  # Converte o código WMO para descrição com emoji
        "ponto_orvalho_c": dew_point,  # Ponto de Orvalho em °C
        "indice_calor_c": hi_c,  # Índice de calor em °C
        "indice_calor_desc": hi_desc,  # Categoria de desconforto térmico
        "indice_calor_nivel": hi_level,  # Nível de risco
        "risco_tempestade": storm_risk,  # Avaliação de risco de tempestade
        "forecast_hourly": forecast_hourly,  # Lista de previsão horária (até 48h)
        "forecast_daily": forecast_daily,  # Lista de previsão diária (até 14 dias)
    }  # Fecha dicionário retornado


def fetch_current_point(latitude: float, longitude: float, location_label: str) -> dict[str, object]:  # Consulta clima atual de uma coordenada
    """Busca o clima ao vivo, previsão horária e diária e qualidade do ar de qualquer coordenada do mundo."""
    params = {  # Monta o dicionário de parâmetros da query string
        "latitude": latitude,  # Latitude alvo
        "longitude": longitude,  # Longitude alvo
        "current": (  # Lista de variáveis instantâneas desejadas separadas por vírgula
            "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,"
            "precipitation,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_gusts_10m"
        ),  # Fecha string de variáveis "current"
        "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code",  # Série horária de previsão
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,uv_index_max,sunrise,sunset,weather_code",  # Previsão diária
        "forecast_days": 14,  # Previsão estendida de 14 dias
        "timezone": "auto",  # Ajusta automaticamente os horários para o fuso do ponto consultado
    }  # Fecha params
    response = requests.get(FORECAST_URL, params=params, timeout=12)  # Faz requisição GET com timeout de 12 segundos
    response.raise_for_status()  # Verifica se não houve erro HTTP
    data = _parse_point_payload(response.json(), location_label, latitude, longitude)  # Normaliza e retorna o payload JSON
    data["air_quality"] = fetch_air_quality(latitude, longitude)  # Anexa medições de qualidade do ar e queimadas
    return data


def fetch_multiple_points(locations: list[tuple[str, float, float]]) -> list[dict[str, object]]:  # Consulta várias cidades de uma só vez
    """Busca o clima ao vivo de várias cidades do mundo em uma única chamada."""  # Docstring explicativa
    if not locations:  # Se a lista de locais estiver vazia
        return []  # Retorna lista vazia sem fazer requisição HTTP
    params = {  # Monta parâmetros passando listas separadas por vírgula para latitudes e longitudes
        "latitude": ",".join(str(lat) for _, lat, _ in locations),  # Concatena todas as latitudes com vírgula
        "longitude": ",".join(str(lon) for _, _, lon in locations),  # Concatena todas as longitudes com vírgula
        "current": (  # Mesmas variáveis atuais da consulta unitária
            "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,"  # Bloco térmico e dia/noite
            "precipitation,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_gusts_10m"  # Bloco chuva, nuvens, pressão e vento
        ),  # Fecha current
        "daily": "uv_index_max,sunrise,sunset",  # Variáveis diárias complementares
        "forecast_days": 1,  # Apenas 1 dia
        "timezone": "auto",  # Fuso automático para cada coordenada
    }  # Fecha params
    response = requests.get(FORECAST_URL, params=params, timeout=15)  # Executa requisição GET com timeout de 15 segundos
    response.raise_for_status()  # Garante sucesso HTTP
    raw = response.json()  # Decodifica o JSON retornado
    items = raw if isinstance(raw, list) else [raw]  # Se vier 1 ponto como dict, embrulha em lista; se vários, já vem como list
    return [  # Retorna uma lista de dicionários normalizados
        _parse_point_payload(item, label, lat, lon)  # Converte cada item da resposta com seu respectivo rótulo
        for (label, lat, lon), item in zip(locations, items)  # Emparelha cada local pedido com o item retornado correspondente
    ]  # Fecha list comprehension


def fetch_live_weather(  # Busca clima atual, previsão diária e série horária dos últimos dias para alimentar as abas de análise
    latitude: float,  # Latitude da cidade escolhida
    longitude: float,  # Longitude da cidade escolhida
    location_name: str,  # Nome do local para metadados e rótulos
    past_days: int = 30,  # Quantidade de dias passados a carregar (padrão 30 dias)
    forecast_days: int = 7,  # Quantidade de dias de previsão futura (padrão 7 dias)
) -> LiveWeatherBundle:  # Retorna um objeto LiveWeatherBundle
    params = {  # Parâmetros da chamada completa à API
        "latitude": latitude,  # Latitude
        "longitude": longitude,  # Longitude
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code",  # Variáveis atuais
        "hourly": "temperature_2m,precipitation",  # Variáveis horárias para montar a série histórica compatível com o INMET
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",  # Variáveis diárias de previsão
        "past_days": past_days,  # Dias históricos passados
        "forecast_days": forecast_days,  # Dias futuros de previsão
        "timezone": "auto",  # Fuso horário automático do local
    }  # Fecha params
    response = requests.get(FORECAST_URL, params=params, timeout=15)  # Faz a requisição GET
    response.raise_for_status()  # Verifica erro HTTP
    payload = response.json()  # Extrai o JSON da resposta

    raw_current = payload.get("current", {})  # Bloco bruto do clima atual
    current = {  # Monta dicionário resumido do momento atual
        "horario": format_datetime_friendly(raw_current.get("time", "")),  # Horário atual formatado
        "temperatura_c": raw_current.get("temperature_2m"),  # Temperatura atual
        "sensacao_c": raw_current.get("apparent_temperature"),  # Sensação térmica
        "umidade_pct": raw_current.get("relative_humidity_2m"),  # Umidade relativa
        "precipitacao_mm": raw_current.get("precipitation"),  # Chuva atual
        "vento_kmh": raw_current.get("wind_speed_10m"),  # Vento atual
        "condicao": weather_description(raw_current.get("weather_code")),  # Descrição da condição do tempo
    }  # Fecha current

    raw_daily = payload.get("daily", {})  # Bloco bruto da previsão diária
    daily_df = pd.DataFrame(  # Constrói o DataFrame com a previsão diária
        {  # Dicionário de colunas
            "data": pd.to_datetime(raw_daily.get("time", [])),  # Datas convertidas para datetime
            "temp_max_c": pd.to_numeric(raw_daily.get("temperature_2m_max", []), errors="coerce"),  # Máximas diárias
            "temp_min_c": pd.to_numeric(raw_daily.get("temperature_2m_min", []), errors="coerce"),  # Mínimas diárias
            "precipitacao_mm": pd.to_numeric(raw_daily.get("precipitation_sum", []), errors="coerce"),  # Chuva diária somada
            "condicao": [weather_description(c) for c in raw_daily.get("weather_code", [])],  # Descrição diária por código WMO
        }  # Fecha dict
    )  # Fecha DataFrame

    raw_hourly = payload.get("hourly", {})  # Bloco bruto das séries horárias
    dt_series = pd.to_datetime(raw_hourly.get("time", []), errors="coerce")  # Converte timestamps horários para datetime
    temp_series = pd.to_numeric(raw_hourly.get("temperature_2m", []), errors="coerce")  # Converte série de temperaturas para float
    rain_series = pd.to_numeric(raw_hourly.get("precipitation", []), errors="coerce")  # Converte série de chuvas para float

    df = (  # Monta o DataFrame no mesmo esquema de colunas usado pelos arquivos do INMET
        pd.DataFrame(  # Cria DataFrame com as 9 colunas padrão do sistema
            {  # Mapeamento das colunas
                "data": dt_series.floor("D"),  # Data truncada para o dia
                "hora": dt_series.hour * 100,  # Hora no formato inteiro INMET (ex.: 14h -> 1400)
                "precipitacao_mm": rain_series,  # Precipitação horária (mm)
                "temp_max_c": temp_series,  # Usa temperatura horária como máx (API horária traz temperatura instantânea/horária)
                "temp_min_c": temp_series,  # Usa temperatura horária como mín para manter compatibilidade com as abas analíticas
                "data_hora": dt_series,  # Timestamp completo
                "hora_num": dt_series.hour,  # Hora inteira (0..23)
                "mes": dt_series.month,  # Número do mês (1..12)
                "dia": dt_series.floor("D"),  # Dia truncado para agregação diária
            }  # Fecha dict de colunas
        )  # Fecha pd.DataFrame
        .dropna(subset=["data_hora"])  # Remove linhas sem timestamp válido
        .sort_values("data_hora")  # Ordena cronologicamente
        .reset_index(drop=True)  # Reinicia o índice de 0 a N-1
    )  # Finaliza construção do DataFrame horário

    now_local = pd.to_datetime(raw_current.get("time")) if raw_current.get("time") else pd.Timestamp.now()  # Referência do horário atual local
    df_observed = df[df["data_hora"] <= now_local].copy()  # Mantém apenas horas passadas/atuais (exclui horas futuras da previsão)
    if df_observed.empty:  # Segurança caso o filtro deixe o DataFrame vazio
        df_observed = df  # Usa todos os registros retornados como fallback

    metadata = {  # Cria metadados no formato esperado pelo cabeçalho da interface
        "nome": location_name.upper(),  # Nome do local em maiúsculas
        "codigo_estacao": "OPEN-METEO",  # Identifica a fonte como Open-Meteo em vez de código INMET
        "latitude": str(latitude),  # Latitude em string
        "longitude": str(longitude),  # Longitude em string
    }  # Fecha metadata
    dataset = StationDataset(  # Empacota tudo em um StationDataset
        metadata=metadata,  # Metadados criados acima
        data=df_observed,  # Série horária observada
        source=Path(f"api_open_meteo_{location_name.replace(' ', '_')}.json"),  # Nome simbólico de arquivo fonte para exibição no banner
    )  # Fecha StationDataset

    return LiveWeatherBundle(  # Retorna o pacote completo LiveWeatherBundle
        location_label=location_name,  # Rótulo do local
        latitude=latitude,  # Latitude
        longitude=longitude,  # Longitude
        current=current,  # Condições atuais
        daily_forecast=daily_df,  # Previsão diária
        dataset=dataset,  # Dataset compatível com as abas analíticas
    )  # Fecha retorno


def fetch_historical_day(
    latitude: float,
    longitude: float,
    location_label: str,
    target_date: str | pd.Timestamp,
) -> dict[str, object]:
    """Consulta os dados meteorológicos completos de qualquer dia específico da história para uma coordenada."""
    if isinstance(target_date, (pd.Timestamp, pd.DatetimeIndex)):
        date_str = target_date.strftime("%Y-%m-%d")
    else:
        date_str = str(target_date)[:10]

    today = pd.Timestamp.now().floor("D")
    target_dt = pd.to_datetime(date_str)
    days_diff = (today - target_dt).days

    # Usa archive para datas com mais de 5 dias atrás e forecast para dias recentes ou futuros
    primary_url = ARCHIVE_URL if days_diff > 5 else FORECAST_URL
    fallback_url = FORECAST_URL if primary_url == ARCHIVE_URL else ARCHIVE_URL

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": date_str,
        "end_date": date_str,
        "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,surface_pressure,wind_speed_10m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,sunrise,sunset,weather_code",
        "timezone": "auto",
    }

    payload = None
    try:
        resp = requests.get(primary_url, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        resp = requests.get(fallback_url, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()

    daily = payload.get("daily", {}) or {}
    hourly = payload.get("hourly", {}) or {}

    tmax = (daily.get("temperature_2m_max") or [None])[0]
    tmin = (daily.get("temperature_2m_min") or [None])[0]
    psum = (daily.get("precipitation_sum") or [0.0])[0]
    wmax = (daily.get("wind_speed_10m_max") or [None])[0]
    sunrise = (daily.get("sunrise") or [""])[0] or ""
    sunset = (daily.get("sunset") or [""])[0] or ""
    code_daily = (daily.get("weather_code") or [None])[0]

    hourly_times = hourly.get("time", [])
    hourly_temps = hourly.get("temperature_2m", [])
    hourly_humids = hourly.get("relative_humidity_2m", [])
    hourly_apparents = hourly.get("apparent_temperature", [])
    hourly_rains = hourly.get("precipitation", [])
    hourly_press = hourly.get("surface_pressure", [])
    hourly_winds = hourly.get("wind_speed_10m", [])
    hourly_codes = hourly.get("weather_code", [])

    hourly_records = []
    for i, t in enumerate(hourly_times):
        temp = hourly_temps[i] if i < len(hourly_temps) else None
        h_rain = hourly_rains[i] if i < len(hourly_rains) else 0.0
        h_hum = hourly_humids[i] if i < len(hourly_humids) else None
        h_wind = hourly_winds[i] if i < len(hourly_winds) else None
        h_code = hourly_codes[i] if i < len(hourly_codes) else None
        hora_label = t[-5:] if len(t) >= 5 else f"{i:02d}:00"
        hourly_records.append(
            {
                "data_hora_raw": t,
                "hora_label": hora_label,
                "temperatura_c": temp,
                "chuva_mm": h_rain if h_rain is not None else 0.0,
                "umidade_pct": h_hum,
                "vento_kmh": h_wind,
                "condicao": weather_description(h_code),
            }
        )

    valid_temps = [t for t in hourly_temps if t is not None and not pd.isna(t)]
    temp_media = (sum(valid_temps) / len(valid_temps)) if valid_temps else None
    valid_hum = [h for h in hourly_humids if h is not None and not pd.isna(h)]
    umid_media = (sum(valid_hum) / len(valid_hum)) if valid_hum else None
    valid_press = [p for p in hourly_press if p is not None and not pd.isna(p)]
    press_media = (sum(valid_press) / len(valid_press)) if valid_press else None

    dt_obj = pd.to_datetime(date_str)
    dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    dia_semana_str = dias_semana[dt_obj.weekday()]

    return {
        "local": location_label,
        "latitude": float(payload.get("latitude", latitude)),
        "longitude": float(payload.get("longitude", longitude)),
        "data_iso": date_str,
        "data_formatada": dt_obj.strftime("%d/%m/%Y"),
        "dia_semana": dia_semana_str,
        "fuso": payload.get("timezone", "UTC"),
        "temp_max_c": tmax,
        "temp_min_c": tmin,
        "temp_media_c": temp_media,
        "amplitude_termica_c": (tmax - tmin) if (tmax is not None and tmin is not None) else None,
        "precipitacao_total_mm": psum if psum is not None else 0.0,
        "vento_max_kmh": wmax,
        "pressao_media_hpa": press_media,
        "umidade_media_pct": umid_media,
        "nascer_sol": sunrise[-5:] if sunrise else "-",
        "por_sol": sunset[-5:] if sunset else "-",
        "condicao": weather_description(code_daily),
        "hourly": hourly_records,
    }


def fetch_annual_dataset(
    latitude: float,
    longitude: float,
    location_name: str,
    year: int,
) -> tuple[StationDataset, bytes]:
    """Baixa 1 ano inteiro de histórico climático (8.760 horas) para uma localização e gera CSV e StationDataset."""
    start_date = f"{year}-01-01"
    now = pd.Timestamp.now()
    if year >= now.year:
        end_date = (now - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        primary_url = FORECAST_URL
        fallback_url = ARCHIVE_URL
    else:
        end_date = f"{year}-12-31"
        primary_url = ARCHIVE_URL
        fallback_url = FORECAST_URL

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,precipitation",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto",
    }

    try:
        resp = requests.get(primary_url, params=params, timeout=25)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        resp = requests.get(fallback_url, params=params, timeout=25)
        resp.raise_for_status()
        payload = resp.json()

    raw_hourly = payload.get("hourly", {}) or {}
    times = raw_hourly.get("time", [])
    if not times:
        raise ValueError(f"Nenhum dado retornado para o ano {year} nas coordenadas ({latitude}, {longitude}).")

    dt_series = pd.to_datetime(times, errors="coerce")
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

    metadata = {
        "nome": f"{location_name.upper()} ({year})",
        "codigo_estacao": "OPEN-METEO-ERA5",
        "latitude": f"{latitude:.2f}",
        "longitude": f"{longitude:.2f}",
        "ano": str(year),
        "total_registros": str(len(df)),
    }

    safe_name = "".join(c if c.isalnum() else "_" for c in location_name).strip("_")
    source_name = f"climaps_{safe_name}_{year}.csv"
    dataset = StationDataset(
        metadata=metadata,
        data=df,
        source=Path(source_name),
    )

    # Gera conteúdo CSV formatado com cabeçalho de metadados legível pelo ClimaPS
    header_meta = [
        f"Nome: {location_name.upper()} ({year})",
        "Codigo Estacao: OPEN-METEO-ERA5",
        f"Latitude: {latitude:.4f}",
        f"Longitude: {longitude:.4f}",
        f"Ano: {year}",
        "Fonte: Open-Meteo Reanalysis ERA5",
        "",
    ]
    meta_str = "\n".join(header_meta) + "\n"
    csv_body = df.to_csv(
        sep=";",
        decimal=",",
        index=False,
        date_format="%Y-%m-%d %H:%M",
    )
    full_csv_text = meta_str + csv_body
    csv_bytes = full_csv_text.encode("utf-8-sig")

    return dataset, csv_bytes
