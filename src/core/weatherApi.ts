import type {
  AirQualityData,
  CityMatch,
  DailyForecastItem,
  HistoricalDayWeather,
  HistoricalHourlyRecord,
  HourlyForecastItem,
  LivePointWeather,
  LiveWeatherBundle,
  StationDataset,
  WeatherRecord,
} from '../types/weather';
import {
  calculateDewPoint,
  calculateHeatIndex,
  classifyAirQuality,
  classifyUv,
  evaluateStormRisk,
} from './analysis';
import { buildCsvExport } from './dataLoader';
import { formatDatetimeFriendly } from './formatters';

const GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search';
const FORECAST_URL = 'https://api.open-meteo.com/v1/forecast';
const AIR_QUALITY_URL = 'https://air-quality-api.open-meteo.com/v1/air-quality';
const ARCHIVE_URL = 'https://archive-api.open-meteo.com/v1/archive';

export const WORLD_DEFAULTS: Array<[string, number, number]> = [
  ['Manaus (BR)', -3.1, -60.02],
  ['São Paulo (BR)', -23.55, -46.63],
  ['Nova York (US)', 40.71, -74.01],
  ['Londres (UK)', 51.51, -0.13],
  ['Paris (FR)', 48.86, 2.35],
  ['Tóquio (JP)', 35.68, 139.69],
  ['Cairo (EG)', 30.04, 31.24],
  ['Cidade do Cabo (ZA)', -33.92, 18.42],
  ['Sydney (AU)', -33.87, 151.21],
  ['Moscou (RU)', 55.75, 37.62],
];

export const WMO_CODES_PT: Record<number, string> = {
  0: '☀️ Céu limpo',
  1: '🌤️ Predominantemente limpo',
  2: '⛅ Parcialmente nublado',
  3: '☁️ Nublado',
  45: '🌫️ Neblina',
  48: '🌫️ Nevoeiro',
  51: '🌦️ Garoa leve',
  53: '🌦️ Garoa moderada',
  55: '🌦️ Garoa intensa',
  61: '🌧️ Chuva fraca',
  63: '🌧️ Chuva moderada',
  65: '🌧️ Chuva forte',
  80: '🌦️ Pancadas leves',
  81: '🌧️ Pancadas moderadas',
  82: '⛈️ Pancadas fortes',
  95: '⛈️ Tempestade',
  96: '⛈️ Tempestade com granizo',
  99: '⛈️ Tempestade severa',
};

export function weatherDescription(code: number | null | undefined): string {
  if (code === null || code === undefined || Number.isNaN(code)) {
    return 'Condição indisponível';
  }
  const intCode = Math.trunc(code);
  return WMO_CODES_PT[intCode] ?? `Código WMO ${intCode}`;
}

// Simple TTL cache matching @st.cache_data
const apiCache = new Map<string, { expiresAt: number; data: unknown }>();

async function cachedFetch<T>(key: string, ttlSeconds: number, fn: () => Promise<T>): Promise<T> {
  const now = Date.now();
  const hit = apiCache.get(key);
  if (hit && hit.expiresAt > now) {
    return hit.data as T;
  }
  const data = await fn();
  apiCache.set(key, { expiresAt: now + ttlSeconds * 1000, data });
  return data;
}

