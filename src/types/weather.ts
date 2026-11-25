export interface WeatherRecord {
  id: number;
  data: string; // YYYY-MM-DD
  hora: number; // 0..2300
  data_hora: string; // YYYY-MM-DD HH:MM:SS
  timestamp: number; // ms since epoch (local/naive UTC-normalized)
  precipitacao_mm: number | null;
  temp_max_c: number | null;
  temp_min_c: number | null;
  hora_num: number; // 0..23
  mes: number; // 1..12
  dia: string; // YYYY-MM-DD
}

export interface ColumnMissingStat {
  key: string;
  label: string;
  total: number;
  missingCount: number;
  validCount: number;
  missingPct: number;
  exceedsThreshold: boolean;
  source: 'core' | 'extra';
}

export interface StationDataset {
  metadata: Record<string, string>;
  data: WeatherRecord[];
  sourceName: string;
  extraColumnMissing?: ColumnMissingStat[];
}

export interface SavedFileEntry {
  id: string;
  folder: string;
  name: string;
  url?: string;
  csvText?: string;
  dataset?: StationDataset;
}

export interface FilterSpec {
  start: string; // YYYY-MM-DD
  end: string; // YYYY-MM-DD
  hourStart: number; // 0..23
  hourEnd: number; // 0..23
  rainyOnly: boolean;
}

export interface CityMatch {
  id?: number;
  name: string;
  admin1?: string;
  country?: string;
  country_code?: string;
  latitude: number;
  longitude: number;
}

export interface StormRisk {
  nivel: string;
  cor: string;
  classe: 'storm-high' | 'storm-med' | 'storm-low';
  icone: string;
  detalhe: string;
}

export interface AirQualityInfo {
  status: string;
  cor: string;
  badge_class: string;
  icone: string;
  recomendacao: string;
}

export interface AirQualityData {
  us_aqi: number | null;
  european_aqi: number | null;
  pm2_5: number | null;
  pm10: number | null;
  co: number | null;
  no2: number | null;
  o3: number | null;
  dust: number | null;
  info: AirQualityInfo;
  erro?: string;
}

export interface UvInfo {
  status: string;
  cor: string;
  icone: string;
  recomendacao: string;
}

export interface ClimateAnomaly {
  has_history: boolean;
  mes_num: number;
  mes_nome: string;
  hist_temp_mean: number;
  hist_max_mean: number;
  hist_min_mean: number;
  hist_rain_daily_avg: number;
  curr_temp: number;
  curr_rain: number;
  delta_temp: number;
  delta_rain: number;
  summary_text: string;
  status: 'quente' | 'frio' | 'neutro';
}

export interface HourlyForecastItem {
  data_hora_raw: string;
  hora_label: string;
  temperatura_c: number | null;
  prob_chuva_pct: number;
  chuva_mm: number;
  condicao: string;
}

export interface DailyForecastItem {
  data_raw: string;
  data_label: string;
  temp_max_c: number | null;
  temp_min_c: number | null;
  prob_chuva_pct: number;
  chuva_mm: number;
  condicao: string;
}

export interface LivePointWeather {
  local: string;
  latitude: number;
  longitude: number;
  fuso: string;
  horario_raw: string;
  horario: string;
  temperatura_c: number | null;
  sensacao_c: number | null;
  umidade_pct: number | null;
  precipitacao_mm: number | null;
  nuvens_pct: number | null;
  pressao_hpa: number | null;
  vento_kmh: number | null;
  rajadas_kmh: number | null;
  periodo: 'Dia' | 'Noite';
  uv_max: number | null;
  uv_info: UvInfo;
  nascer_sol: string;
  por_sol: string;
  condicao: string;
  ponto_orvalho_c: number | null;
  indice_calor_c: number | null;
  indice_calor_desc: string;
  indice_calor_nivel: string;
  risco_tempestade: StormRisk;
  forecast_hourly: HourlyForecastItem[];
  forecast_daily: DailyForecastItem[];
  air_quality?: AirQualityData;
}

