from dataclasses import dataclass  # Importa dataclass para estruturar o pacote de retorno da API
from pathlib import Path  # Usado para criar um Path simbólico identificando a origem dos dados da API

import pandas as pd  # Manipulação de séries temporais e DataFrames
import requests  # Biblioteca para fazer requisições HTTP à API Open-Meteo

from climaps.core.data_loader import StationDataset  # Reaproveita a estrutura StationDataset usada pelo resto do app
from climaps.ui_styles import format_datetime_friendly  # Formata datas/horas no padrão brasileiro amigável


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"  # Endpoint público de busca de cidades por nome (Open-Meteo)
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"  # Endpoint público de previsão e clima atual (Open-Meteo)

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


def _parse_point_payload(payload: dict[str, object], label: str, lat: float, lon: float) -> dict[str, object]:  # Extrai e padroniza o JSON de um ponto
    cur = payload.get("current", {}) or {}  # Obtém o bloco "current" do JSON (garantindo dicionário mesmo se vier None)
    daily = payload.get("daily", {}) or {}  # Obtém o bloco "daily" do JSON
    sunrise_val = (daily.get("sunrise") or [""])[0] or ""  # Pega a primeira string de nascer do sol (se existir)
    sunset_val = (daily.get("sunset") or [""])[0] or ""  # Pega a primeira string de pôr do sol (se existir)

    return {  # Retorna um dicionário plano com chaves em português para a interface
        "local": label,  # Nome de exibição do local
        "latitude": float(payload.get("latitude", lat)),  # Latitude retornada pela grade da API (ou a solicitada)
        "longitude": float(payload.get("longitude", lon)),  # Longitude retornada pela grade da API (ou a solicitada)
        "fuso": payload.get("timezone", "UTC"),  # Fuso horário local detectado pela API
        "horario": format_datetime_friendly(cur.get("time", "")),  # Data/hora da medição atual formatada
        "temperatura_c": cur.get("temperature_2m"),  # Temperatura a 2 metros de altura (°C)
        "sensacao_c": cur.get("apparent_temperature"),  # Sensação térmica (°C)
        "umidade_pct": cur.get("relative_humidity_2m"),  # Umidade relativa do ar (%)
        "precipitacao_mm": cur.get("precipitation"),  # Precipitação atual (mm)
        "nuvens_pct": cur.get("cloud_cover"),  # Cobertura de nuvens (%)
        "pressao_hpa": cur.get("pressure_msl"),  # Pressão atmosférica ao nível do mar (hPa)
        "vento_kmh": cur.get("wind_speed_10m"),  # Velocidade do vento a 10 metros (km/h)
        "rajadas_kmh": cur.get("wind_gusts_10m"),  # Rajadas de vento a 10 metros (km/h)
        "periodo": "Dia" if cur.get("is_day", 1) == 1 else "Noite",  # Converte flag is_day (1/0) para "Dia" ou "Noite"
        "uv_max": (daily.get("uv_index_max") or [None])[0],  # Índice UV máximo previsto para o dia
        "nascer_sol": sunrise_val[-5:] if sunrise_val else "-",  # Extrai apenas "HH:MM" dos últimos 5 caracteres
        "por_sol": sunset_val[-5:] if sunset_val else "-",  # Extrai apenas "HH:MM" dos últimos 5 caracteres
        "condicao": weather_description(cur.get("weather_code")),  # Converte o código WMO para descrição com emoji
    }  # Fecha dicionário retornado


def fetch_current_point(latitude: float, longitude: float, location_label: str) -> dict[str, object]:  # Consulta clima atual de uma coordenada
    """Busca o clima ao vivo de qualquer coordenada do mundo."""  # Docstring da função
    params = {  # Monta o dicionário de parâmetros da query string
        "latitude": latitude,  # Latitude alvo
        "longitude": longitude,  # Longitude alvo
        "current": (  # Lista de variáveis instantâneas desejadas separadas por vírgula
            "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,"  # Temperatura, umidade, sensação, dia/noite
            "precipitation,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_gusts_10m"  # Chuva, código WMO, nuvens, pressão, vento e rajadas
        ),  # Fecha string de variáveis "current"
        "daily": "uv_index_max,sunrise,sunset",  # Variáveis diárias adicionais (UV máximo, nascer e pôr do sol)
        "forecast_days": 1,  # Solicita apenas o dia atual para resposta rápida
        "timezone": "auto",  # Ajusta automaticamente os horários para o fuso do ponto consultado
    }  # Fecha params
    response = requests.get(FORECAST_URL, params=params, timeout=12)  # Faz requisição GET com timeout de 12 segundos
    response.raise_for_status()  # Verifica se não houve erro HTTP
    return _parse_point_payload(response.json(), location_label, latitude, longitude)  # Normaliza e retorna o payload JSON


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