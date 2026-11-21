import React, { useEffect, useMemo, useState } from 'react';
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  Activity,
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Compass,
  Database,
  Download,
  ExternalLink,
  Globe,
  Loader2,
  MapPin,
  Pin,
  Search,
  ShieldAlert,
  Trash2,
  Wind,
} from 'lucide-react';
import type {
  CityMatch,
  HistoricalDayWeather,
  LivePointWeather,
  StationDataset,
  WeatherRecord,
} from '../types/weather';
import {
  WORLD_DEFAULTS,
  fetchAnnualDataset,
  fetchCurrentPoint,
  fetchHistoricalDay,
  fetchLiveWeather,
  fetchMultiplePoints,
  searchCity,
} from '../core/weatherApi';
import { MESES_PT, calculateClimateAnomaly } from '../core/analysis';
import { brNumber, formatDatetimeFriendly } from '../core/formatters';
import { WeatherConditionIcon, cleanConditionText } from '../core/weatherIcons';
import { MetricCard } from './MetricCard';

interface WorldLiveTabProps {
  isDark: boolean;
  activeRecords: WeatherRecord[] | null;
  onLoadDatasetIntoSession: (dataset: StationDataset, toastMessage: string, csvText?: string) => void;
}

type SearchMode = 'city' | 'coords';
type ToolMode = 'live' | 'calendar' | 'annual';
type ForecastScope = '24h' | '7d' | '14d';
type WindyLayer = 'wind' | 'temp' | 'rain' | 'clouds' | 'pressure';