export interface HistoricalHourlyRecord {
  data_hora_raw: string;
  hora_label: string;
  temperatura_c: number | null;
  chuva_mm: number;
  umidade_pct: number | null;
  vento_kmh: number | null;
  condicao: string;
}

export interface HistoricalDayWeather {
  local: string;
  latitude: number;
  longitude: number;
  data_iso: string;
  data_formatada: string;
  dia_semana: string;
  fuso: string;
  temp_max_c: number | null;
  temp_min_c: number | null;
  temp_media_c: number | null;
  amplitude_termica_c: number | null;
  precipitacao_total_mm: number;
  vento_max_kmh: number | null;
  pressao_media_hpa: number | null;
  umidade_media_pct: number | null;
  nascer_sol: string;
  por_sol: string;
  condicao: string;
  hourly: HistoricalHourlyRecord[];
}

export interface LiveWeatherBundle {
  location_label: string;
  latitude: number;
  longitude: number;
  dataset: StationDataset;
}

export interface KpiResult {
  registros: number;
  precipitacao_total: number;
  temp_max_media: number | null;
  temp_min_media: number | null;
  completude: number;
}

export interface MonthlySummaryRow {
  mes: number;
  mes_nome: string;
  registros: number;
  precipitacao_mm: number;
  temp_max_media: number | null;
  temp_min_media: number | null;
  horas_com_chuva: number;
}

export interface DailySummaryRow {
  dia: string;
  label: string;
  mes: number;
  precipitacao_mm: number;
  temp_max_media: number | null;
  temp_min_media: number | null;
}

export interface QualityReport {
  linhas: number;
  duplicadas: number;
  timestamps_duplicados: number;
  timestamps_ausentes: number;
  datas_invalidas: number;
  valores_ausentes: {
    precipitacao_mm: number;
    temp_max_c: number;
    temp_min_c: number;
  };
  outliers_iqr: {
    precipitacao_mm: number;
    temp_max_c: number;
    temp_min_c: number;
  };
  chuva_negativa: number;
  chuva_extrema_fisica: number;
  temp_inconsistente: number;
}

export interface PrecipitationHistogramBin {
  id: string;
  rangeLabel: string;
  min: number;
  max: number;
  count: number;
  densityPct: number;
  isExtreme: boolean;
}

export interface PrecipitationHistogramResult {
  totalValid: number;
  zeroCount: number;
  rainyCount: number;
  q1: number | null;
  median: number | null;
  q3: number | null;
  iqr: number | null;
  upperFence: number | null;
  p95: number | null;
  maxVal: number | null;
  extremeCount: number;
  extremePct: number;
  firstExtremeBinLabel: string | null;
  bins: PrecipitationHistogramBin[];
}

export interface ClimatologicalBaselineStat {
  mean: number | null;
  std: number | null;
  low: number | null;
  high: number | null;
  sampleCount: number;
}

export interface ClimatologicalAlertFlag {
  variable: 'rain' | 'tempMax' | 'tempMin';
  label: string;
  zScore: number;
  severity: 'alerta' | 'critico';
}

export interface ClimatologicalAlertRecord {
  record: WeatherRecord;
  flags: ClimatologicalAlertFlag[];
  maxAbsZ: number;
  signedPeakZ: number;
  severity: 'alerta' | 'critico';
}

export interface ClimatologicalMonitorResult {
  sigmaThreshold: number;
  totalEvaluated: number;
  alertCount: number;
  criticalCount: number;
  countsByVar: {
    rain: number;
    tempMax: number;
    tempMin: number;
  };
  baselines: {
    rain: ClimatologicalBaselineStat;
    tempMax: ClimatologicalBaselineStat;
    tempMin: ClimatologicalBaselineStat;
  };
  alerts: ClimatologicalAlertRecord[];
}
