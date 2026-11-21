import React, { useEffect, useMemo, useState } from 'react';
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Download, FileSpreadsheet, Globe, Loader2, Upload } from 'lucide-react';
import type { SavedFileEntry, StationDataset } from '../types/weather';
import { MESES_NOMES, MESES_PT } from '../core/analysis';
import { identifyYearAndName, parseStationCsv } from '../core/dataLoader';
import { fetchAnnualDataset, searchCity } from '../core/weatherApi';
import { brNumber } from '../core/formatters';
import { MetricCard } from './MetricCard';

interface ComparisonTabProps {
  isDark: boolean;
  savedFiles: SavedFileEntry[];
  resolveSavedDataset: (entry: SavedFileEntry) => Promise<StationDataset>;
}

type SourceMode = 'saved' | 'upload' | 'era5';

const PRESET_COORDS: Record<string, [number, number]> = {
  manaus: [-3.1, -60.02],
  'são paulo': [-23.55, -46.63],
  'sao paulo': [-23.55, -46.63],
  'rio de janeiro': [-22.9, -43.17],
  brasília: [-15.78, -47.93],
  brasilia: [-15.78, -47.93],
  belém: [-1.45, -48.5],
  belem: [-1.45, -48.5],
  curitiba: [-25.42, -49.27],
  'porto alegre': [-30.03, -51.23],
  salvador: [-12.97, -38.51],
  recife: [-8.05, -34.88],
  fortaleza: [-3.71, -38.54],
};