function downloadTextFile(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function getYesterdayIso(): string {
  const d = new Date(Date.now() - 86400 * 1000);
  const pad2 = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

function getMaxCalendarIso(): string {
  const d = new Date(Date.now() + 7 * 86400 * 1000);
  const pad2 = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

export const WorldLiveTab: React.FC<WorldLiveTabProps> = ({
  isDark,
  activeRecords,
  onLoadDatasetIntoSession,
}) => {
  const [searchMode, setSearchMode] = useState<SearchMode>('city');
  const [cityQuery, setCityQuery] = useState('Manaus');
  const [matches, setMatches] = useState<CityMatch[]>([]);
  const [selectedMatchIdx, setSelectedMatchIdx] = useState(0);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [coordLat, setCoordLat] = useState(-3.1);
  const [coordLon, setCoordLon] = useState(-60.02);
  const [coordLabel, setCoordLabel] = useState('Ponto personalizado');

  const [toolMode, setToolMode] = useState<ToolMode>('live');
  const [forecastScope, setForecastScope] = useState<ForecastScope>('24h');
  const [aqiOpen, setAqiOpen] = useState(true);

  const [weather, setWeather] = useState<LivePointWeather | null>(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [weatherError, setWeatherError] = useState<string | null>(null);
  const [loading30d, setLoading30d] = useState(false);

  const [calDate, setCalDate] = useState(getYesterdayIso());
  const [histDay, setHistDay] = useState<HistoricalDayWeather | null>(null);
  const [histDayLoading, setHistDayLoading] = useState(false);
  const [histDayError, setHistDayError] = useState<string | null>(null);
  const [histTableOpen, setHistTableOpen] = useState(false);

  const currentYear = new Date().getFullYear();
  const [annualYear, setAnnualYear] = useState(currentYear - 1);
  const [annualResult, setAnnualResult] = useState<{
    dataset: StationDataset;
    csvText: string;
    csvFilename: string;
  } | null>(null);
  const [annualLoading, setAnnualLoading] = useState(false);
  const [annualError, setAnnualError] = useState<string | null>(null);

  const [windyLayer, setWindyLayer] = useState<WindyLayer>('wind');
  const [windyFraming, setWindyFraming] = useState<'world' | 'city'>('world');

  const [worldPins, setWorldPins] = useState<LivePointWeather[]>([]);
  const [pinsLoading, setPinsLoading] = useState(false);

  const chartAxis = isDark ? '#94A3B8' : '#475569';
  const gridStroke = isDark ? 'rgba(148, 163, 184, 0.12)' : 'rgba(15, 23, 42, 0.08)';
  const tooltipStyle = {
    backgroundColor: isDark ? '#0E131F' : '#FFFFFF',
    borderColor: isDark ? 'rgba(148, 163, 184, 0.25)' : '#CBD5E1',
    color: isDark ? '#F1F5F9' : '#0F172A',
    borderRadius: '8px',
    fontSize: '0.8rem',
    fontFamily: 'var(--font-mono)',
  };

  useEffect(() => {
    let cancelled = false;
    setPinsLoading(true);
    fetchMultiplePoints(WORLD_DEFAULTS)
      .then((res) => {
        if (!cancelled) setWorldPins(res);
      })
      .catch(() => {
        if (!cancelled) setWorldPins([]);
      })
      .finally(() => {
        if (!cancelled) setPinsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (searchMode !== 'city') return;
    const trimmed = cityQuery.trim();
    if (!trimmed) {
      setMatches([]);
      setSearchError(null);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      setSearchLoading(true);
      setSearchError(null);
      searchCity(trimmed, 10)
        .then((res) => {
          if (!cancelled) {
            setMatches(res);
            setSelectedMatchIdx(0);
          }
        })
        .catch((err) => {
          if (!cancelled) {
            setMatches([]);
            setSearchError(err instanceof Error ? err.message : String(err));
          }
        })
        .finally(() => {
          if (!cancelled) setSearchLoading(false);
        });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [cityQuery, searchMode]);

  const target = useMemo(() => {
    if (searchMode === 'city') {
      const m = matches[selectedMatchIdx];
      if (!m) return null;
      const label = `${m.name} (${m.country_code || ''})`.trim();
      return { lat: Number(m.latitude), lon: Number(m.longitude), label };
    }
    return { lat: coordLat, lon: coordLon, label: coordLabel || 'Ponto personalizado' };
  }, [searchMode, matches, selectedMatchIdx, coordLat, coordLon, coordLabel]);

  useEffect(() => {
    if (!target || toolMode !== 'live') return;
    let cancelled = false;
    setWeatherLoading(true);
    setWeatherError(null);
    fetchCurrentPoint(target.lat, target.lon, target.label)
      .then((res) => {
        if (!cancelled) setWeather(res);
      })
      .catch((err) => {
        if (!cancelled) {
          setWeather(null);
          setWeatherError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setWeatherLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [target?.lat, target?.lon, target?.label, toolMode]);

  useEffect(() => {
    if (!target || toolMode !== 'calendar' || !calDate) return;
    let cancelled = false;
    setHistDayLoading(true);
    setHistDayError(null);
    fetchHistoricalDay(target.lat, target.lon, target.label, calDate)
      .then((res) => {
        if (!cancelled) setHistDay(res);
      })
      .catch((err) => {
        if (!cancelled) {
          setHistDay(null);
          setHistDayError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setHistDayLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [target?.lat, target?.lon, target?.label, toolMode, calDate]);

  useEffect(() => {
    if (!target || toolMode !== 'annual') return;
    let cancelled = false;
    setAnnualLoading(true);
    setAnnualError(null);
    fetchAnnualDataset(target.lat, target.lon, target.label, annualYear)
      .then((res) => {
        if (!cancelled) setAnnualResult(res);
      })
      .catch((err) => {
        if (!cancelled) {
          setAnnualResult(null);
          setAnnualError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setAnnualLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [target?.lat, target?.lon, target?.label, toolMode, annualYear]);

  const anomaly = useMemo(
    () => calculateClimateAnomaly(activeRecords, weather),
    [activeRecords, weather]
  );

  const annualStats = useMemo(() => {
    if (!annualResult) return null;
    const rows = annualResult.dataset.data;
    let maxT = -Infinity;
    let minT = Infinity;
    let sumT = 0;
    let countT = 0;
    let totalRain = 0;
    const rainByDay = new Map<string, number>();
    const monthAgg = new Map<number, { rain: number; tempSum: number; tempCount: number }>();

    for (const r of rows) {
      if (r.temp_max_c !== null) {
        if (r.temp_max_c > maxT) maxT = r.temp_max_c;
        sumT += r.temp_max_c;
        countT++;
      }
      if (r.temp_min_c !== null && r.temp_min_c < minT) minT = r.temp_min_c;
      const rain = r.precipitacao_mm ?? 0;
      totalRain += rain;
      rainByDay.set(r.dia, (rainByDay.get(r.dia) ?? 0) + rain);

      const m = monthAgg.get(r.mes) || { rain: 0, tempSum: 0, tempCount: 0 };
      m.rain += rain;
      if (r.temp_max_c !== null) {
        m.tempSum += r.temp_max_c;
        m.tempCount++;
      }
      monthAgg.set(r.mes, m);
    }

    let rainDays = 0;
    rainByDay.forEach((v) => {
      if (v > 0.2) rainDays++;
    });

    const monthlyChart = Array.from(monthAgg.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([mes, agg]) => ({
        mes_nome: MESES_PT[mes] || String(mes),
        chuva_total: Math.round(agg.rain * 10) / 10,
        temp_media: agg.tempCount > 0 ? Math.round((agg.tempSum / agg.tempCount) * 10) / 10 : null,
      }));

    return {
      count: rows.length,
      tMax: Number.isFinite(maxT) ? maxT : null,
      tMin: Number.isFinite(minT) ? minT : null,
      tMed: countT > 0 ? sumT / countT : null,
      rainTotal: totalRain,
      rainDays,
      monthlyChart,
    };
  }, [annualResult]);

  const handleLoad30Days = async () => {
    if (!target) return;
    setLoading30d(true);
    try {
      const bundle = await fetchLiveWeather(target.lat, target.lon, target.label, 30, 7);
      onLoadDatasetIntoSession(
        bundle.dataset,
        `Histórico recente (30 dias) carregado para ${target.label}.`
      );
    } catch (err) {
      setWeatherError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading30d(false);
    }
  };

  const handlePinCurrent = () => {
    if (!weather) return;
    setWorldPins((prev) => [...prev.filter((p) => p.local !== weather.local), weather]);
  };

  const handleResetDefaults = async () => {
    setPinsLoading(true);
    try {
      const res = await fetchMultiplePoints(WORLD_DEFAULTS);
      setWorldPins(res);
    } finally {
      setPinsLoading(false);
    }
  };

  const tablePoints = worldPins.length > 0 ? worldPins : weather ? [weather] : [];

  const podium = useMemo(() => {
    if (tablePoints.length < 2) return null;
    const validTemp = tablePoints.filter((p) => p.temperatura_c !== null);
    const validWind = tablePoints.filter((p) => p.vento_kmh !== null);
    if (validTemp.length === 0 || validWind.length === 0) return null;
    const hottest = validTemp.reduce((a, b) => ((b.temperatura_c ?? -999) > (a.temperatura_c ?? -999) ? b : a));
    const coldest = validTemp.reduce((a, b) => ((b.temperatura_c ?? 999) < (a.temperatura_c ?? 999) ? b : a));
    const windiest = validWind.reduce((a, b) => ((b.vento_kmh ?? -1) > (a.vento_kmh ?? -1) ? b : a));
    return { hottest, coldest, windiest };
  }, [tablePoints]);

  const windyZoom = windyFraming === 'world' || !target ? 3 : 6;
  const windyLat = windyFraming === 'world' || !target ? 15.0 : target.lat;
  const windyLon = windyFraming === 'world' || !target ? -20.0 : target.lon;
  const windyUrl =
    `https://embed.windy.com/embed.html?type=map&location=coordinates&metricRain=mm&metricTemp=%C2%B0C&metricWind=km/h` +
    `&zoom=${windyZoom}&overlay=${windyLayer}&product=ecmwf&level=surface&lat=${windyLat}&lon=${windyLon}&message=true`;

  const yearOptions = useMemo(() => {
    const arr: number[] = [];
    for (let y = currentYear; y >= 1940; y--) arr.push(y);
    return arr;
  }, [currentYear]);

  return (
    <div className="space-y-8">
      {/* LOCATION QUERY BAR */}
      <section className="surface-panel p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="m-0 text-[1.25rem] font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Consulta Meteorológica Global
            </h1>
            <p className="mt-0.5 mb-0 text-[0.84rem]" style={{ color: 'var(--text-muted)' }}>
              Telemetria em tempo real, previsão estendida e reanálise histórica ERA5 para qualquer coordenada.
            </p>
          </div>

          <div className="segmented-track" role="tablist" aria-label="Modo de busca">
            <button
              type="button"
              onClick={() => setSearchMode('city')}
              className={`segmented-item ${searchMode === 'city' ? 'segmented-item-active' : ''}`}
            >
              <Search size={13} />
              <span>Cidade ou região</span>
            </button>
            <button
              type="button"
              onClick={() => setSearchMode('coords')}
              className={`segmented-item ${searchMode === 'coords' ? 'segmented-item-active' : ''}`}
            >
              <Compass size={13} />
              <span>Coordenadas</span>
            </button>
          </div>
        </div>

        {searchMode === 'city' ? (
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3.5 items-end">
            <div className="md:col-span-5">
              <label className="block text-[0.78rem] font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>
                Buscar localidade
              </label>
              <div className="relative">
                <Search
                  size={15}
                  className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                  style={{ color: 'var(--text-muted)' }}
                />
                <input
                  type="text"
                  value={cityQuery}
                  onChange={(e) => setCityQuery(e.target.value)}
                  placeholder="Manaus, São Paulo, Tóquio..."
                  className="field-input pl-9"
                />
              </div>
            </div>
            <div className="md:col-span-7">
              <label className="block text-[0.78rem] font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>
                Estação ou município correspondente {searchLoading ? '· pesquisando...' : ''}
              </label>
              {searchError ? (
                <div className="text-[0.82rem] py-2" style={{ color: 'var(--danger)' }}>
                  Erro ao pesquisar local: {searchError}
                </div>
              ) : matches.length > 0 ? (
                <select
                  value={selectedMatchIdx}
                  onChange={(e) => setSelectedMatchIdx(Number(e.target.value))}
                  className="field-input"
                >
                  {matches.map((r, i) => {
                    const region = [r.admin1, r.country].filter(Boolean).join(', ');
                    return (
                      <option key={`${r.name}-${r.latitude}-${r.longitude}-${i}`} value={i}>
                        {r.name} — {region} ({Number(r.latitude).toFixed(2)}, {Number(r.longitude).toFixed(2)})
                      </option>
                    );
                  })}
                </select>
              ) : (
                <div
                  className="field-input text-[0.84rem]"
                  style={{ color: 'var(--text-muted)', backgroundColor: 'var(--bg-subtle)' }}
                >
                  {searchLoading ? 'Buscando correspondências...' : 'Nenhum local encontrado para este termo.'}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
            <div>
              <label className="block text-[0.78rem] font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>
                Latitude (-90 a 90)
              </label>
              <input
                type="number"
                min={-90}
                max={90}
                step={0.01}
                value={coordLat}
                onChange={(e) => setCoordLat(Number(e.target.value))}
                className="field-input font-mono-tabular"
              />
            </div>
            <div>
              <label className="block text-[0.78rem] font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>
                Longitude (-180 a 180)
              </label>
              <input
                type="number"
                min={-180}
                max={180}
                step={0.01}
                value={coordLon}
                onChange={(e) => setCoordLon(Number(e.target.value))}
                className="field-input font-mono-tabular"
              />
            </div>
            <div>
              <label className="block text-[0.78rem] font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>
                Rótulo do ponto
              </label>
              <input
                type="text"
                value={coordLabel}
                onChange={(e) => setCoordLabel(e.target.value)}
                className="field-input"
              />
            </div>
          </div>
        )}

        {/* Tool mode switcher */}
        {target && (
          <div
            className="pt-4 flex flex-wrap items-center justify-between gap-3"
            style={{ borderTop: '1px solid var(--border-hairline)' }}
          >
            <div className="segmented-track" role="tablist" aria-label="Modo de análise do ponto">
              <button
                type="button"
                onClick={() => setToolMode('live')}
                className={`segmented-item ${toolMode === 'live' ? 'segmented-item-active' : ''}`}
              >
                <Activity size={13} />
                <span>Tempo Real e Previsão</span>
              </button>
              <button
                type="button"
                onClick={() => setToolMode('calendar')}
                className={`segmented-item ${toolMode === 'calendar' ? 'segmented-item-active' : ''}`}
              >
                <Calendar size={13} />
                <span>Calendário Histórico</span>
              </button>
              <button
                type="button"
                onClick={() => setToolMode('annual')}
                className={`segmented-item ${toolMode === 'annual' ? 'segmented-item-active' : ''}`}
              >
                <Database size={13} />
                <span>Série Anual (8.760h)</span>
              </button>
            </div>

            <div className="flex items-center gap-2 text-[0.78rem] font-mono-tabular" style={{ color: 'var(--text-muted)' }}>
              <MapPin size={13} />
              <span>
                {target.lat.toFixed(2)}°, {target.lon.toFixed(2)}°
              </span>
            </div>
          </div>
        )}
      </section>

      {/* ACTIVE TOOL CONTENT */}
      {target && toolMode === 'live' && (
        <section className="space-y-6">
          {weatherLoading && (
            <div className="space-y-4">
              <div className="surface-panel p-6 h-[156px] flex flex-col justify-between">
                <div className="skeleton-block h-6 w-52" />
                <div className="skeleton-block h-10 w-36" />
                <div className="skeleton-block h-4 w-72" />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3.5">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="surface-panel p-4 h-[96px] space-y-3">
                    <div className="skeleton-block h-3 w-20" />
                    <div className="skeleton-block h-6 w-24" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {weatherError && (
            <div
              className="surface-panel p-4 text-[0.86rem]"
              style={{ borderColor: 'rgba(239, 68, 68, 0.35)', color: 'var(--danger)' }}
            >
              Não foi possível obter a telemetria ao vivo: {weatherError}
            </div>
          )}

          {weather && !weatherLoading && (
            <>
              {/* Hero Telemetry Console */}
              <div className="surface-panel p-6">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                  <div className="space-y-2.5">
                    <div
                      className="flex flex-wrap items-center gap-2 text-[0.78rem]"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      <span>{weather.periodo}</span>
                      <span aria-hidden="true">·</span>
                      <span className="font-mono-tabular">{weather.fuso}</span>
                      <span aria-hidden="true">·</span>
                      <span className="font-mono-tabular">
                        Atualizado {formatDatetimeFriendly(weather.horario)}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-baseline gap-3">
                      <h2 className="m-0 text-[1.8rem] font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
                        {weather.local}
                      </h2>
                      <span
                        className="inline-flex items-center gap-1.5 text-[0.92rem] font-medium"
                        style={{ color: 'var(--text-secondary)' }}
                      >
                        <WeatherConditionIcon condition={weather.condicao} size={17} />
                        {cleanConditionText(weather.condicao)}
                      </span>
                    </div>

                    <div
                      className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[0.82rem] font-mono-tabular"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      <span>Nuvens {brNumber(weather.nuvens_pct, 0)}%</span>
                      <span aria-hidden="true">·</span>
                      <span>Rajadas {brNumber(weather.rajadas_kmh)} km/h</span>
                      <span aria-hidden="true">·</span>
                      <span>UV máx. {brNumber(weather.uv_max)}</span>
                      <span aria-hidden="true">·</span>
                      <span>
                        Sol {weather.nascer_sol} – {weather.por_sol}
                      </span>
                    </div>
                  </div>

                  {/* Calibrated Large Readout + Quick Actions */}
                  <div className="flex flex-col sm:flex-row lg:flex-col sm:items-end justify-between gap-4">
                    <div className="sm:text-right">
                      <div className="flex items-baseline sm:justify-end gap-1.5">
                        <span
                          className="font-mono-tabular text-[3rem] font-semibold tracking-tight leading-none"
                          style={{ color: 'var(--text-primary)' }}
                        >
                          {brNumber(weather.temperatura_c)}
                        </span>
                        <span
                          className="font-mono-tabular text-[1.2rem] font-medium"
                          style={{ color: 'var(--accent-text)' }}
                        >
                          °C
                        </span>
                      </div>
                      <div className="mt-1.5 text-[0.84rem]" style={{ color: 'var(--text-muted)' }}>
                        Sensação térmica{' '}
                        <span className="font-mono-tabular font-semibold" style={{ color: 'var(--text-primary)' }}>
                          {brNumber(weather.sensacao_c)} °C
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <button type="button" onClick={handlePinCurrent} className="btn-secondary text-[0.8rem] py-1.5 px-3">
                        <Pin size={13} />
                        <span>Fixar na tabela</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleLoad30Days()}
                        disabled={loading30d}
                        className="btn-primary text-[0.8rem] py-1.5 px-3"
                      >
                        {loading30d ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
                        <span>{loading30d ? 'Carregando...' : 'Analisar últimos 30 dias'}</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Integrated Barometric Risk Footer inside Hero */}
                {weather.risco_tempestade && (
                  <div
                    className="mt-5 pt-4 flex items-start sm:items-center gap-3 text-[0.84rem]"
                    style={{ borderTop: '1px solid var(--border-hairline)' }}
                  >
                    {weather.risco_tempestade.classe === 'storm-high' ? (
                      <ShieldAlert size={17} className="shrink-0 mt-0.5 sm:mt-0" style={{ color: 'var(--danger)' }} />
                    ) : weather.risco_tempestade.classe === 'storm-med' ? (
                      <AlertTriangle size={17} className="shrink-0 mt-0.5 sm:mt-0" style={{ color: 'var(--warning)' }} />
                    ) : (
                      <CheckCircle2 size={17} className="shrink-0 mt-0.5 sm:mt-0" style={{ color: 'var(--nominal)' }} />
                    )}
                    <div className="min-w-0">
                      <span
                        className="font-semibold mr-2"
                        style={{
                          color:
                            weather.risco_tempestade.classe === 'storm-high'
                              ? 'var(--danger)'
                              : weather.risco_tempestade.classe === 'storm-med'
                              ? 'var(--warning)'
                              : 'var(--nominal)',
                        }}
                      >
                        {weather.risco_tempestade.nivel}
                      </span>
                      <span style={{ color: 'var(--text-secondary)' }}>
                        {weather.risco_tempestade.detalhe}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* 6 Calibrated Telemetry Readouts */}
              <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3.5">
                <MetricCard label="Temperatura" value={brNumber(weather.temperatura_c)} unit="°C" />
                <MetricCard label="Sensação térmica" value={brNumber(weather.sensacao_c)} unit="°C" />
                <MetricCard label="Umidade relativa" value={brNumber(weather.umidade_pct, 0)} unit="%" />
                <MetricCard label="Velocidade do vento" value={brNumber(weather.vento_kmh)} unit="km/h" />
                <MetricCard label="Pressão atmosférica" value={brNumber(weather.pressao_hpa, 0)} unit="hPa" />
                <MetricCard label="Precipitação atual" value={brNumber(weather.precipitacao_mm)} unit="mm" />
              </div>

              {/* Bioclimatic Indices Strip */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
                <MetricCard
                  label="Índice de Calor (Heat Index)"
                  value={weather.indice_calor_c !== null ? brNumber(weather.indice_calor_c) : '-'}
                  unit={weather.indice_calor_c !== null ? '°C' : undefined}
                  subtext={weather.indice_calor_desc}
                  tone={
                    weather.indice_calor_c !== null && weather.indice_calor_c >= 41
                      ? 'negative'
                      : weather.indice_calor_c !== null && weather.indice_calor_c >= 32
                      ? 'warning'
                      : 'neutral'
                  }
                  help="Temperatura aparente calculada pela equação NOAA/Steadman combinando temperatura do ar e umidade relativa."
                />
                <MetricCard
                  label="Ponto de Orvalho (Dew Point)"
                  value={weather.ponto_orvalho_c !== null ? brNumber(weather.ponto_orvalho_c) : '-'}
                  unit={weather.ponto_orvalho_c !== null ? '°C' : undefined}
                  subtext={
                    weather.ponto_orvalho_c !== null && weather.ponto_orvalho_c >= 21
                      ? 'Ar abafado / tropical'
                      : weather.ponto_orvalho_c !== null && weather.ponto_orvalho_c >= 10
                      ? 'Faixa confortável'
                      : 'Ar seco'
                  }
                  help="Temperatura de condensação (Magnus-Tetens). Acima de 20 °C indica forte desconforto por umidade."
                />
                <MetricCard
                  label="Radiação UV Máxima"
                  value={weather.uv_max !== null ? brNumber(weather.uv_max) : '-'}
                  unit={weather.uv_max !== null ? 'UV' : undefined}
                  subtext={weather.uv_info?.status || 'Sem leitura'}
                  tone={
                    weather.uv_max !== null && weather.uv_max >= 8
                      ? 'negative'
                      : weather.uv_max !== null && weather.uv_max >= 6
                      ? 'warning'
                      : 'neutral'
                  }
                  help="Índice ultravioleta diário máximo conforme classificação da Organização Mundial da Saúde."
                />
              </div>

              {/* Historical Climate Anomaly Comparison */}
              {anomaly ? (
                <div className="surface-panel p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2.5 text-[0.8rem]" style={{ color: 'var(--text-muted)' }}>
                      <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                        Anomalia Climática Histórica ({anomaly.mes_nome})
                      </span>
                      <span aria-hidden="true">·</span>
                      <span
                        className="font-mono-tabular font-semibold"
                        style={{
                          color:
                            anomaly.delta_temp > 0.5
                              ? 'var(--danger)'
                              : anomaly.delta_temp < -0.5
                              ? 'var(--accent-text)'
                              : 'var(--nominal)',
                        }}
                      >
                        {anomaly.delta_temp >= 0 ? '+' : ''}
                        {anomaly.delta_temp.toFixed(1)} °C vs. série histórica
                      </span>
                    </div>
                    <p className="m-0 text-[0.86rem]" style={{ color: 'var(--text-secondary)' }}>
                      {anomaly.summary_text}
                    </p>
                  </div>
                  <div className="flex items-center gap-6 shrink-0 font-mono-tabular text-[0.82rem]">
                    <div>
                      <div style={{ color: 'var(--text-muted)' }}>Chuva hoje</div>
                      <div className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                        {brNumber(anomaly.curr_rain)} mm
                      </div>
                    </div>
                    <div>
                      <div style={{ color: 'var(--text-muted)' }}>Média diária ({anomaly.mes_nome})</div>
                      <div className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                        {brNumber(anomaly.hist_rain_daily_avg)} mm
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="surface-subtle px-4 py-3 text-[0.82rem]" style={{ color: 'var(--text-muted)' }}>
                  Carregue uma base CSV do INMET ou clique em <strong style={{ color: 'var(--text-primary)' }}>Analisar últimos 30 dias</strong> para comparar a temperatura e precipitação atuais com a média histórica mensal.
                </div>
              )}

              {/* Air Quality & Wildfire Smoke Panel */}
              {weather.air_quality && (
                <div className="surface-panel overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setAqiOpen((v) => !v)}
                    className="w-full px-5 py-3.5 flex items-center justify-between text-left bg-transparent border-0 cursor-pointer"
                    style={{
                      borderBottom: aqiOpen ? '1px solid var(--border-hairline)' : 'none',
                    }}
                  >
                    <div className="flex flex-wrap items-center gap-2.5">
                      <span className="font-display font-semibold text-[0.94rem]" style={{ color: 'var(--text-primary)' }}>
                        Qualidade do Ar e Monitoramento de Fumaça
                      </span>
                      <span className="text-[0.8rem]" style={{ color: 'var(--text-muted)' }}>
                        · Status:{' '}
                        <strong style={{ color: weather.air_quality.info.cor }}>
                          {weather.air_quality.info.status}
                        </strong>
                      </span>
                    </div>
                    <span style={{ color: 'var(--text-muted)' }}>
                      {aqiOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </span>
                  </button>

                  {aqiOpen && (
                    <div className="p-5 space-y-4">
                      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
                        <div className="surface-subtle px-4 py-3">
                          <div className="text-[0.76rem]" style={{ color: 'var(--text-muted)' }}>
                            Índice US AQI
                          </div>
                          <div className="mt-1 font-mono-tabular text-[1.35rem] font-semibold">
                            {weather.air_quality.us_aqi !== null ? weather.air_quality.us_aqi : '-'}
                          </div>
                          <div className="text-[0.75rem] mt-0.5" style={{ color: weather.air_quality.info.cor }}>
                            {weather.air_quality.info.status}
                          </div>
                        </div>
                        <div className="surface-subtle px-4 py-3">
                          <div className="text-[0.76rem]" style={{ color: 'var(--text-muted)' }}>
                            PM2.5 (Fumaça fina)
                          </div>
                          <div className="mt-1 flex items-baseline gap-1 font-mono-tabular">
                            <span className="text-[1.35rem] font-semibold">
                              {weather.air_quality.pm2_5 !== null ? brNumber(weather.air_quality.pm2_5) : '-'}
                            </span>
                            <span className="text-[0.75rem]" style={{ color: 'var(--text-muted)' }}>
                              µg/m³
                            </span>
                          </div>
                          <div className="text-[0.75rem] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                            Queimadas e fuligem
                          </div>
                        </div>
                        <div className="surface-subtle px-4 py-3">
                          <div className="text-[0.76rem]" style={{ color: 'var(--text-muted)' }}>
                            PM10 (Material particulado)
                          </div>
                          <div className="mt-1 flex items-baseline gap-1 font-mono-tabular">
                            <span className="text-[1.35rem] font-semibold">
                              {weather.air_quality.pm10 !== null ? brNumber(weather.air_quality.pm10) : '-'}
                            </span>
                            <span className="text-[0.75rem]" style={{ color: 'var(--text-muted)' }}>
                              µg/m³
                            </span>
                          </div>
                          <div className="text-[0.75rem] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                            Poeira e aerossóis
                          </div>
                        </div>
                        <div className="surface-subtle px-4 py-3">
                          <div className="text-[0.76rem]" style={{ color: 'var(--text-muted)' }}>
                            Monóxido de Carbono (CO)
                          </div>
                          <div className="mt-1 flex items-baseline gap-1 font-mono-tabular">
                            <span className="text-[1.35rem] font-semibold">
                              {weather.air_quality.co !== null ? brNumber(weather.air_quality.co, 0) : '-'}
                            </span>
                            <span className="text-[0.75rem]" style={{ color: 'var(--text-muted)' }}>
                              µg/m³
                            </span>
                          </div>
                          <div className="text-[0.75rem] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                            Gases de combustão
                          </div>
                        </div>
                      </div>
                      <p className="m-0 text-[0.83rem]" style={{ color: 'var(--text-secondary)' }}>
                        <strong style={{ color: 'var(--text-primary)' }}>Recomendação de saúde:</strong>{' '}
                        {weather.air_quality.info.recomendacao}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Interactive Forecast Chart */}
              {(weather.forecast_hourly.length > 0 || weather.forecast_daily.length > 0) && (
                <div className="surface-panel p-5 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="m-0 text-[1rem] font-semibold" style={{ color: 'var(--text-primary)' }}>
                        Previsão Meteorológica
                      </h3>
                      <p className="mt-0.5 mb-0 text-[0.8rem]" style={{ color: 'var(--text-muted)' }}>
                        Evolução térmica e probabilidade ou volume de precipitação prevista.
                      </p>
                    </div>
                    <div className="segmented-track" role="tablist" aria-label="Horizonte de previsão">
                      {[
                        { id: '24h' as const, label: '24 horas' },
                        { id: '7d' as const, label: '7 dias' },
                        { id: '14d' as const, label: '14 dias' },
                      ].map((opt) => (
                        <button
                          key={opt.id}
                          type="button"
                          onClick={() => setForecastScope(opt.id)}
                          className={`segmented-item ${forecastScope === opt.id ? 'segmented-item-active' : ''}`}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="w-full h-[340px]">
                    {forecastScope === '24h' ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={weather.forecast_hourly.slice(0, 24)} margin={{ top: 10, right: 16, left: 0, bottom: 4 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                          <XAxis dataKey="hora_label" tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
                          <YAxis
                            yAxisId="left"
                            tick={{ fill: isDark ? '#F59E0B' : '#D97706', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                            axisLine={false}
                            tickLine={false}
                            unit="°"
                          />
                          <YAxis
                            yAxisId="right"
                            orientation="right"
                            domain={[0, 100]}
                            tick={{ fill: isDark ? '#38BDF8' : '#0284C7', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                            axisLine={false}
                            tickLine={false}
                            unit="%"
                          />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                          <Bar
                            yAxisId="right"
                            dataKey="prob_chuva_pct"
                            name="Prob. de chuva (%)"
                            fill={isDark ? 'rgba(14, 165, 233, 0.35)' : 'rgba(2, 132, 199, 0.28)'}
                            radius={[3, 3, 0, 0]}
                          />
                          <Line
                            yAxisId="left"
                            type="monotone"
                            dataKey="temperatura_c"
                            name="Temperatura (°C)"
                            stroke="#F59E0B"
                            strokeWidth={2.4}
                            dot={{ r: 3, strokeWidth: 0, fill: '#F59E0B' }}
                            activeDot={{ r: 5 }}
                          />
                        </ComposedChart>
                      </ResponsiveContainer>
                    ) : (
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart
                          data={weather.forecast_daily.slice(0, forecastScope === '7d' ? 7 : 14)}
                          margin={{ top: 10, right: 16, left: 0, bottom: 4 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                          <XAxis dataKey="data_label" tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
                          <YAxis
                            yAxisId="left"
                            tick={{ fill: isDark ? '#F59E0B' : '#D97706', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                            axisLine={false}
                            tickLine={false}
                            unit="°"
                          />
                          <YAxis
                            yAxisId="right"
                            orientation="right"
                            tick={{ fill: isDark ? '#38BDF8' : '#0284C7', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                            axisLine={false}
                            tickLine={false}
                            unit="mm"
                          />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                          <Bar
                            yAxisId="right"
                            dataKey="chuva_mm"
                            name="Chuva prevista (mm)"
                            fill={isDark ? 'rgba(14, 165, 233, 0.38)' : 'rgba(2, 132, 199, 0.3)'}
                            radius={[3, 3, 0, 0]}
                          />
                          <Area
                            yAxisId="left"
                            type="monotone"
                            dataKey="temp_max_c"
                            name="Máxima (°C)"
                            stroke="#F59E0B"
                            fill="rgba(245, 158, 11, 0.1)"
                            strokeWidth={2.4}
                          />
                          <Line
                            yAxisId="left"
                            type="monotone"
                            dataKey="temp_min_c"
                            name="Mínima (°C)"
                            stroke={isDark ? '#38BDF8' : '#0284C7'}
                            strokeWidth={2.2}
                            dot={{ r: 3, strokeWidth: 0, fill: isDark ? '#38BDF8' : '#0284C7' }}
                          />
                        </ComposedChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </section>
      )}

      {/* TOOL 2: HISTORICAL CALENDAR DAY */}
      {target && toolMode === 'calendar' && (
        <section className="space-y-6">
          <div className="surface-panel p-5 grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
            <div className="md:col-span-4">
              <label className="block text-[0.78rem] font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>
                Data da reanálise (desde 1940)
              </label>
              <input
                type="date"
                value={calDate}
                min="1940-01-01"
                max={getMaxCalendarIso()}
                onChange={(e) => setCalDate(e.target.value)}
                className="field-input font-mono-tabular"
              />
            </div>
            <div className="md:col-span-8 text-[0.85rem]" style={{ color: 'var(--text-secondary)' }}>
              Consulte a telemetria horária reconstituída para <strong style={{ color: 'var(--text-primary)' }}>{target.label}</strong> em qualquer data histórica via Open-Meteo / ECMWF ERA5.
            </div>
          </div>

          {histDayLoading && (
            <div className="surface-panel p-6 flex items-center gap-3 text-[0.86rem]" style={{ color: 'var(--text-muted)' }}>
              <Loader2 size={17} className="animate-spin" style={{ color: 'var(--accent)' }} />
              Consultando série horária de {calDate} para {target.label}...
            </div>
          )}
          {histDayError && (
            <div className="surface-panel p-4 text-[0.85rem]" style={{ color: 'var(--danger)' }}>
              Erro ao consultar histórico: {histDayError}
            </div>
          )}

          {histDay && !histDayLoading && (
            <>
              <div className="surface-panel p-6 flex flex-wrap justify-between items-center gap-6">
                <div className="space-y-1.5">
                  <div className="text-[0.8rem]" style={{ color: 'var(--text-muted)' }}>
                    {histDay.dia_semana} · <span className="font-mono-tabular">{histDay.data_formatada}</span> ·{' '}
                    <span className="font-mono-tabular">{histDay.fuso}</span>
                  </div>
                  <h2 className="m-0 text-[1.6rem] font-bold tracking-tight">{histDay.local}</h2>
                  <div className="flex flex-wrap items-center gap-3 text-[0.84rem]" style={{ color: 'var(--text-secondary)' }}>
                    <span className="inline-flex items-center gap-1.5">
                      <WeatherConditionIcon condition={histDay.condicao} size={16} />
                      {cleanConditionText(histDay.condicao)}
                    </span>
                    <span aria-hidden="true">·</span>
                    <span className="font-mono-tabular">
                      Sol {histDay.nascer_sol} – {histDay.por_sol}
                    </span>
                    <span aria-hidden="true">·</span>
                    <span className="font-mono-tabular">
                      Pressão média {brNumber(histDay.pressao_media_hpa, 0)} hPa
                    </span>
                  </div>
                </div>
                <div className="sm:text-right">
                  <div className="font-mono-tabular text-[2.2rem] font-semibold leading-none">
                    <span style={{ color: 'var(--thermal-high)' }}>{brNumber(histDay.temp_max_c)}°</span>
                    <span className="mx-1.5 text-[1.2rem]" style={{ color: 'var(--text-muted)' }}>
                      /
                    </span>
                    <span style={{ color: 'var(--thermal-low)' }}>{brNumber(histDay.temp_min_c)}°C</span>
                  </div>
                  <div className="mt-1.5 text-[0.82rem] font-mono-tabular" style={{ color: 'var(--text-muted)' }}>
                    Média {brNumber(histDay.temp_media_c)} °C · Amplitude {brNumber(histDay.amplitude_termica_c)} °C
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3.5">
                <MetricCard label="Máxima do dia" value={brNumber(histDay.temp_max_c)} unit="°C" />
                <MetricCard label="Mínima do dia" value={brNumber(histDay.temp_min_c)} unit="°C" />
                <MetricCard label="Temperatura média" value={brNumber(histDay.temp_media_c)} unit="°C" />
                <MetricCard label="Chuva acumulada" value={brNumber(histDay.precipitacao_total_mm)} unit="mm" />
                <MetricCard label="Vento máximo" value={brNumber(histDay.vento_max_kmh)} unit="km/h" />
                <MetricCard label="Umidade média" value={brNumber(histDay.umidade_media_pct, 0)} unit="%" />
              </div>

              {histDay.hourly.length > 0 && (
                <>
                  <div className="surface-panel p-5 space-y-3">
                    <h3 className="m-0 text-[1rem] font-semibold">Perfil Horário do Dia</h3>
                    <div className="w-full h-[330px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={histDay.hourly} margin={{ top: 10, right: 16, left: 0, bottom: 4 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                          <XAxis dataKey="hora_label" tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
                          <YAxis yAxisId="left" tick={{ fill: isDark ? '#F59E0B' : '#D97706', fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} unit="°" />
                          <YAxis yAxisId="right" orientation="right" tick={{ fill: isDark ? '#38BDF8' : '#0284C7', fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} unit="mm" />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                          <Bar yAxisId="right" dataKey="chuva_mm" name="Precipitação (mm)" fill={isDark ? 'rgba(14, 165, 233, 0.38)' : 'rgba(2, 132, 199, 0.32)'} radius={[3, 3, 0, 0]} />
                          <Line yAxisId="left" type="monotone" dataKey="temperatura_c" name="Temperatura (°C)" stroke="#F59E0B" strokeWidth={2.5} dot={{ r: 3, strokeWidth: 0, fill: '#F59E0B' }} />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="surface-panel overflow-hidden">
                    <button
                      type="button"
                      onClick={() => setHistTableOpen((v) => !v)}
                      className="w-full px-5 py-3.5 flex items-center justify-between text-left bg-transparent border-0 cursor-pointer"
                      style={{ borderBottom: histTableOpen ? '1px solid var(--border-hairline)' : 'none' }}
                    >
                      <span className="font-display font-semibold text-[0.92rem]" style={{ color: 'var(--text-primary)' }}>
                        Telemetria horária detalhada ({histDay.hourly.length} medições)
                      </span>
                      <span style={{ color: 'var(--text-muted)' }}>
                        {histTableOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </span>
                    </button>
                    {histTableOpen && (
                      <div className="p-4">
                        <div className="data-grid-wrap max-h-[380px]">
                          <table className="data-grid">
                            <thead>
                              <tr>
                                <th>Hora</th>
                                <th>Condição</th>
                                <th className="num">Temp. (°C)</th>
                                <th className="num">Chuva (mm)</th>
                                <th className="num">Umidade (%)</th>
                                <th className="num">Vento (km/h)</th>
                              </tr>
                            </thead>
                            <tbody>
                              {histDay.hourly.map((row) => (
                                <tr key={row.data_hora_raw}>
                                  <td className="font-mono-tabular">{row.hora_label}</td>
                                  <td>{cleanConditionText(row.condicao)}</td>
                                  <td className="num">{brNumber(row.temperatura_c)}</td>
                                  <td className="num">{brNumber(row.chuva_mm)}</td>
                                  <td className="num">{brNumber(row.umidade_pct, 0)}</td>
                                  <td className="num">{brNumber(row.vento_kmh)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}
            </>
          )}
        </section>
      )}

      {/* TOOL 3: ANNUAL DATASET (8,760h) */}
      {target && toolMode === 'annual' && (
        <section className="space-y-6">
          <div className="surface-panel p-5 grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
            <div className="md:col-span-4">
              <label className="block text-[0.78rem] font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>
                Ano de referência (ERA5)
              </label>
              <select
                value={annualYear}
                onChange={(e) => setAnnualYear(Number(e.target.value))}
                className="field-input font-mono-tabular"
              >
                {yearOptions.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
            <div className="md:col-span-8 text-[0.85rem]" style={{ color: 'var(--text-secondary)' }}>
              Gere uma série horária anual completa para <strong style={{ color: 'var(--text-primary)' }}>{target.label}</strong> no formato compatível com o INMET e carregue diretamente nas abas de análise histórica.
            </div>
          </div>

          {annualLoading && (
            <div className="surface-panel p-6 flex items-center gap-3 text-[0.86rem]" style={{ color: 'var(--text-muted)' }}>
              <Loader2 size={17} className="animate-spin" style={{ color: 'var(--accent)' }} />
              Gerando série anual de {annualYear} para {target.label}...
            </div>
          )}
          {annualError && (
            <div className="surface-panel p-4 text-[0.85rem]" style={{ color: 'var(--danger)' }}>
              Erro ao buscar histórico anual: {annualError}
            </div>
          )}

          {annualResult && annualStats && !annualLoading && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
                <MetricCard label="Máxima absoluta" value={brNumber(annualStats.tMax)} unit="°C" />
                <MetricCard label="Mínima absoluta" value={brNumber(annualStats.tMin)} unit="°C" />
                <MetricCard label="Temperatura média anual" value={brNumber(annualStats.tMed)} unit="°C" />
                <MetricCard
                  label="Chuva acumulada anual"
                  value={brNumber(annualStats.rainTotal)}
                  unit="mm"
                  subtext={`${annualStats.rainDays} dias chuvosos · ${brNumber(annualStats.count, 0)} horas`}
                />
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() =>
                    onLoadDatasetIntoSession(
                      annualResult.dataset,
                      `Ano ${annualYear} de ${target.label} carregado nas abas de análise.`,
                      annualResult.csvText
                    )
                  }
                  className="btn-primary"
                >
                  <Database size={15} />
                  <span>Carregar {annualYear} nas abas analíticas</span>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    downloadTextFile(annualResult.csvText, annualResult.csvFilename, 'text/csv;charset=utf-8;')
                  }
                  className="btn-secondary"
                >
                  <Download size={15} />
                  <span>Baixar CSV ({brNumber(annualStats.count, 0)} horas)</span>
                </button>
              </div>

              <div className="surface-panel p-5 space-y-3">
                <h3 className="m-0 text-[1rem] font-semibold">Perfil Climático Mensal ({annualYear})</h3>
                <div className="w-full h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={annualStats.monthlyChart} margin={{ top: 10, right: 16, left: 0, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                      <XAxis dataKey="mes_nome" tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
                      <YAxis yAxisId="left" tick={{ fill: isDark ? '#F59E0B' : '#D97706', fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} unit="°" />
                      <YAxis yAxisId="right" orientation="right" tick={{ fill: isDark ? '#38BDF8' : '#0284C7', fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} unit="mm" />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                      <Bar yAxisId="right" dataKey="chuva_total" name="Chuva mensal (mm)" fill={isDark ? 'rgba(14, 165, 233, 0.38)' : 'rgba(2, 132, 199, 0.32)'} radius={[3, 3, 0, 0]} />
                      <Line yAxisId="left" type="monotone" dataKey="temp_media" name="Temp. média (°C)" stroke="#F59E0B" strokeWidth={2.5} dot={{ r: 3.5, strokeWidth: 0, fill: '#F59E0B' }} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          )}
        </section>
      )}

      {/* WINDY GLOBAL RADAR */}
      <section className="surface-panel overflow-hidden">
        <div
          className="px-5 py-4 flex flex-wrap items-center justify-between gap-4"
          style={{ borderBottom: '1px solid var(--border-hairline)' }}
        >
          <div>
            <h3 className="m-0 text-[1rem] font-semibold">Radar Meteorológico Global (Windy / ECMWF)</h3>
            <p className="mt-0.5 mb-0 text-[0.8rem]" style={{ color: 'var(--text-muted)' }}>
              Visualização interativa de ventos, temperatura, precipitação, nebulosidade e pressão em superfície.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <select
              value={windyLayer}
              onChange={(e) => setWindyLayer(e.target.value as WindyLayer)}
              className="field-input w-auto py-1.5 text-[0.82rem]"
              aria-label="Camada meteorológica"
            >
              <option value="wind">Camada: Ventos</option>
              <option value="temp">Camada: Temperatura</option>
              <option value="rain">Camada: Chuva</option>
              <option value="clouds">Camada: Nuvens</option>
              <option value="pressure">Camada: Pressão</option>
            </select>

            <div className="segmented-track">
              <button
                type="button"
                onClick={() => setWindyFraming('world')}
                className={`segmented-item ${windyFraming === 'world' ? 'segmented-item-active' : ''}`}
              >
                Global
              </button>
              {target && (
                <button
                  type="button"
                  onClick={() => setWindyFraming('city')}
                  className={`segmented-item ${windyFraming === 'city' ? 'segmented-item-active' : ''}`}
                >
                  {target.label}
                </button>
              )}
            </div>

            <a
              href={windyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary text-[0.8rem] py-1.5 px-3 no-underline"
            >
              <ExternalLink size={13} />
              <span>Abrir externo</span>
            </a>
          </div>
        </div>

        <iframe
          title="Windy.com Mapa Meteorológico"
          src={windyUrl}
          className="w-full h-[480px] block border-0"
        />
      </section>

      {/* GLOBAL LIVE COMPARISON TABLE */}
      {tablePoints.length > 0 && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="m-0 text-[1.08rem] font-semibold">Comparativo Global em Tempo Real</h3>
              <p className="mt-0.5 mb-0 text-[0.82rem]" style={{ color: 'var(--text-muted)' }}>
                {tablePoints.length} localidades monitoradas simultaneamente via Open-Meteo.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => void handleResetDefaults()}
                disabled={pinsLoading}
                className="btn-secondary text-[0.8rem] py-1.5 px-3"
              >
                <Globe size={13} />
                <span>Restaurar capitais</span>
              </button>
              <button
                type="button"
                onClick={() => setWorldPins([])}
                className="btn-secondary text-[0.8rem] py-1.5 px-3"
              >
                <Trash2 size={13} />
                <span>Limpar lista</span>
              </button>
            </div>
          </div>

          {podium && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
              <div className="surface-panel px-4 py-3.5 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-[0.76rem]" style={{ color: 'var(--text-muted)' }}>
                    Maior temperatura agora
                  </div>
                  <div className="font-display font-semibold text-[1.02rem] truncate mt-0.5" title={podium.hottest.local}>
                    {podium.hottest.local}
                  </div>
                </div>
                <div className="flex items-center gap-1 font-mono-tabular font-semibold text-[1.15rem] shrink-0" style={{ color: 'var(--thermal-high)' }}>
                  <ArrowUp size={15} />
                  <span>{brNumber(podium.hottest.temperatura_c)} °C</span>
                </div>
              </div>

              <div className="surface-panel px-4 py-3.5 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-[0.76rem]" style={{ color: 'var(--text-muted)' }}>
                    Menor temperatura agora
                  </div>
                  <div className="font-display font-semibold text-[1.02rem] truncate mt-0.5" title={podium.coldest.local}>
                    {podium.coldest.local}
                  </div>
                </div>
                <div className="flex items-center gap-1 font-mono-tabular font-semibold text-[1.15rem] shrink-0" style={{ color: 'var(--thermal-low)' }}>
                  <ArrowDown size={15} />
                  <span>{brNumber(podium.coldest.temperatura_c)} °C</span>
                </div>
              </div>

              <div className="surface-panel px-4 py-3.5 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-[0.76rem]" style={{ color: 'var(--text-muted)' }}>
                    Maior velocidade de vento
                  </div>
                  <div className="font-display font-semibold text-[1.02rem] truncate mt-0.5" title={podium.windiest.local}>
                    {podium.windiest.local}
                  </div>
                </div>
                <div className="flex items-center gap-1.5 font-mono-tabular font-semibold text-[1.15rem] shrink-0" style={{ color: 'var(--text-primary)' }}>
                  <Wind size={15} style={{ color: 'var(--accent-text)' }} />
                  <span>{brNumber(podium.windiest.vento_kmh)} km/h</span>
                </div>
              </div>
            </div>
          )}

          <div className="data-grid-wrap">
            <table className="data-grid">
              <thead>
                <tr>
                  <th>Localidade</th>
                  <th>Condição</th>
                  <th className="num">Temp. (°C)</th>
                  <th className="num">Sensação (°C)</th>
                  <th className="num">Heat Index (°C)</th>
                  <th className="num">Orvalho (°C)</th>
                  <th className="num">Umidade (%)</th>
                  <th className="num">Vento (km/h)</th>
                  <th className="num">Pressão (hPa)</th>
                  <th className="num">Chuva (mm)</th>
                  <th className="num">Hora local</th>
                </tr>
              </thead>
              <tbody>
                {tablePoints.map((row) => (
                  <tr key={`${row.local}-${row.latitude}-${row.longitude}`}>
                    <td className="font-medium">{row.local}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{cleanConditionText(row.condicao)}</td>
                    <td className="num font-semibold">{brNumber(row.temperatura_c)}</td>
                    <td className="num">{brNumber(row.sensacao_c)}</td>
                    <td className="num">{brNumber(row.indice_calor_c)}</td>
                    <td className="num">{brNumber(row.ponto_orvalho_c)}</td>
                    <td className="num">{brNumber(row.umidade_pct, 0)}</td>
                    <td className="num">{brNumber(row.vento_kmh)}</td>
                    <td className="num">{brNumber(row.pressao_hpa, 0)}</td>
                    <td className="num">{brNumber(row.precipitacao_mm)}</td>
                    <td className="num" style={{ color: 'var(--text-muted)' }}>
                      {formatDatetimeFriendly(row.horario)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
};