async function fetchJson(url: string, params: Record<string, string | number>): Promise<any> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => qs.set(k, String(v)));
  const resp = await fetch(`${url}?${qs.toString()}`);
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status} ao consultar Open-Meteo`);
  }
  return resp.json();
}

export async function searchCity(cityName: string, count = 10): Promise<CityMatch[]> {
  const trimmed = cityName.trim();
  if (!trimmed) return [];
  return cachedFetch(`geo:${trimmed.toLowerCase()}:${count}`, 300, async () => {
    const json = await fetchJson(GEOCODING_URL, {
      name: trimmed,
      count,
      language: 'pt',
      format: 'json',
    });
    return (json.results || []) as CityMatch[];
  });
}

export async function fetchAirQuality(latitude: number, longitude: number): Promise<AirQualityData> {
  try {
    const json = await fetchJson(AIR_QUALITY_URL, {
      latitude,
      longitude,
      current: 'european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone,dust',
    });
    const cur = json.current || {};
    const usAqi = cur.us_aqi ?? null;
    const pm25 = cur.pm2_5 ?? null;
    return {
      us_aqi: usAqi,
      european_aqi: cur.european_aqi ?? null,
      pm2_5: pm25,
      pm10: cur.pm10 ?? null,
      co: cur.carbon_monoxide ?? null,
      no2: cur.nitrogen_dioxide ?? null,
      o3: cur.ozone ?? null,
      dust: cur.dust ?? null,
      info: classifyAirQuality(usAqi, pm25),
    };
  } catch (err) {
    return {
      us_aqi: null,
      european_aqi: null,
      pm2_5: null,
      pm10: null,
      co: null,
      no2: null,
      o3: null,
      dust: null,
      info: classifyAirQuality(null, null),
      erro: err instanceof Error ? err.message : String(err),
    };
  }
}

function parsePointPayload(payload: any, label: string, lat: number, lon: number): LivePointWeather {
  const cur = payload.current || {};
  const daily = payload.daily || {};
  const hourly = payload.hourly || {};

  const sunriseVal: string = (daily.sunrise && daily.sunrise[0]) || '';
  const sunsetVal: string = (daily.sunset && daily.sunset[0]) || '';

  const tempC: number | null = cur.temperature_2m ?? null;
  const humid: number | null = cur.relative_humidity_2m ?? null;
  const press: number | null = cur.pressure_msl ?? null;
  const wind: number | null = cur.wind_speed_10m ?? null;
  const gust: number | null = cur.wind_gusts_10m ?? null;
  const rain: number | null = cur.precipitation ?? null;
  const uvMax: number | null = (daily.uv_index_max && daily.uv_index_max[0]) ?? null;

  const dewPoint = calculateDewPoint(tempC, humid);
  const hi = calculateHeatIndex(tempC, humid);
  const stormRisk = evaluateStormRisk(press, humid, wind, gust, rain);
  const uvInfo = classifyUv(uvMax);

  const hourlyTimes: string[] = hourly.time || [];
  const hourlyTemps: Array<number | null> = hourly.temperature_2m || [];
  const hourlyProbs: Array<number | null> = hourly.precipitation_probability || [];
  const hourlyRains: Array<number | null> = hourly.precipitation || [];
  const hourlyCodes: Array<number | null> = hourly.weather_code || [];

  const forecastHourly: HourlyForecastItem[] = [];
  const hLimit = Math.min(48, hourlyTimes.length, hourlyTemps.length);
  for (let i = 0; i < hLimit; i++) {
    const t = hourlyTimes[i];
    forecastHourly.push({
      data_hora_raw: t,
      hora_label: t.slice(-5),
      temperatura_c: hourlyTemps[i] ?? null,
      prob_chuva_pct: hourlyProbs[i] ?? 0,
      chuva_mm: hourlyRains[i] ?? 0,
      condicao: weatherDescription(hourlyCodes[i]),
    });
  }

  const dailyTimes: string[] = daily.time || [];
  const dailyTmax: Array<number | null> = daily.temperature_2m_max || [];
  const dailyTmin: Array<number | null> = daily.temperature_2m_min || [];
  const dailyProbs: Array<number | null> = daily.precipitation_probability_max || [];
  const dailySums: Array<number | null> = daily.precipitation_sum || [];
  const dailyCodes: Array<number | null> = daily.weather_code || [];

  const forecastDaily: DailyForecastItem[] = [];
  const dLimit = Math.min(14, dailyTimes.length, dailyTmax.length);
  for (let i = 0; i < dLimit; i++) {
    const d = dailyTimes[i];
    const diaStr = d.length >= 10 ? `${d.slice(8, 10)}/${d.slice(5, 7)}` : d;
    forecastDaily.push({
      data_raw: d,
      data_label: diaStr,
      temp_max_c: dailyTmax[i] ?? null,
      temp_min_c: dailyTmin[i] ?? null,
      prob_chuva_pct: dailyProbs[i] ?? 0,
      chuva_mm: dailySums[i] ?? 0,
      condicao: weatherDescription(dailyCodes[i]),
    });
  }

  return {
    local: label,
    latitude: Number(payload.latitude ?? lat),
    longitude: Number(payload.longitude ?? lon),
    fuso: payload.timezone || 'UTC',
    horario_raw: cur.time || '',
    horario: formatDatetimeFriendly(cur.time || ''),
    temperatura_c: tempC,
    sensacao_c: cur.apparent_temperature ?? null,
    umidade_pct: humid,
    precipitacao_mm: rain,
    nuvens_pct: cur.cloud_cover ?? null,
    pressao_hpa: press,
    vento_kmh: wind,
    rajadas_kmh: gust,
    periodo: (cur.is_day ?? 1) === 1 ? 'Dia' : 'Noite',
    uv_max: uvMax,
    uv_info: uvInfo,
    nascer_sol: sunriseVal ? sunriseVal.slice(-5) : '-',
    por_sol: sunsetVal ? sunsetVal.slice(-5) : '-',
    condicao: weatherDescription(cur.weather_code),
    ponto_orvalho_c: dewPoint,
    indice_calor_c: hi.value,
    indice_calor_desc: hi.description,
    indice_calor_nivel: hi.level,
    risco_tempestade: stormRisk,
    forecast_hourly: forecastHourly,
    forecast_daily: forecastDaily,
  };
}

export async function fetchCurrentPoint(
  latitude: number,
  longitude: number,
  locationLabel: string
): Promise<LivePointWeather> {
  return cachedFetch(`pt:${latitude.toFixed(3)}:${longitude.toFixed(3)}:${locationLabel}`, 300, async () => {
    const payload = await fetchJson(FORECAST_URL, {
      latitude,
      longitude,
      current:
        'temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_gusts_10m',
      hourly: 'temperature_2m,precipitation_probability,precipitation,weather_code',
      daily: 'temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,uv_index_max,sunrise,sunset,weather_code',
      forecast_days: 14,
      timezone: 'auto',
    });
    const parsed = parsePointPayload(payload, locationLabel, latitude, longitude);
    parsed.air_quality = await fetchAirQuality(latitude, longitude);
    return parsed;
  });
}

export async function fetchMultiplePoints(
  locations: Array<[string, number, number]>
): Promise<LivePointWeather[]> {
  if (locations.length === 0) return [];
  const key = `multi:${locations.map((l) => `${l[0]}:${l[1]}:${l[2]}`).join('|')}`;
  return cachedFetch(key, 300, async () => {
    const raw = await fetchJson(FORECAST_URL, {
      latitude: locations.map((l) => l[1]).join(','),
      longitude: locations.map((l) => l[2]).join(','),
      current:
        'temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_gusts_10m',
      daily: 'uv_index_max,sunrise,sunset',
      forecast_days: 1,
      timezone: 'auto',
    });
    const items = Array.isArray(raw) ? raw : [raw];
    return locations.map(([label, lat, lon], idx) => parsePointPayload(items[idx] || {}, label, lat, lon));
  });
}

function buildRecordsFromHourly(
  times: string[],
  temps: Array<number | null>,
  rains: Array<number | null>,
  cutoffIso?: string
): WeatherRecord[] {
  const records: WeatherRecord[] = [];
  for (let i = 0; i < times.length; i++) {
    const t = times[i];
    if (!t) continue;
    if (cutoffIso && t > cutoffIso) continue;
    const match = t.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
    if (!match) continue;
    const y = Number(match[1]);
    const m = Number(match[2]);
    const d = Number(match[3]);
    const hh = Number(match[4]);
    const mm = Number(match[5]);
    const dia = `${match[1]}-${match[2]}-${match[3]}`;
    const dataHora = `${dia} ${match[4]}:${match[5]}:00`;
    const tempVal = temps[i] !== undefined && temps[i] !== null ? Number(temps[i]) : null;
    const rainVal = rains[i] !== undefined && rains[i] !== null ? Number(rains[i]) : null;

    records.push({
      id: records.length,
      data: dia,
      hora: hh * 100,
      data_hora: dataHora,
      timestamp: Date.UTC(y, m - 1, d, hh, mm, 0),
      precipitacao_mm: rainVal,
      temp_max_c: tempVal,
      temp_min_c: tempVal,
      hora_num: hh,
      mes: m,
      dia,
    });
  }
  return records;
}

export async function fetchLiveWeather(
  latitude: number,
  longitude: number,
  locationName: string,
  pastDays = 30,
  forecastDays = 7
): Promise<LiveWeatherBundle> {
  const payload = await fetchJson(FORECAST_URL, {
    latitude,
    longitude,
    current: 'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code',
    hourly: 'temperature_2m,precipitation',
    daily: 'temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code',
    past_days: pastDays,
    forecast_days: forecastDays,
    timezone: 'auto',
  });

  const rawCurrent = payload.current || {};
  const rawHourly = payload.hourly || {};
  const cutoffIso: string | undefined = rawCurrent.time || undefined;

  let records = buildRecordsFromHourly(
    rawHourly.time || [],
    rawHourly.temperature_2m || [],
    rawHourly.precipitation || [],
    cutoffIso
  );
  if (records.length === 0) {
    records = buildRecordsFromHourly(rawHourly.time || [], rawHourly.temperature_2m || [], rawHourly.precipitation || []);
  }

  const dataset: StationDataset = {
    metadata: {
      nome: locationName.toUpperCase(),
      codigo_estacao: 'OPEN-METEO',
      latitude: String(latitude),
      longitude: String(longitude),
    },
    data: records,
    sourceName: `api_open_meteo_${locationName.replace(/\s+/g, '_')}.json`,
  };

  return {
    location_label: locationName,
    latitude,
    longitude,
    dataset,
  };
}

export async function fetchHistoricalDay(
  latitude: number,
  longitude: number,
  locationLabel: string,
  targetDate: string
): Promise<HistoricalDayWeather> {
  const dateStr = targetDate.slice(0, 10);
  return cachedFetch(`histday:${latitude.toFixed(3)}:${longitude.toFixed(3)}:${dateStr}`, 3600, async () => {
    const today = new Date();
    const targetDt = new Date(`${dateStr}T12:00:00Z`);
    const daysDiff = Math.floor((today.getTime() - targetDt.getTime()) / (86400 * 1000));

    const primaryUrl = daysDiff > 5 ? ARCHIVE_URL : FORECAST_URL;
    const fallbackUrl = primaryUrl === ARCHIVE_URL ? FORECAST_URL : ARCHIVE_URL;

    const params = {
      latitude,
      longitude,
      start_date: dateStr,
      end_date: dateStr,
      hourly: 'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,surface_pressure,wind_speed_10m,weather_code',
      daily: 'temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,sunrise,sunset,weather_code',
      timezone: 'auto',
    };

    let payload: any;
    try {
      payload = await fetchJson(primaryUrl, params);
    } catch {
      payload = await fetchJson(fallbackUrl, params);
    }

    const daily = payload.daily || {};
    const hourly = payload.hourly || {};

    const tmax: number | null = (daily.temperature_2m_max && daily.temperature_2m_max[0]) ?? null;
    const tmin: number | null = (daily.temperature_2m_min && daily.temperature_2m_min[0]) ?? null;
    const psum: number = (daily.precipitation_sum && daily.precipitation_sum[0]) ?? 0;
    const wmax: number | null = (daily.wind_speed_10m_max && daily.wind_speed_10m_max[0]) ?? null;
    const sunrise: string = (daily.sunrise && daily.sunrise[0]) || '';
    const sunset: string = (daily.sunset && daily.sunset[0]) || '';
    const codeDaily: number | null = (daily.weather_code && daily.weather_code[0]) ?? null;

    const hourlyTimes: string[] = hourly.time || [];
    const hourlyTemps: Array<number | null> = hourly.temperature_2m || [];
    const hourlyHumids: Array<number | null> = hourly.relative_humidity_2m || [];
    const hourlyRains: Array<number | null> = hourly.precipitation || [];
    const hourlyPress: Array<number | null> = hourly.surface_pressure || [];
    const hourlyWinds: Array<number | null> = hourly.wind_speed_10m || [];
    const hourlyCodes: Array<number | null> = hourly.weather_code || [];

    const hourlyRecords: HistoricalHourlyRecord[] = hourlyTimes.map((t, i) => ({
      data_hora_raw: t,
      hora_label: t.length >= 5 ? t.slice(-5) : `${String(i).padStart(2, '0')}:00`,
      temperatura_c: hourlyTemps[i] ?? null,
      chuva_mm: hourlyRains[i] ?? 0,
      umidade_pct: hourlyHumids[i] ?? null,
      vento_kmh: hourlyWinds[i] ?? null,
      condicao: weatherDescription(hourlyCodes[i]),
    }));

    const validTemps = hourlyTemps.filter((v): v is number => v !== null && !Number.isNaN(v));
    const validHum = hourlyHumids.filter((v): v is number => v !== null && !Number.isNaN(v));
    const validPress = hourlyPress.filter((v): v is number => v !== null && !Number.isNaN(v));

    const avg = (arr: number[]) => (arr.length > 0 ? arr.reduce((a, b) => a + b, 0) / arr.length : null);

    const diasSemana = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado'];
    const [yy, mm, dd] = dateStr.split('-').map(Number);
    const localDate = new Date(Date.UTC(yy, mm - 1, dd, 12, 0, 0));

    return {
      local: locationLabel,
      latitude: Number(payload.latitude ?? latitude),
      longitude: Number(payload.longitude ?? longitude),
      data_iso: dateStr,
      data_formatada: `${String(dd).padStart(2, '0')}/${String(mm).padStart(2, '0')}/${yy}`,
      dia_semana: diasSemana[localDate.getUTCDay()],
      fuso: payload.timezone || 'UTC',
      temp_max_c: tmax,
      temp_min_c: tmin,
      temp_media_c: avg(validTemps),
      amplitude_termica_c: tmax !== null && tmin !== null ? tmax - tmin : null,
      precipitacao_total_mm: psum,
      vento_max_kmh: wmax,
      pressao_media_hpa: avg(validPress),
      umidade_media_pct: avg(validHum),
      nascer_sol: sunrise ? sunrise.slice(-5) : '-',
      por_sol: sunset ? sunset.slice(-5) : '-',
      condicao: weatherDescription(codeDaily),
      hourly: hourlyRecords,
    };
  });
}

export async function fetchAnnualDataset(
  latitude: number,
  longitude: number,
  locationName: string,
  year: number
): Promise<{ dataset: StationDataset; csvText: string; csvFilename: string }> {
  return cachedFetch(`annual:${latitude.toFixed(3)}:${longitude.toFixed(3)}:${year}:${locationName}`, 86400, async () => {
    const startDate = `${year}-01-01`;
    const now = new Date();
    const nowYear = now.getFullYear();

    let endDate: string;
    let primaryUrl: string;
    let fallbackUrl: string;

    if (year >= nowYear) {
      const yesterday = new Date(now.getTime() - 86400 * 1000);
      const pad2 = (n: number) => String(n).padStart(2, '0');
      endDate = `${yesterday.getFullYear()}-${pad2(yesterday.getMonth() + 1)}-${pad2(yesterday.getDate())}`;
      primaryUrl = ARCHIVE_URL;
      fallbackUrl = FORECAST_URL;
    } else {
      endDate = `${year}-12-31`;
      primaryUrl = ARCHIVE_URL;
      fallbackUrl = FORECAST_URL;
    }

    const params = {
      latitude,
      longitude,
      start_date: startDate,
      end_date: endDate,
      hourly: 'temperature_2m,precipitation',
      timezone: 'auto',
    };

    let payload: any;
    try {
      payload = await fetchJson(primaryUrl, params);
    } catch {
      payload = await fetchJson(fallbackUrl, params);
    }

    const rawHourly = payload.hourly || {};
    const times: string[] = rawHourly.time || [];
    if (times.length === 0) {
      throw new Error(`Nenhum dado retornado para o ano ${year} nas coordenadas (${latitude}, ${longitude}).`);
    }

    const records = buildRecordsFromHourly(times, rawHourly.temperature_2m || [], rawHourly.precipitation || []);
    const safeName = locationName.replace(/[^A-Za-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'local';
    const csvFilename = `climaps_${safeName}_${year}.csv`;

    const dataset: StationDataset = {
      metadata: {
        nome: `${locationName.toUpperCase()} (${year})`,
        codigo_estacao: 'OPEN-METEO-ERA5',
        latitude: latitude.toFixed(2),
        longitude: longitude.toFixed(2),
        ano: String(year),
        total_registros: String(records.length),
      },
      data: records,
      sourceName: csvFilename,
    };

    const headerMeta = [
      `Nome: ${locationName.toUpperCase()} (${year})`,
      'Codigo Estacao: OPEN-METEO-ERA5',
      `Latitude: ${latitude.toFixed(4)}`,
      `Longitude: ${longitude.toFixed(4)}`,
      `Ano: ${year}`,
      'Fonte: Open-Meteo Reanalysis ERA5',
      '',
    ];
    const csvText = buildCsvExport(records, headerMeta);

    return { dataset, csvText, csvFilename };
  });
}