function downloadCsv(content: string, filename: string) {
  const blob = new Blob(['\ufeff' + content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

interface DatasetSelectorCardProps {
  prefix: 'a' | 'b';
  title: string;
  accentColor: string;
  defaultIndex: number;
  savedFiles: SavedFileEntry[];
  resolveSavedDataset: (entry: SavedFileEntry) => Promise<StationDataset>;
  dataset: StationDataset | null;
  onChangeDataset: (ds: StationDataset | null) => void;
}

const DatasetSelectorCard: React.FC<DatasetSelectorCardProps> = ({
  prefix,
  title,
  accentColor,
  defaultIndex,
  savedFiles,
  resolveSavedDataset,
  dataset,
  onChangeDataset,
}) => {
  const currentYear = new Date().getFullYear();
  const [mode, setMode] = useState<SourceMode>(
    prefix === 'b' && savedFiles.length < 2 ? 'era5' : 'saved'
  );
  const [selectedId, setSelectedId] = useState<string>(
    savedFiles[defaultIndex]?.id || savedFiles[0]?.id || ''
  );
  const [city, setCity] = useState('Manaus');
  const [year, setYear] = useState(prefix === 'a' ? 2014 : currentYear - 1);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const yearOptions = useMemo(() => {
    const arr: number[] = [];
    for (let y = currentYear; y >= 1940; y--) arr.push(y);
    return arr;
  }, [currentYear]);

  useEffect(() => {
    if (mode !== 'saved' || !selectedId) return;
    const entry = savedFiles.find((f) => f.id === selectedId);
    if (!entry) return;
    let cancelled = false;
    setLoading(true);
    setErrorMsg(null);
    resolveSavedDataset(entry)
      .then((ds) => {
        if (!cancelled) onChangeDataset(ds);
      })
      .catch((err) => {
        if (!cancelled) {
          setErrorMsg(err instanceof Error ? err.message : String(err));
          onChangeDataset(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [mode, selectedId, savedFiles]);

  const handleUpload = async (file: File | undefined) => {
    if (!file) return;
    setLoading(true);
    setErrorMsg(null);
    setStatusMsg(null);
    try {
      const text = await file.text();
      const ds = parseStationCsv(text, file.name);
      onChangeDataset(ds);
      setStatusMsg(`Arquivo ${file.name} carregado.`);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleFetchEra5 = async () => {
    setLoading(true);
    setErrorMsg(null);
    setStatusMsg(null);
    try {
      const key = city.trim().toLowerCase();
      let lat = -3.1;
      let lon = -60.02;
      if (PRESET_COORDS[key]) {
        [lat, lon] = PRESET_COORDS[key];
      } else {
        const matches = await searchCity(city, 1);
        if (matches.length > 0) {
          lat = matches[0].latitude;
          lon = matches[0].longitude;
        }
      }
      const res = await fetchAnnualDataset(lat, lon, city.trim() || 'Manaus', year);
      onChangeDataset(res.dataset);
      setStatusMsg(`Série ${year} (${brNumber(res.dataset.data.length, 0)} horas) carregada via ERA5.`);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const metaInfo = dataset ? identifyYearAndName(dataset) : null;

  return (
    <div className="surface-panel p-5 space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono-tabular text-[0.75rem] font-semibold" style={{ color: accentColor }}>
            {prefix === 'a' ? 'SÉRIE A' : 'SÉRIE B'}
          </span>
          <span aria-hidden="true" style={{ color: 'var(--text-muted)' }}>·</span>
          <h3 className="m-0 text-[0.98rem] font-semibold">{title}</h3>
        </div>
      </div>

      <div className="segmented-track w-full">
        <button
          type="button"
          onClick={() => setMode('saved')}
          className={`segmented-item flex-1 justify-center ${mode === 'saved' ? 'segmented-item-active' : ''}`}
        >
          <FileSpreadsheet size={13} />
          <span>Salvo</span>
        </button>
        <button
          type="button"
          onClick={() => setMode('upload')}
          className={`segmented-item flex-1 justify-center ${mode === 'upload' ? 'segmented-item-active' : ''}`}
        >
          <Upload size={13} />
          <span>Upload CSV</span>
        </button>
        <button
          type="button"
          onClick={() => setMode('era5')}
          className={`segmented-item flex-1 justify-center ${mode === 'era5' ? 'segmented-item-active' : ''}`}
        >
          <Globe size={13} />
          <span>ERA5</span>
        </button>
      </div>

      {mode === 'saved' && (
        <div>
          <label className="block text-[0.78rem] font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>
            Arquivo disponível
          </label>
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="field-input"
          >
            {savedFiles.map((f) => (
              <option key={f.id} value={f.id}>
                {f.folder}/{f.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {mode === 'upload' && (
        <div>
          <label className="block text-[0.78rem] font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>
            Selecionar CSV (INMET ou ClimaPS)
          </label>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => {
              void handleUpload(e.target.files?.[0]);
              e.target.value = '';
            }}
            className="field-input text-[0.82rem]"
          />
        </div>
      )}

      {mode === 'era5' && (
        <div className="space-y-3">
          <div className="grid grid-cols-12 gap-2.5">
            <div className="col-span-7">
              <label className="block text-[0.78rem] font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>
                Cidade ou estação
              </label>
              <input
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="field-input"
              />
            </div>
            <div className="col-span-5">
              <label className="block text-[0.78rem] font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>
                Ano
              </label>
              <select
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                className="field-input font-mono-tabular"
              >
                {yearOptions.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void handleFetchEra5()}
            disabled={loading}
            className="btn-primary w-full"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            <span>{loading ? `Consultando ${year}...` : `Buscar série ${year} (ERA5)`}</span>
          </button>
        </div>
      )}

      {statusMsg && (
        <div className="text-[0.8rem]" style={{ color: 'var(--nominal)' }}>
          {statusMsg}
        </div>
      )}
      {errorMsg && (
        <div className="text-[0.8rem]" style={{ color: 'var(--danger)' }}>
          {errorMsg}
        </div>
      )}

      {metaInfo && dataset && (
        <div
          className="pt-3 flex items-center justify-between text-[0.8rem]"
          style={{ borderTop: '1px solid var(--border-hairline)', color: 'var(--text-muted)' }}
        >
          <span className="truncate font-medium" style={{ color: 'var(--text-primary)' }}>
            {metaInfo.nome}
          </span>
          <span className="font-mono-tabular shrink-0 ml-2">
            {metaInfo.ano} · {brNumber(dataset.data.length, 0)} h
          </span>
        </div>
      )}
    </div>
  );
};

export const ComparisonTab: React.FC<ComparisonTabProps> = ({
  isDark,
  savedFiles,
  resolveSavedDataset,
}) => {
  const [datasetA, setDatasetA] = useState<StationDataset | null>(null);
  const [datasetB, setDatasetB] = useState<StationDataset | null>(null);

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

  const analysis = useMemo(() => {
    if (!datasetA || !datasetB) return null;

    const infoA = identifyYearAndName(datasetA);
    const infoB = identifyYearAndName(datasetB);

    const calcAnnual = (ds: StationDataset) => {
      let tSum = 0;
      let tCnt = 0;
      let tMax = -Infinity;
      let tMin = Infinity;
      let rainTotal = 0;
      const byDay = new Map<string, number>();
      const byMonth = new Map<number, { tSum: number; tCnt: number; rain: number }>();

      for (const r of ds.data) {
        if (r.temp_max_c !== null) {
          tSum += r.temp_max_c;
          tCnt++;
          if (r.temp_max_c > tMax) tMax = r.temp_max_c;
        }
        if (r.temp_min_c !== null && r.temp_min_c < tMin) tMin = r.temp_min_c;
        const rain = r.precipitacao_mm ?? 0;
        rainTotal += rain;
        byDay.set(r.dia, (byDay.get(r.dia) ?? 0) + rain);

        const m = byMonth.get(r.mes) || { tSum: 0, tCnt: 0, rain: 0 };
        m.rain += rain;
        if (r.temp_max_c !== null) {
          m.tSum += r.temp_max_c;
          m.tCnt++;
        }
        byMonth.set(r.mes, m);
      }

      const sortedDays = Array.from(byDay.entries()).sort((a, b) => a[0].localeCompare(b[0]));
      let rainDays = 0;
      let maxRain24h = 0;
      let running = 0;
      const cumulative = sortedDays.map(([, val], idx) => {
        if (val > 0.2) rainDays++;
        if (val > maxRain24h) maxRain24h = val;
        running += val;
        return { dia_num: idx + 1, acum: Math.round(running * 10) / 10 };
      });

      return {
        tMed: tCnt > 0 ? tSum / tCnt : 0,
        tMax: Number.isFinite(tMax) ? tMax : 0,
        tMin: Number.isFinite(tMin) ? tMin : 0,
        rainTotal,
        rainDays,
        maxRain24h,
        byMonth,
        cumulative,
      };
    };

    const a = calcAnnual(datasetA);
    const b = calcAnnual(datasetB);

    const monthSet = new Set<number>([...a.byMonth.keys(), ...b.byMonth.keys()]);
    const monthly = Array.from(monthSet)
      .sort((x, y) => x - y)
      .map((m) => {
        const ma = a.byMonth.get(m);
        const mb = b.byMonth.get(m);
        const tempA = ma && ma.tCnt > 0 ? ma.tSum / ma.tCnt : null;
        const tempB = mb && mb.tCnt > 0 ? mb.tSum / mb.tCnt : null;
        const rainA = ma ? ma.rain : 0;
        const rainB = mb ? mb.rain : 0;
        const deltaTemp = tempA !== null && tempB !== null ? tempB - tempA : null;
        const deltaRain = rainB - rainA;
        const pctRain = rainA > 0 ? (deltaRain / rainA) * 100 : 0;
        return {
          mes: m,
          mes_nome: MESES_NOMES[m - 1] || String(m),
          mes_abrev: MESES_PT[m] || String(m),
          temp_media_a: tempA !== null ? Math.round(tempA * 10) / 10 : null,
          temp_media_b: tempB !== null ? Math.round(tempB * 10) / 10 : null,
          delta_temp: deltaTemp !== null ? Math.round(deltaTemp * 10) / 10 : null,
          chuva_total_a: Math.round(rainA * 10) / 10,
          chuva_total_b: Math.round(rainB * 10) / 10,
          delta_chuva: Math.round(deltaRain * 10) / 10,
          pct_chuva: Math.round(pctRain * 10) / 10,
        };
      });

    const maxDays = Math.max(a.cumulative.length, b.cumulative.length);
    const trajectory = Array.from({ length: maxDays }, (_, idx) => ({
      dia_num: idx + 1,
      acum_a: a.cumulative[idx]?.acum ?? null,
      acum_b: b.cumulative[idx]?.acum ?? null,
    }));

    return { infoA, infoB, a, b, monthly, trajectory };
  }, [datasetA, datasetB]);

  const handleDownloadCompCsv = () => {
    if (!analysis) return;
    const { infoA, infoB, monthly } = analysis;
    const headers = [
      'Mês',
      `Temp. Média ${infoA.ano} (°C)`,
      `Temp. Média ${infoB.ano} (°C)`,
      'Δ Temp (°C)',
      `Chuva ${infoA.ano} (mm)`,
      `Chuva ${infoB.ano} (mm)`,
      'Δ Chuva (mm)',
      'Variação Chuva (%)',
    ];
    const fmt = (v: number | null) => (v === null ? '' : String(v).replace('.', ','));
    const lines = [
      headers.join(';'),
      ...monthly.map((r) =>
        [
          r.mes_nome,
          fmt(r.temp_media_a),
          fmt(r.temp_media_b),
          fmt(r.delta_temp),
          fmt(r.chuva_total_a),
          fmt(r.chuva_total_b),
          fmt(r.delta_chuva),
          fmt(r.pct_chuva),
        ].join(';')
      ),
    ];
    downloadCsv(lines.join('\n') + '\n', `climaps_comparacao_${infoA.ano}_vs_${infoB.ano}.csv`);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="m-0 text-[1.25rem] font-bold tracking-tight">Comparação Interanual de Séries</h1>
        <p className="mt-1 mb-0 text-[0.86rem]" style={{ color: 'var(--text-muted)' }}>
          Confronte dois anos climáticos ou duas estações meteorológicas para medir variações térmicas e pluviométricas mês a mês.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DatasetSelectorCard
          prefix="a"
          title="Referência Base"
          accentColor="var(--thermal-high)"
          defaultIndex={0}
          savedFiles={savedFiles}
          resolveSavedDataset={resolveSavedDataset}
          dataset={datasetA}
          onChangeDataset={setDatasetA}
        />
        <DatasetSelectorCard
          prefix="b"
          title="Série Comparativa"
          accentColor="var(--accent-text)"
          defaultIndex={1}
          savedFiles={savedFiles}
          resolveSavedDataset={resolveSavedDataset}
          dataset={datasetB}
          onChangeDataset={setDatasetB}
        />
      </div>

      {!analysis ? (
        <div className="surface-subtle p-6 text-center text-[0.86rem]" style={{ color: 'var(--text-muted)' }}>
          Selecione ou busque as duas séries acima (Série A e Série B) para gerar os gráficos e deltas comparativos.
        </div>
      ) : (
        <div className="space-y-6">
          {/* Clean Side-by-side Comparison Strip */}
          <div className="surface-panel px-6 py-4 flex flex-wrap items-center justify-between gap-4">
            <div className="min-w-[180px]">
              <div className="text-[0.74rem] font-mono-tabular font-semibold" style={{ color: 'var(--thermal-high)' }}>
                SÉRIE A · {analysis.infoA.ano}
              </div>
              <div className="font-display text-[1.15rem] font-bold mt-0.5">{analysis.infoA.nome}</div>
              <div className="text-[0.78rem] font-mono-tabular" style={{ color: 'var(--text-muted)' }}>
                {brNumber(datasetA?.data.length, 0)} registros horários
              </div>
            </div>

            <div className="font-mono-tabular text-[0.8rem] font-semibold" style={{ color: 'var(--text-muted)' }}>
              VS
            </div>

            <div className="min-w-[180px] sm:text-right">
              <div className="text-[0.74rem] font-mono-tabular font-semibold" style={{ color: 'var(--accent-text)' }}>
                SÉRIE B · {analysis.infoB.ano}
              </div>
              <div className="font-display text-[1.15rem] font-bold mt-0.5">{analysis.infoB.nome}</div>
              <div className="text-[0.78rem] font-mono-tabular" style={{ color: 'var(--text-muted)' }}>
                {brNumber(datasetB?.data.length, 0)} registros horários
              </div>
            </div>
          </div>

          {/* 6 Comparative KPIs */}
          {(() => {
            const deltaT = analysis.b.tMed - analysis.a.tMed;
            const deltaMax = analysis.b.tMax - analysis.a.tMax;
            const deltaMin = analysis.b.tMin - analysis.a.tMin;
            const deltaRain = analysis.b.rainTotal - analysis.a.rainTotal;
            const pctRain = analysis.a.rainTotal > 0 ? (deltaRain / analysis.a.rainTotal) * 100 : 0;
            const deltaDays = analysis.b.rainDays - analysis.a.rainDays;
            const delta24h = analysis.b.maxRain24h - analysis.a.maxRain24h;

            return (
              <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3.5">
                <MetricCard
                  label="Temp. média anual"
                  value={brNumber(analysis.b.tMed)}
                  unit="°C"
                  subtext={`${deltaT >= 0 ? '+' : ''}${deltaT.toFixed(1)} °C vs ${analysis.infoA.ano}`}
                  tone={deltaT > 0.3 ? 'negative' : deltaT < -0.3 ? 'positive' : 'neutral'}
                />
                <MetricCard
                  label="Máxima absoluta"
                  value={brNumber(analysis.b.tMax)}
                  unit="°C"
                  subtext={`${deltaMax >= 0 ? '+' : ''}${deltaMax.toFixed(1)} °C vs ${analysis.infoA.ano}`}
                />
                <MetricCard
                  label="Mínima absoluta"
                  value={brNumber(analysis.b.tMin)}
                  unit="°C"
                  subtext={`${deltaMin >= 0 ? '+' : ''}${deltaMin.toFixed(1)} °C vs ${analysis.infoA.ano}`}
                />
                <MetricCard
                  label="Chuva acumulada"
                  value={brNumber(analysis.b.rainTotal)}
                  unit="mm"
                  subtext={`${deltaRain >= 0 ? '+' : ''}${deltaRain.toFixed(0)} mm (${pctRain >= 0 ? '+' : ''}${pctRain.toFixed(1)}%)`}
                  tone={deltaRain >= 0 ? 'positive' : 'warning'}
                />
                <MetricCard
                  label="Dias de chuva (>0.2mm)"
                  value={String(analysis.b.rainDays)}
                  unit="dias"
                  subtext={`${deltaDays >= 0 ? '+' : ''}${deltaDays} dias vs ${analysis.infoA.ano}`}
                />
                <MetricCard
                  label="Pico diário (24h)"
                  value={brNumber(analysis.b.maxRain24h)}
                  unit="mm"
                  subtext={`${delta24h >= 0 ? '+' : ''}${delta24h.toFixed(1)} mm vs ${analysis.infoA.ano}`}
                />
              </div>
            );
          })()}

          {/* Monthly Thermal & Precipitation Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="surface-panel p-5 space-y-3">
              <h3 className="m-0 text-[0.96rem] font-semibold">
                Perfil Térmico Mensal ({analysis.infoA.ano} vs {analysis.infoB.ano})
              </h3>
              <div className="w-full h-[310px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={analysis.monthly} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                    <XAxis dataKey="mes_abrev" tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} unit="°" />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                    <Line type="monotone" dataKey="temp_media_a" name={`Série A (${analysis.infoA.ano})`} stroke="#F59E0B" strokeWidth={2.4} dot={{ r: 3.5, strokeWidth: 0, fill: '#F59E0B' }} />
                    <Area type="monotone" dataKey="temp_media_b" name={`Série B (${analysis.infoB.ano})`} stroke={isDark ? '#38BDF8' : '#0284C7'} fill={isDark ? 'rgba(56, 189, 248, 0.12)' : 'rgba(2, 132, 199, 0.1)'} strokeWidth={2.4} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="surface-panel p-5 space-y-3">
              <h3 className="m-0 text-[0.96rem] font-semibold">Precipitação Mensal Comparada (mm)</h3>
              <div className="w-full h-[310px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={analysis.monthly} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                    <XAxis dataKey="mes_abrev" tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                    <Bar dataKey="chuva_total_a" name={`Série A (${analysis.infoA.ano})`} fill="rgba(245, 158, 11, 0.85)" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="chuva_total_b" name={`Série B (${analysis.infoB.ano})`} fill={isDark ? 'rgba(56, 189, 248, 0.85)' : 'rgba(2, 132, 199, 0.85)'} radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Cumulative Annual Trajectory */}
          <div className="surface-panel p-5 space-y-3">
            <h3 className="m-0 text-[0.96rem] font-semibold">
              Trajetória de Precipitação Acumulada (Dia 1 ao 365)
            </h3>
            <div className="w-full h-[290px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={analysis.trajectory} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                  <XAxis dataKey="dia_num" tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} unit="mm" />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                  <Line type="monotone" dataKey="acum_a" name={`Acumulado ${analysis.infoA.ano}`} stroke="#F59E0B" strokeWidth={2.2} dot={false} />
                  <Line type="monotone" dataKey="acum_b" name={`Acumulado ${analysis.infoB.ano}`} stroke={isDark ? '#38BDF8' : '#0284C7'} strokeWidth={2.4} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Monthly Matrix Table */}
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="m-0 text-[1rem] font-semibold">Matriz Comparativa Mensal</h3>
              <button type="button" onClick={handleDownloadCompCsv} className="btn-secondary text-[0.8rem] py-1.5 px-3">
                <Download size={13} />
                <span>Baixar tabela CSV</span>
              </button>
            </div>
            <div className="data-grid-wrap">
              <table className="data-grid">
                <thead>
                  <tr>
                    <th>Mês</th>
                    <th className="num">Temp. {analysis.infoA.ano} (°C)</th>
                    <th className="num">Temp. {analysis.infoB.ano} (°C)</th>
                    <th className="num">Δ Temp (°C)</th>
                    <th className="num">Chuva {analysis.infoA.ano} (mm)</th>
                    <th className="num">Chuva {analysis.infoB.ano} (mm)</th>
                    <th className="num">Δ Chuva (mm)</th>
                    <th className="num">Variação (%)</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.monthly.map((row) => (
                    <tr key={row.mes}>
                      <td className="font-medium">{row.mes_nome}</td>
                      <td className="num">{brNumber(row.temp_media_a)}</td>
                      <td className="num">{brNumber(row.temp_media_b)}</td>
                      <td
                        className="num font-semibold"
                        style={{
                          color:
                            row.delta_temp !== null && row.delta_temp > 0
                              ? 'var(--thermal-high)'
                              : row.delta_temp !== null && row.delta_temp < 0
                              ? 'var(--thermal-low)'
                              : 'var(--text-muted)',
                        }}
                      >
                        {row.delta_temp !== null
                          ? `${row.delta_temp >= 0 ? '+' : ''}${brNumber(row.delta_temp)}`
                          : '-'}
                      </td>
                      <td className="num">{brNumber(row.chuva_total_a)}</td>
                      <td className="num">{brNumber(row.chuva_total_b)}</td>
                      <td className="num">
                        {row.delta_chuva >= 0 ? '+' : ''}
                        {brNumber(row.delta_chuva)}
                      </td>
                      <td className="num">
                        {row.pct_chuva >= 0 ? '+' : ''}
                        {brNumber(row.pct_chuva)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
