import React, { useMemo, useState } from 'react';
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Database,
  Download,
  FileCode2,
  FileSpreadsheet,
  FileText,
  FolderPlus,
  Save,
} from 'lucide-react';
import type {
  ColumnMissingStat,
  FilterSpec,
  PrecipitationHistogramBin,
  StationDataset,
  WeatherRecord,
} from '../types/weather';
import {
  MESES_PT,
  MISSING_ALERT_THRESHOLD_PCT,
  calculateColumnMissingStats,
  calculateKpis,
  climatologicalThresholdMonitor,
  correlationMatrix,
  dailySummary,
  generateInsights,
  monthlySummary,
  precipitationHistogram,
  qualityReport,
} from '../core/analysis';
import { buildCsvExport, buildSqlScript } from '../core/dataLoader';
import { generateStructuredPdfReport } from '../core/pdfReport';
import { brNumber, formatDateTimeBR, getStamp } from '../core/formatters';
import { MetricCard } from './MetricCard';

function triggerDownload(content: string, filename: string, mime: string) {
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

/* ============================================================================
   TAB 3: RESUMO E QUALIDADE
   ============================================================================ */
export const SummaryTab: React.FC<{
  filtered: WeatherRecord[];
  fullRecords: WeatherRecord[];
  extraColumns?: ColumnMissingStat[];
  isDark: boolean;
}> = ({ filtered, fullRecords, extraColumns, isDark }) => {
  const [missingScope, setMissingScope] = useState<'full' | 'filtered'>('full');
  const [histView, setHistView] = useState<'all' | 'extremes'>('all');
  const [histMetric, setHistMetric] = useState<'density' | 'count'>('density');
  const [sigmaThreshold, setSigmaThreshold] = useState<number>(2);
  const [alertVarFilter, setAlertVarFilter] = useState<'all' | 'rain' | 'tempMax' | 'tempMin'>('all');
  const [alertSort, setAlertSort] = useState<'severity' | 'time'>('severity');
  const [alertPage, setAlertPage] = useState<number>(0);

  const kpis = useMemo(() => calculateKpis(filtered), [filtered]);
  const insights = useMemo(() => generateInsights(filtered), [filtered]);
  const mensal = useMemo(() => monthlySummary(filtered), [filtered]);
  const report = useMemo(() => qualityReport(fullRecords), [fullRecords]);
  const rainHist = useMemo(() => precipitationHistogram(filtered), [filtered]);
  const monitor = useMemo(
    () => climatologicalThresholdMonitor(fullRecords, filtered, sigmaThreshold),
    [fullRecords, filtered, sigmaThreshold]
  );
  const missingByColumn = useMemo(() => {
    const sourceRecords = missingScope === 'full' ? fullRecords : filtered;
    const extras = missingScope === 'full' ? extraColumns ?? [] : [];
    return calculateColumnMissingStats(sourceRecords, extras, MISSING_ALERT_THRESHOLD_PCT);
  }, [missingScope, fullRecords, filtered, extraColumns]);
  const criticalColumns = useMemo(
    () => missingByColumn.filter((c) => c.exceedsThreshold),
    [missingByColumn]
  );

  const displayedHistBins = useMemo(() => {
    if (histView === 'extremes' && rainHist.extremeCount > 0) {
      return rainHist.bins.filter((b) => b.isExtreme);
    }
    return rainHist.bins;
  }, [histView, rainHist]);

  const displayedAlerts = useMemo(() => {
    const list =
      alertVarFilter === 'all'
        ? monitor.alerts
        : monitor.alerts.filter((a) => a.flags.some((f) => f.variable === alertVarFilter));
    const sorted = [...list];
    if (alertSort === 'severity') {
      sorted.sort((a, b) => b.maxAbsZ - a.maxAbsZ);
    } else {
      sorted.sort((a, b) => b.record.timestamp - a.record.timestamp);
    }
    return sorted;
  }, [monitor.alerts, alertVarFilter, alertSort]);

  const alertsPerPage = 12;
  const totalAlertPages = Math.max(1, Math.ceil(displayedAlerts.length / alertsPerPage));
  const safeAlertPage = Math.min(alertPage, totalAlertPages - 1);
  const alertSlice = displayedAlerts.slice(
    safeAlertPage * alertsPerPage,
    (safeAlertPage + 1) * alertsPerPage
  );

  if (filtered.length === 0) {
    return (
      <div className="surface-panel p-6 text-[0.88rem]" style={{ color: 'var(--text-secondary)' }}>
        Nenhum registro atende aos filtros selecionados na barra lateral. Ajuste o período ou a janela horária.
      </div>
    );
  }

  const qualityRows = [
    { indicador: 'Lacunas de timestamp', valor: report.timestamps_ausentes, warn: report.timestamps_ausentes > 0 },
    { indicador: 'Timestamps duplicados', valor: report.timestamps_duplicados, warn: report.timestamps_duplicados > 0 },
    { indicador: 'Chuva negativa', valor: report.chuva_negativa, warn: report.chuva_negativa > 0 },
    {
      indicador: 'Chuva acima do limite físico (> 150 mm/h)',
      valor: report.chuva_extrema_fisica,
      warn: report.chuva_extrema_fisica > 0,
    },
    { indicador: 'Máxima < Mínima', valor: report.temp_inconsistente, warn: report.temp_inconsistente > 0 },
    { indicador: 'Ausentes em chuva', valor: report.valores_ausentes.precipitacao_mm, warn: report.valores_ausentes.precipitacao_mm > 0 },
    { indicador: 'Ausentes em temp. máx.', valor: report.valores_ausentes.temp_max_c, warn: report.valores_ausentes.temp_max_c > 0 },
    { indicador: 'Ausentes em temp. mín.', valor: report.valores_ausentes.temp_min_c, warn: report.valores_ausentes.temp_min_c > 0 },
    {
      indicador: 'Outliers de chuva (IQR em horas chuvosas)',
      valor: report.outliers_iqr.precipitacao_mm,
      warn: false,
    },
    {
      indicador: 'Outliers térmicos (IQR máx./mín.)',
      valor: report.outliers_iqr.temp_max_c + report.outliers_iqr.temp_min_c,
      warn: false,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
        <MetricCard label="Registros no recorte" value={brNumber(kpis.registros, 0)} unit="h" />
        <MetricCard label="Chuva acumulada" value={brNumber(kpis.precipitacao_total)} unit="mm" />
        <MetricCard label="Temp. máxima média" value={brNumber(kpis.temp_max_media)} unit="°C" />
        <MetricCard label="Temp. mínima média" value={brNumber(kpis.temp_min_media)} unit="°C" />
        <MetricCard
          label="Completude dos dados"
          value={brNumber(kpis.completude)}
          unit="%"
          tone={kpis.completude >= 95 ? 'positive' : 'warning'}
        />
      </div>

      {/* Automated Insights */}
      <div className="surface-panel p-5 space-y-3">
        <h2 className="m-0 text-[1rem] font-semibold">Destaques do Recorte</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {insights.map((text, idx) => (
            <div
              key={idx}
              className="surface-subtle px-4 py-3 text-[0.85rem] leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}
            >
              {text}
            </div>
          ))}
        </div>
      </div>

      {/* Precipitation Distribution Histogram & Extreme Tail Density */}
      <div className="surface-panel p-5 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="m-0 text-[1rem] font-semibold">
              Histograma de Precipitação e Densidade de Extremos
            </h2>
            <p className="mt-1 mb-0 text-[0.8rem]" style={{ color: 'var(--text-muted)' }}>
              Distribuição das horas com chuva (&gt; 0 mm) destacando eventos acima do limite superior IQR (Q3 + 1,5 × IQR)
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="segmented-track" role="group" aria-label="Recorte do histograma">
              <button
                type="button"
                onClick={() => setHistView('all')}
                className={`segmented-item ${histView === 'all' ? 'segmented-item-active' : ''}`}
              >
                Todas as faixas
              </button>
              <button
                type="button"
                disabled={rainHist.extremeCount === 0}
                onClick={() => setHistView('extremes')}
                className={`segmented-item ${histView === 'extremes' && rainHist.extremeCount > 0 ? 'segmented-item-active' : ''}`}
                style={rainHist.extremeCount === 0 ? { opacity: 0.45, cursor: 'not-allowed' } : undefined}
              >
                Cauda extrema
              </button>
            </div>

            <div className="segmented-track" role="group" aria-label="Métrica do eixo Y">
              <button
                type="button"
                onClick={() => setHistMetric('density')}
                className={`segmented-item ${histMetric === 'density' ? 'segmented-item-active' : ''}`}
              >
                Densidade (%)
              </button>
              <button
                type="button"
                onClick={() => setHistMetric('count')}
                className={`segmented-item ${histMetric === 'count' ? 'segmented-item-active' : ''}`}
              >
                Frequência (h)
              </button>
            </div>
          </div>
        </div>

        {rainHist.rainyCount === 0 ? (
          <div
            className="surface-subtle px-4 py-6 text-center text-[0.84rem]"
            style={{ color: 'var(--text-muted)' }}
          >
            Nenhuma hora com precipitação &gt; 0 mm no recorte atual para construir o histograma.
          </div>
        ) : (
          <>
            {/* Compact Statistical Threshold Strip */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              <div className="surface-subtle px-3.5 py-2.5">
                <div className="text-[0.72rem] font-medium" style={{ color: 'var(--text-muted)' }}>
                  Horas com chuva
                </div>
                <div className="mt-1 font-mono-tabular text-[1rem] font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {brNumber(rainHist.rainyCount, 0)} h
                </div>
                <div className="text-[0.72rem] font-mono-tabular" style={{ color: 'var(--text-muted)' }}>
                  {brNumber(rainHist.zeroCount, 0)} h secas (0 mm)
                </div>
              </div>

              <div className="surface-subtle px-3.5 py-2.5">
                <div className="text-[0.72rem] font-medium" style={{ color: 'var(--text-muted)' }}>
                  Mediana · Q3
                </div>
                <div className="mt-1 font-mono-tabular text-[1rem] font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {brNumber(rainHist.median)} · {brNumber(rainHist.q3)} mm
                </div>
                <div className="text-[0.72rem] font-mono-tabular" style={{ color: 'var(--text-muted)' }}>
                  IQR {brNumber(rainHist.iqr)} mm
                </div>
              </div>

              <div className="surface-subtle px-3.5 py-2.5">
                <div className="text-[0.72rem] font-medium" style={{ color: 'var(--text-muted)' }}>
                  Limite normal (Q3 + 1,5×IQR)
                </div>
                <div className="mt-1 font-mono-tabular text-[1rem] font-semibold" style={{ color: 'var(--accent-text)' }}>
                  {brNumber(rainHist.upperFence)} mm/h
                </div>
                <div className="text-[0.72rem] font-mono-tabular" style={{ color: 'var(--text-muted)' }}>
                  P95: {brNumber(rainHist.p95)} mm/h
                </div>
              </div>

              <div
                className="surface-subtle px-3.5 py-2.5"
                style={
                  rainHist.extremeCount > 0
                    ? { borderColor: 'rgba(239, 68, 68, 0.35)' }
                    : undefined
                }
              >
                <div className="text-[0.72rem] font-medium" style={{ color: 'var(--text-muted)' }}>
                  Densidade de extremos
                </div>
                <div
                  className="mt-1 font-mono-tabular text-[1rem] font-semibold"
                  style={{ color: rainHist.extremeCount > 0 ? 'var(--danger)' : 'var(--nominal)' }}
                >
                  {brNumber(rainHist.extremePct, 1)}%
                </div>
                <div className="text-[0.72rem] font-mono-tabular" style={{ color: 'var(--text-muted)' }}>
                  {brNumber(rainHist.extremeCount, 0)} eventos &gt; limite
                </div>
              </div>

              <div className="surface-subtle px-3.5 py-2.5">
                <div className="text-[0.72rem] font-medium" style={{ color: 'var(--text-muted)' }}>
                  Pico máximo horário
                </div>
                <div className="mt-1 font-mono-tabular text-[1rem] font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {brNumber(rainHist.maxVal)} mm/h
                </div>
                <div className="text-[0.72rem]" style={{ color: 'var(--text-muted)' }}>
                  {rainHist.maxVal !== null && rainHist.upperFence !== null && rainHist.maxVal > rainHist.upperFence
                    ? 'Fora da faixa normal'
                    : 'Dentro da faixa normal'}
                </div>
              </div>
            </div>

            {/* Histogram Chart */}
            <div className="w-full h-[300px] pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={displayedHistBins}
                  margin={{ top: 18, right: 16, left: 4, bottom: 26 }}
                  barCategoryGap="10%"
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                    stroke={isDark ? 'rgba(148, 163, 184, 0.12)' : 'rgba(15, 23, 42, 0.08)'}
                  />
                  <XAxis
                    dataKey="rangeLabel"
                    tick={{
                      fill: isDark ? '#94A3B8' : '#475569',
                      fontSize: 11,
                      fontFamily: 'var(--font-mono)',
                    }}
                    angle={-25}
                    textAnchor="end"
                    height={52}
                    interval={0}
                  />
                  <YAxis
                    tick={{
                      fill: isDark ? '#94A3B8' : '#475569',
                      fontSize: 11,
                      fontFamily: 'var(--font-mono)',
                    }}
                    tickFormatter={(v: number) =>
                      histMetric === 'density' ? `${brNumber(v, 0)}%` : brNumber(v, 0)
                    }
                    width={52}
                  />
                  <Tooltip
                    cursor={{ fill: isDark ? 'rgba(148, 163, 184, 0.08)' : 'rgba(15, 23, 42, 0.05)' }}
                    content={({ active, payload }) => {
                      if (!active || !payload || payload.length === 0) return null;
                      const bin = payload[0].payload as PrecipitationHistogramBin;
                      return (
                        <div
                          className="rounded-lg px-3.5 py-2.5 text-[0.79rem] shadow-lg space-y-1"
                          style={{
                            backgroundColor: isDark ? '#0E131F' : '#FFFFFF',
                            border: `1px solid ${isDark ? 'rgba(148, 163, 184, 0.25)' : '#CBD5E1'}`,
                            color: isDark ? '#F1F5F9' : '#0F172A',
                          }}
                        >
                          <div className="font-mono-tabular font-semibold">
                            Faixa: {bin.rangeLabel} mm/h
                          </div>
                          <div className="font-mono-tabular flex items-center justify-between gap-4">
                            <span style={{ color: 'var(--text-muted)' }}>Densidade:</span>
                            <span className="font-semibold">{brNumber(bin.densityPct, 2)}%</span>
                          </div>
                          <div className="font-mono-tabular flex items-center justify-between gap-4">
                            <span style={{ color: 'var(--text-muted)' }}>Frequência:</span>
                            <span className="font-semibold">{brNumber(bin.count, 0)} h</span>
                          </div>
                          <div
                            className="pt-1 text-[0.74rem] font-medium"
                            style={{ color: bin.isExtreme ? 'var(--danger)' : 'var(--accent-text)' }}
                          >
                            {bin.isExtreme
                              ? 'Evento extremo (> Q3 + 1,5 × IQR)'
                              : 'Intervalo estatístico normal'}
                          </div>
                        </div>
                      );
                    }}
                  />
                  {histView === 'all' && rainHist.firstExtremeBinLabel && (
                    <ReferenceLine
                      x={rainHist.firstExtremeBinLabel}
                      stroke={isDark ? '#EF4444' : '#DC2626'}
                      strokeDasharray="4 4"
                      strokeWidth={1.5}
                      label={{
                        value: `> ${brNumber(rainHist.upperFence)} mm/h`,
                        position: 'top',
                        fill: isDark ? '#F87171' : '#DC2626',
                        fontSize: 11,
                        fontFamily: 'var(--font-mono)',
                      }}
                    />
                  )}
                  <Bar
                    dataKey={histMetric === 'density' ? 'densityPct' : 'count'}
                    radius={[4, 4, 0, 0]}
                    maxBarSize={48}
                  >
                    {displayedHistBins.map((bin) => (
                      <Cell
                        key={bin.id}
                        fill={
                          bin.isExtreme
                            ? isDark
                              ? '#EF4444'
                              : '#DC2626'
                            : isDark
                              ? '#0EA5E9'
                              : '#0284C7'
                        }
                        fillOpacity={bin.isExtreme ? 0.9 : 0.82}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Legend Footer */}
            <div
              className="flex flex-wrap items-center justify-between gap-3 pt-1 text-[0.76rem]"
              style={{ color: 'var(--text-muted)' }}
            >
              <div className="flex flex-wrap items-center gap-4">
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="inline-block w-2.5 h-2.5 rounded-xs"
                    style={{ backgroundColor: isDark ? '#0EA5E9' : '#0284C7' }}
                  />
                  <span>Intervalo normal (≤ {brNumber(rainHist.upperFence)} mm/h)</span>
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="inline-block w-2.5 h-2.5 rounded-xs"
                    style={{ backgroundColor: isDark ? '#EF4444' : '#DC2626' }}
                  />
                  <span>Cauda extrema (&gt; {brNumber(rainHist.upperFence)} mm/h)</span>
                </span>
              </div>
              <span className="font-mono-tabular">
                Eixo X: intensidade horária (mm/h) · horas secas (0 mm) excluídas da densidade
              </span>
            </div>
          </>
        )}
      </div>

      {/* Missing Data Percentage by Column */}
      <div className="surface-panel p-5 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="m-0 text-[1rem] font-semibold">Dados Faltantes por Coluna</h2>
            <p className="mt-1 mb-0 text-[0.8rem]" style={{ color: 'var(--text-muted)' }}>
              Percentual de valores nulos ou NaN em{' '}
              <span className="font-mono-tabular">
                {brNumber(missingScope === 'full' ? fullRecords.length : filtered.length, 0)}
              </span>{' '}
              registros · destaque automático acima de{' '}
              <span className="font-mono-tabular">{MISSING_ALERT_THRESHOLD_PCT}%</span>
            </p>
          </div>

          <div className="segmented-track" role="group" aria-label="Escopo da análise de lacunas">
            <button
              type="button"
              onClick={() => setMissingScope('full')}
              className={`segmented-item ${missingScope === 'full' ? 'segmented-item-active' : ''}`}
            >
              Base completa
            </button>
            <button
              type="button"
              onClick={() => setMissingScope('filtered')}
              className={`segmented-item ${missingScope === 'filtered' ? 'segmented-item-active' : ''}`}
            >
              Recorte filtrado
            </button>
          </div>
        </div>

        {criticalColumns.length > 0 ? (
          <div
            className="rounded-lg px-4 py-3 flex items-start gap-2.5 text-[0.84rem]"
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.08)',
              border: '1px solid rgba(239, 68, 68, 0.28)',
              color: 'var(--text-primary)',
            }}
          >
            <AlertTriangle size={16} className="shrink-0 mt-0.5" style={{ color: 'var(--danger)' }} />
            <div>
              <span className="font-semibold" style={{ color: 'var(--danger)' }}>
                {criticalColumns.length === 1
                  ? '1 coluna com lacunas superiores a 10%:'
                  : `${criticalColumns.length} colunas com lacunas superiores a 10%:`}
              </span>{' '}
              <span style={{ color: 'var(--text-secondary)' }}>
                {criticalColumns.map((c) => `${c.label} (${brNumber(c.missingPct, 2)}%)`).join(', ')}.
              </span>
            </div>
          </div>
        ) : (
          <div
            className="flex items-center gap-2 text-[0.82rem]"
            style={{ color: 'var(--text-secondary)' }}
          >
            <CheckCircle2 size={15} className="shrink-0" style={{ color: 'var(--nominal)' }} />
            <span>
              Nenhuma coluna ultrapassa o limite de {MISSING_ALERT_THRESHOLD_PCT}% de dados faltantes neste escopo.
            </span>
          </div>
        )}

        <div className="data-grid-wrap">
          <table className="data-grid">
            <thead>
              <tr>
                <th>Coluna</th>
                <th className="num">Válidos</th>
                <th className="num">Faltantes (Nulo / NaN)</th>
                <th className="num">% Faltante</th>
                <th style={{ minWidth: '170px' }}>Proporção de lacunas</th>
                <th>Situação</th>
              </tr>
            </thead>
            <tbody>
              {missingByColumn.map((col) => {
                const isCritical = col.exceedsThreshold;
                const hasMinorGaps = !isCritical && col.missingCount > 0;
                const pctColor = isCritical
                  ? 'var(--danger)'
                  : hasMinorGaps
                    ? 'var(--warning)'
                    : 'var(--nominal)';
                const barWidth = Math.min(100, Math.max(col.missingPct > 0 ? 1.5 : 0, col.missingPct));

                return (
                  <tr
                    key={`${col.source}_${col.key}`}
                    style={
                      isCritical
                        ? { backgroundColor: 'rgba(239, 68, 68, 0.08)' }
                        : undefined
                    }
                  >
                    <td>
                      <div className="flex items-center gap-2">
                        {isCritical && (
                          <AlertTriangle
                            size={14}
                            className="shrink-0"
                            style={{ color: 'var(--danger)' }}
                          />
                        )}
                        <div>
                          <div
                            className="font-medium leading-tight"
                            style={{ color: isCritical ? 'var(--danger)' : 'var(--text-primary)' }}
                          >
                            {col.label}
                          </div>
                          <div
                            className="font-mono-tabular text-[0.73rem] leading-tight mt-0.5"
                            style={{ color: 'var(--text-muted)' }}
                          >
                            {col.key}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="num">{brNumber(col.validCount, 0)}</td>
                    <td
                      className="num font-medium"
                      style={{
                        color: col.missingCount > 0 ? pctColor : 'var(--text-secondary)',
                      }}
                    >
                      {brNumber(col.missingCount, 0)}
                    </td>
                    <td className="num font-semibold" style={{ color: pctColor }}>
                      {brNumber(col.missingPct, 2)}%
                    </td>
                    <td>
                      <div
                        className="relative h-2 w-full rounded-sm overflow-hidden"
                        style={{ backgroundColor: 'var(--bg-subtle)' }}
                        title={`${brNumber(col.missingPct, 2)}% faltantes (referência: 10%)`}
                      >
                        <div
                          className="h-full transition-all duration-200"
                          style={{
                            width: `${barWidth}%`,
                            backgroundColor: pctColor,
                          }}
                        />
                        <div
                          className="absolute top-0 bottom-0 w-px"
                          style={{
                            left: `${MISSING_ALERT_THRESHOLD_PCT}%`,
                            backgroundColor: 'var(--border-strong)',
                          }}
                          aria-hidden="true"
                        />
                      </div>
                    </td>
                    <td>
                      <span
                        className="inline-flex items-center gap-1.5 text-[0.8rem] font-medium"
                        style={{ color: pctColor }}
                      >
                        {isCritical
                          ? 'Crítico (> 10%)'
                          : hasMinorGaps
                            ? 'Lacunas leves (≤ 10%)'
                            : 'Completa'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Climatological Threshold Monitoring (Standard Deviation / Z-Score) */}
      <div className="surface-panel p-5 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="m-0 text-[1rem] font-semibold">
              Monitoramento de Limites Climatológicos (Desvio Padrão)
            </h2>
            <p className="mt-1 mb-0 text-[0.8rem]" style={{ color: 'var(--text-muted)' }}>
              Detecta registros horários fora da faixa histórica (μ ±{' '}
              <span className="font-mono-tabular">{brNumber(sigmaThreshold, 1)}σ</span>) calculada sobre a série completa da estação
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="segmented-track" role="group" aria-label="Sensibilidade em desvios padrão">
              {[1.5, 2, 2.5, 3].map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => {
                    setSigmaThreshold(k);
                    setAlertPage(0);
                  }}
                  className={`segmented-item font-mono-tabular ${
                    sigmaThreshold === k ? 'segmented-item-active' : ''
                  }`}
                >
                  {brNumber(k, 1)}σ
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Historical Baseline Reference Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="surface-subtle px-4 py-3 space-y-1">
            <div className="flex items-center justify-between text-[0.75rem]">
              <span className="font-medium" style={{ color: 'var(--text-muted)' }}>
                Temp. Máxima (μ ± {brNumber(sigmaThreshold, 1)}σ)
              </span>
              <span
                className="font-mono-tabular font-semibold"
                style={{ color: monitor.countsByVar.tempMax > 0 ? 'var(--warning)' : 'var(--nominal)' }}
              >
                {brNumber(monitor.countsByVar.tempMax, 0)} alertas
              </span>
            </div>
            <div className="font-mono-tabular text-[0.95rem] font-semibold" style={{ color: 'var(--text-primary)' }}>
              {brNumber(monitor.baselines.tempMax.low)} a {brNumber(monitor.baselines.tempMax.high)} °C
            </div>
            <div className="font-mono-tabular text-[0.73rem]" style={{ color: 'var(--text-muted)' }}>
              μ = {brNumber(monitor.baselines.tempMax.mean)} °C · σ = {brNumber(monitor.baselines.tempMax.std)} °C
            </div>
          </div>

          <div className="surface-subtle px-4 py-3 space-y-1">
            <div className="flex items-center justify-between text-[0.75rem]">
              <span className="font-medium" style={{ color: 'var(--text-muted)' }}>
                Temp. Mínima (μ ± {brNumber(sigmaThreshold, 1)}σ)
              </span>
              <span
                className="font-mono-tabular font-semibold"
                style={{ color: monitor.countsByVar.tempMin > 0 ? 'var(--warning)' : 'var(--nominal)' }}
              >
                {brNumber(monitor.countsByVar.tempMin, 0)} alertas
              </span>
            </div>
            <div className="font-mono-tabular text-[0.95rem] font-semibold" style={{ color: 'var(--text-primary)' }}>
              {brNumber(monitor.baselines.tempMin.low)} a {brNumber(monitor.baselines.tempMin.high)} °C
            </div>
            <div className="font-mono-tabular text-[0.73rem]" style={{ color: 'var(--text-muted)' }}>
              μ = {brNumber(monitor.baselines.tempMin.mean)} °C · σ = {brNumber(monitor.baselines.tempMin.std)} °C
            </div>
          </div>

          <div className="surface-subtle px-4 py-3 space-y-1">
            <div className="flex items-center justify-between text-[0.75rem]">
              <span className="font-medium" style={{ color: 'var(--text-muted)' }}>
                Chuva &gt; 0 mm (μ + {brNumber(sigmaThreshold, 1)}σ)
              </span>
              <span
                className="font-mono-tabular font-semibold"
                style={{ color: monitor.countsByVar.rain > 0 ? 'var(--danger)' : 'var(--nominal)' }}
              >
                {brNumber(monitor.countsByVar.rain, 0)} alertas
              </span>
            </div>
            <div className="font-mono-tabular text-[0.95rem] font-semibold" style={{ color: 'var(--text-primary)' }}>
              Limite superior: {brNumber(monitor.baselines.rain.high)} mm/h
            </div>
            <div className="font-mono-tabular text-[0.73rem]" style={{ color: 'var(--text-muted)' }}>
              μ = {brNumber(monitor.baselines.rain.mean)} mm · σ = {brNumber(monitor.baselines.rain.std)} mm
            </div>
          </div>
        </div>

        {/* Filter & Sort Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="segmented-track" role="group" aria-label="Filtrar alertas por variável">
            <button
              type="button"
              onClick={() => {
                setAlertVarFilter('all');
                setAlertPage(0);
              }}
              className={`segmented-item ${alertVarFilter === 'all' ? 'segmented-item-active' : ''}`}
            >
              Todos ({brNumber(monitor.alertCount, 0)})
            </button>
            <button
              type="button"
              onClick={() => {
                setAlertVarFilter('rain');
                setAlertPage(0);
              }}
              className={`segmented-item ${alertVarFilter === 'rain' ? 'segmented-item-active' : ''}`}
            >
              Chuva ({brNumber(monitor.countsByVar.rain, 0)})
            </button>
            <button
              type="button"
              onClick={() => {
                setAlertVarFilter('tempMax');
                setAlertPage(0);
              }}
              className={`segmented-item ${alertVarFilter === 'tempMax' ? 'segmented-item-active' : ''}`}
            >
              Temp. Máx. ({brNumber(monitor.countsByVar.tempMax, 0)})
            </button>
            <button
              type="button"
              onClick={() => {
                setAlertVarFilter('tempMin');
                setAlertPage(0);
              }}
              className={`segmented-item ${alertVarFilter === 'tempMin' ? 'segmented-item-active' : ''}`}
            >
              Temp. Mín. ({brNumber(monitor.countsByVar.tempMin, 0)})
            </button>
          </div>

          <div className="segmented-track" role="group" aria-label="Ordenação de alertas">
            <button
              type="button"
              onClick={() => {
                setAlertSort('severity');
                setAlertPage(0);
              }}
              className={`segmented-item ${alertSort === 'severity' ? 'segmented-item-active' : ''}`}
            >
              Maior desvio (|z|)
            </button>
            <button
              type="button"
              onClick={() => {
                setAlertSort('time');
                setAlertPage(0);
              }}
              className={`segmented-item ${alertSort === 'time' ? 'segmented-item-active' : ''}`}
            >
              Mais recente
            </button>
          </div>
        </div>

        {/* Records Table with Inline Alert Badges */}
        {displayedAlerts.length === 0 ? (
          <div
            className="flex items-center gap-2 text-[0.83rem] py-2"
            style={{ color: 'var(--text-secondary)' }}
          >
            <CheckCircle2 size={15} className="shrink-0" style={{ color: 'var(--nominal)' }} />
            <span>
              Nenhum registro ultrapassa o limite climatológico de ±{brNumber(sigmaThreshold, 1)}σ para este filtro.
            </span>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="data-grid-wrap">
              <table className="data-grid">
                <thead>
                  <tr>
                    <th>Data e hora</th>
                    <th className="num">Chuva (mm)</th>
                    <th className="num">Temp. máx. (°C)</th>
                    <th className="num">Temp. mín. (°C)</th>
                    <th className="num">Pico z-score</th>
                    <th>Notificação de alerta</th>
                  </tr>
                </thead>
                <tbody>
                  {alertSlice.map((item) => {
                    const rainFlag = item.flags.find((f) => f.variable === 'rain');
                    const maxFlag = item.flags.find((f) => f.variable === 'tempMax');
                    const minFlag = item.flags.find((f) => f.variable === 'tempMin');
                    const isCritical = item.severity === 'critico';

                    return (
                      <tr
                        key={item.record.id}
                        style={
                          isCritical
                            ? { backgroundColor: 'rgba(239, 68, 68, 0.06)' }
                            : undefined
                        }
                      >
                        <td className="font-mono-tabular" style={{ color: 'var(--text-secondary)' }}>
                          {formatDateTimeBR(item.record.data_hora)}
                        </td>
                        <td
                          className={`num ${rainFlag ? 'font-semibold' : ''}`}
                          style={
                            rainFlag
                              ? { color: rainFlag.severity === 'critico' ? 'var(--danger)' : 'var(--warning)' }
                              : undefined
                          }
                        >
                          {brNumber(item.record.precipitacao_mm)}
                        </td>
                        <td
                          className={`num ${maxFlag ? 'font-semibold' : ''}`}
                          style={
                            maxFlag
                              ? { color: maxFlag.severity === 'critico' ? 'var(--danger)' : 'var(--warning)' }
                              : undefined
                          }
                        >
                          {brNumber(item.record.temp_max_c)}
                        </td>
                        <td
                          className={`num ${minFlag ? 'font-semibold' : ''}`}
                          style={
                            minFlag
                              ? { color: minFlag.severity === 'critico' ? 'var(--danger)' : 'var(--warning)' }
                              : undefined
                          }
                        >
                          {brNumber(item.record.temp_min_c)}
                        </td>
                        <td
                          className="num font-semibold"
                          style={{ color: isCritical ? 'var(--danger)' : 'var(--warning)' }}
                        >
                          {item.signedPeakZ >= 0 ? '+' : ''}
                          {brNumber(item.signedPeakZ, 2)}σ
                        </td>
                        <td>
                          <div className="flex flex-wrap items-center gap-1.5">
                            {item.flags.map((flag) => {
                              const crit = flag.severity === 'critico';
                              return (
                                <span
                                  key={`${item.record.id}_${flag.variable}`}
                                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[0.73rem] font-semibold whitespace-nowrap"
                                  style={{
                                    backgroundColor: crit
                                      ? 'rgba(239, 68, 68, 0.14)'
                                      : 'rgba(245, 158, 11, 0.14)',
                                    border: `1px solid ${
                                      crit
                                        ? 'rgba(239, 68, 68, 0.38)'
                                        : 'rgba(245, 158, 11, 0.38)'
                                    }`,
                                    color: crit ? 'var(--danger)' : 'var(--warning)',
                                  }}
                                  title={`Desvio de ${flag.zScore >= 0 ? '+' : ''}${brNumber(flag.zScore, 2)} desvios padrão em relação à média histórica`}
                                >
                                  <AlertTriangle size={11} className="shrink-0" />
                                  <span>{flag.label}</span>
                                  <span className="font-mono-tabular opacity-90">
                                    ({flag.zScore >= 0 ? '+' : ''}
                                    {brNumber(flag.zScore, 1)}σ)
                                  </span>
                                </span>
                              );
                            })}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {totalAlertPages > 1 && (
              <div className="flex flex-wrap items-center justify-between gap-3 text-[0.8rem]">
                <span className="font-mono-tabular" style={{ color: 'var(--text-muted)' }}>
                  Exibindo {brNumber(safeAlertPage * alertsPerPage + 1, 0)}–
                  {brNumber(Math.min((safeAlertPage + 1) * alertsPerPage, displayedAlerts.length), 0)}{' '}
                  de {brNumber(displayedAlerts.length, 0)} registros fora do limite ·{' '}
                  {brNumber(monitor.criticalCount, 0)} críticos (≥ {brNumber(sigmaThreshold + 1, 1)}σ)
                </span>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setAlertPage((p) => Math.max(0, p - 1))}
                    disabled={safeAlertPage === 0}
                    className="btn-secondary py-1 px-2.5 text-[0.78rem]"
                  >
                    <ChevronLeft size={14} />
                    <span>Anterior</span>
                  </button>
                  <span className="font-mono-tabular px-1.5" style={{ color: 'var(--text-muted)' }}>
                    {safeAlertPage + 1} / {totalAlertPages}
                  </span>
                  <button
                    type="button"
                    onClick={() => setAlertPage((p) => Math.min(totalAlertPages - 1, p + 1))}
                    disabled={safeAlertPage >= totalAlertPages - 1}
                    className="btn-secondary py-1 px-2.5 text-[0.78rem]"
                  >
                    <span>Próxima</span>
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Monthly Summary + Data Quality */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-7 space-y-3">
          <h3 className="m-0 text-[1rem] font-semibold">Resumo Mensal</h3>
          <div className="data-grid-wrap">
            <table className="data-grid">
              <thead>
                <tr>
                  <th>Mês</th>
                  <th className="num">Registros</th>
                  <th className="num">Chuva (mm)</th>
                  <th className="num">Máx. média (°C)</th>
                  <th className="num">Mín. média (°C)</th>
                  <th className="num">Horas c/ chuva</th>
                </tr>
              </thead>
              <tbody>
                {mensal.map((m) => (
                  <tr key={m.mes}>
                    <td className="font-medium">{m.mes_nome}</td>
                    <td className="num">{brNumber(m.registros, 0)}</td>
                    <td className="num font-semibold">{brNumber(m.precipitacao_mm)}</td>
                    <td className="num">{brNumber(m.temp_max_media)}</td>
                    <td className="num">{brNumber(m.temp_min_media)}</td>
                    <td className="num">{brNumber(m.horas_com_chuva, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="lg:col-span-5 space-y-3">
          <h3 className="m-0 text-[1rem] font-semibold">Auditoria de Qualidade (Base Completa)</h3>
          <div className="data-grid-wrap">
            <table className="data-grid">
              <thead>
                <tr>
                  <th>Indicador de integridade</th>
                  <th className="num">Ocorrências</th>
                </tr>
              </thead>
              <tbody>
                {qualityRows.map((row) => (
                  <tr key={row.indicador}>
                    <td>{row.indicador}</td>
                    <td
                      className="num font-semibold"
                      style={{
                        color: row.warn ? 'var(--warning)' : 'var(--text-primary)',
                      }}
                    >
                      {brNumber(row.valor, 0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ============================================================================
   TAB 4: GRÁFICOS E CORRELAÇÃO
   ============================================================================ */
export const ChartsTab: React.FC<{
  filtered: WeatherRecord[];
  isDark: boolean;
}> = ({ filtered, isDark }) => {
  const [granularity, setGranularity] = useState<'month' | 'day'>('month');
  const [selectedMonth, setSelectedMonth] = useState<string>('todos');

  const availableMonths = useMemo(() => {
    const s = new Set<number>();
    filtered.forEach((r) => s.add(r.mes));
    return Array.from(s).sort((a, b) => a - b);
  }, [filtered]);

  const chartData = useMemo(() => {
    if (granularity === 'month') {
      return monthlySummary(filtered).map((m) => ({
        label: m.mes_nome,
        precipitacao_mm: Math.round(m.precipitacao_mm * 10) / 10,
        temp_max_media: m.temp_max_media !== null ? Math.round(m.temp_max_media * 10) / 10 : null,
        temp_min_media: m.temp_min_media !== null ? Math.round(m.temp_min_media * 10) / 10 : null,
      }));
    }
    const daily = dailySummary(filtered);
    const filteredDaily =
      selectedMonth === 'todos' ? daily : daily.filter((d) => String(d.mes) === selectedMonth);
    return filteredDaily.map((d) => ({
      label: d.label,
      precipitacao_mm: Math.round(d.precipitacao_mm * 10) / 10,
      temp_max_media: d.temp_max_media !== null ? Math.round(d.temp_max_media * 10) / 10 : null,
      temp_min_media: d.temp_min_media !== null ? Math.round(d.temp_min_media * 10) / 10 : null,
    }));
  }, [filtered, granularity, selectedMonth]);

  const corr = useMemo(() => correlationMatrix(filtered), [filtered]);

  if (filtered.length === 0) {
    return (
      <div className="surface-panel p-6 text-[0.88rem]" style={{ color: 'var(--text-secondary)' }}>
        Nenhum dado disponível para os filtros atuais.
      </div>
    );
  }

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

  const corrCellBg = (val: number | null): string => {
    if (val === null) return isDark ? '#141B2B' : '#F1F5F9';
    if (val >= 0) {
      const alpha = 0.18 + Math.min(1, val) * 0.68;
      return `rgba(239, 68, 68, ${alpha.toFixed(2)})`;
    }
    const alpha = 0.18 + Math.min(1, Math.abs(val)) * 0.68;
    return `rgba(14, 165, 233, ${alpha.toFixed(2)})`;
  };

  return (
    <div className="space-y-6">
      <div className="surface-panel px-5 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="m-0 text-[1.05rem] font-semibold">Séries Temporais e Tendências</h2>
          <p className="mt-0.5 mb-0 text-[0.8rem]" style={{ color: 'var(--text-muted)' }}>
            Alterne a granularidade entre visão mensal e detalhamento diário.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="segmented-track">
            <button
              type="button"
              onClick={() => setGranularity('month')}
              className={`segmented-item ${granularity === 'month' ? 'segmented-item-active' : ''}`}
            >
              Por mês
            </button>
            <button
              type="button"
              onClick={() => setGranularity('day')}
              className={`segmented-item ${granularity === 'day' ? 'segmented-item-active' : ''}`}
            >
              Por dia
            </button>
          </div>

          {granularity === 'day' && (
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="field-input w-auto py-1.5 text-[0.82rem]"
              aria-label="Filtrar mês"
            >
              <option value="todos">Todos os meses</option>
              {availableMonths.map((m) => (
                <option key={m} value={String(m)}>
                  {MESES_PT[m] || String(m)}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {chartData.length === 0 ? (
        <div className="surface-subtle p-6 text-center text-[0.86rem]" style={{ color: 'var(--text-muted)' }}>
          Sem registros para a seleção atual.
        </div>
      ) : (
        <>
          <div className="surface-panel p-5 space-y-3">
            <h3 className="m-0 text-[0.98rem] font-semibold">Precipitação Acumulada (mm)</h3>
            <div className="w-full h-[330px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 14, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} unit="mm" />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar
                    dataKey="precipitacao_mm"
                    name="Chuva (mm)"
                    fill={isDark ? '#0EA5E9' : '#0284C7'}
                    radius={[3, 3, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="surface-panel p-5 space-y-3">
            <h3 className="m-0 text-[0.98rem] font-semibold">Amplitude Térmica Média (°C)</h3>
            <div className="w-full h-[340px]">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 8, right: 14, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: chartAxis, fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} unit="°" />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                  <Area
                    type="monotone"
                    dataKey="temp_max_media"
                    name="Temp. máxima média (°C)"
                    stroke="#F59E0B"
                    fill="rgba(245, 158, 11, 0.12)"
                    strokeWidth={2.4}
                  />
                  <Line
                    type="monotone"
                    dataKey="temp_min_media"
                    name="Temp. mínima média (°C)"
                    stroke={isDark ? '#38BDF8' : '#0284C7'}
                    strokeWidth={2.4}
                    dot={{ r: 3, strokeWidth: 0, fill: isDark ? '#38BDF8' : '#0284C7' }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="surface-panel p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="m-0 text-[0.98rem] font-semibold">Matriz de Correlação de Pearson</h3>
                <p className="mt-0.5 mb-0 text-[0.8rem]" style={{ color: 'var(--text-muted)' }}>
                  Coeficiente r variando de -1,00 (inversa) a +1,00 (direta).
                </p>
              </div>
              <div className="flex items-center gap-2 text-[0.74rem] font-mono-tabular" style={{ color: 'var(--text-muted)' }}>
                <span>-1.0</span>
                <div
                  className="w-28 h-2.5 rounded-sm"
                  style={{
                    background: 'linear-gradient(90deg, rgba(14,165,233,0.85), rgba(148,163,184,0.2), rgba(239,68,68,0.85))',
                  }}
                />
                <span>+1.0</span>
              </div>
            </div>

            <div className="max-w-[520px] mx-auto pt-1">
              <div className="grid grid-cols-4 gap-1.5 text-center text-[0.82rem]">
                <div />
                {corr.labels.map((col) => (
                  <div key={col} className="font-medium py-2" style={{ color: 'var(--text-muted)' }}>
                    {col}
                  </div>
                ))}
                {corr.labels.map((rowLabel, i) => (
                  <React.Fragment key={rowLabel}>
                    <div
                      className="font-medium flex items-center justify-end pr-3"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {rowLabel}
                    </div>
                    {corr.values[i].map((val, j) => (
                      <div
                        key={`${i}-${j}`}
                        className="rounded-md py-5 font-mono-tabular font-semibold text-[0.92rem]"
                        style={{
                          backgroundColor: corrCellBg(val),
                          color: '#FFFFFF',
                          textShadow: '0 1px 2px rgba(0, 0, 0, 0.35)',
                        }}
                      >
                        {val !== null ? val.toFixed(2) : '-'}
                      </div>
                    ))}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

/* ============================================================================
   TAB 5: TABELA EDITÁVEL
   ============================================================================ */
export const EditableTableTab: React.FC<{
  records: WeatherRecord[];
  onSaveEdits: (updated: WeatherRecord[]) => void;
}> = ({ records, onSaveEdits }) => {
  const PAGE_SIZE = 50;
  const [page, setPage] = useState(0);
  const [drafts, setDrafts] = useState<
    Record<number, { precipitacao_mm?: string; temp_max_c?: string; temp_min_c?: string }>
  >({});
  const [savedBanner, setSavedBanner] = useState(false);

  const totalPages = Math.max(1, Math.ceil(records.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const slice = records.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  const updateCell = (id: number, field: 'precipitacao_mm' | 'temp_max_c' | 'temp_min_c', value: string) => {
    setSavedBanner(false);
    setDrafts((prev) => ({
      ...prev,
      [id]: {
        ...prev[id],
        [field]: value,
      },
    }));
  };

  const handleSave = () => {
    const editedIds = Object.keys(drafts);
    if (editedIds.length === 0) {
      setSavedBanner(true);
      return;
    }
    const next = records.map((row) => {
      const d = drafts[row.id];
      if (!d) return row;
      const parseNum = (str: string | undefined, fallback: number | null) => {
        if (str === undefined) return fallback;
        const clean = str.trim().replace(',', '.');
        if (clean === '') return null;
        const n = Number(clean);
        return Number.isFinite(n) ? n : fallback;
      };
      const rain = parseNum(d.precipitacao_mm, row.precipitacao_mm);
      return {
        ...row,
        precipitacao_mm: rain !== null ? Math.max(0, rain) : null,
        temp_max_c: parseNum(d.temp_max_c, row.temp_max_c),
        temp_min_c: parseNum(d.temp_min_c, row.temp_min_c),
      };
    });
    onSaveEdits(next);
    setDrafts({});
    setSavedBanner(true);
  };

  const pendingCount = Object.keys(drafts).length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="m-0 text-[1.05rem] font-semibold">Editor de Medições em Sessão</h2>
          <p className="mt-0.5 mb-0 text-[0.82rem]" style={{ color: 'var(--text-muted)' }}>
            Corrija valores pontuais de precipitação ou temperatura e salve para recalcular KPIs e gráficos.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {savedBanner && (
            <span className="inline-flex items-center gap-1.5 text-[0.82rem] font-medium" style={{ color: 'var(--nominal)' }}>
              <CheckCircle2 size={15} />
              Alterações salvas
            </span>
          )}
          <button type="button" onClick={handleSave} className="btn-primary text-[0.82rem]">
            <Save size={14} />
            <span>Salvar edições{pendingCount > 0 ? ` (${pendingCount})` : ''}</span>
          </button>
        </div>
      </div>

      <div className="data-grid-wrap max-h-[520px]">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Data e hora</th>
              <th>Chuva (mm)</th>
              <th>Temp. máx. (°C)</th>
              <th>Temp. mín. (°C)</th>
            </tr>
          </thead>
          <tbody>
            {slice.map((row) => {
              const d = drafts[row.id];
              const rainVal = d?.precipitacao_mm ?? (row.precipitacao_mm !== null ? String(row.precipitacao_mm) : '');
              const maxVal = d?.temp_max_c ?? (row.temp_max_c !== null ? String(row.temp_max_c) : '');
              const minVal = d?.temp_min_c ?? (row.temp_min_c !== null ? String(row.temp_min_c) : '');
              return (
                <tr key={row.id}>
                  <td className="font-mono-tabular text-[0.82rem]" style={{ color: 'var(--text-secondary)' }}>
                    {formatDateTimeBR(row.data_hora)}
                  </td>
                  <td>
                    <input
                      type="number"
                      min={0}
                      step={0.1}
                      value={rainVal}
                      onChange={(e) => updateCell(row.id, 'precipitacao_mm', e.target.value)}
                      className="field-input font-mono-tabular py-1 px-2.5 w-28 text-[0.82rem]"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step={0.1}
                      value={maxVal}
                      onChange={(e) => updateCell(row.id, 'temp_max_c', e.target.value)}
                      className="field-input font-mono-tabular py-1 px-2.5 w-28 text-[0.82rem]"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step={0.1}
                      value={minVal}
                      onChange={(e) => updateCell(row.id, 'temp_min_c', e.target.value)}
                      className="field-input font-mono-tabular py-1 px-2.5 w-28 text-[0.82rem]"
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-[0.82rem]" style={{ color: 'var(--text-muted)' }}>
        <span className="font-mono-tabular">
          Página {safePage + 1} de {totalPages} · {brNumber(records.length, 0)} registros totais
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={safePage === 0}
            className="btn-secondary py-1.5 px-3 text-[0.8rem]"
          >
            <ChevronLeft size={14} />
            <span>Anterior</span>
          </button>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={safePage >= totalPages - 1}
            className="btn-secondary py-1.5 px-3 text-[0.8rem]"
          >
            <span>Próxima</span>
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};

/* ============================================================================
   TAB 6: EXPLORADOR
   ============================================================================ */
export const ExplorerTab: React.FC<{ filtered: WeatherRecord[] }> = ({ filtered }) => {
  const PAGE_SIZE = 100;
  const [page, setPage] = useState(0);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const slice = filtered.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="m-0 text-[1.05rem] font-semibold">Explorador de Medições</h2>
          <p className="mt-0.5 mb-0 text-[0.82rem] font-mono-tabular" style={{ color: 'var(--text-muted)' }}>
            {brNumber(filtered.length, 0)} registros correspondem aos filtros ativos.
          </p>
        </div>

        <div className="flex items-center gap-2 text-[0.82rem]">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={safePage === 0}
            className="btn-secondary py-1.5 px-3 text-[0.8rem]"
          >
            <ChevronLeft size={14} />
            <span>Anterior</span>
          </button>
          <span className="font-mono-tabular px-2" style={{ color: 'var(--text-muted)' }}>
            {safePage + 1} / {totalPages}
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={safePage >= totalPages - 1}
            className="btn-secondary py-1.5 px-3 text-[0.8rem]"
          >
            <span>Próxima</span>
            <ChevronRight size={14} />
          </button>
        </div>
      </div>

      <div className="data-grid-wrap max-h-[540px]">
        <table className="data-grid">
          <thead>
            <tr>
              <th>Data e hora</th>
              <th className="num">Chuva (mm)</th>
              <th className="num">Temp. máx. (°C)</th>
              <th className="num">Temp. mín. (°C)</th>
            </tr>
          </thead>
          <tbody>
            {slice.map((row) => (
              <tr key={row.id}>
                <td className="font-mono-tabular" style={{ color: 'var(--text-secondary)' }}>
                  {formatDateTimeBR(row.data_hora)}
                </td>
                <td className="num">{brNumber(row.precipitacao_mm)}</td>
                <td className="num">{brNumber(row.temp_max_c)}</td>
                <td className="num">{brNumber(row.temp_min_c)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

/* ============================================================================
   TAB 7: EXPORTAR
   ============================================================================ */
export const ExportTab: React.FC<{
  dataset: StationDataset;
  fullRecords: WeatherRecord[];
  filtered: WeatherRecord[];
  filterSpec: FilterSpec;
  onSaveExportCopy: (filename: string, csvText: string) => void;
}> = ({ dataset, fullRecords, filtered, filterSpec, onSaveExportCopy }) => {
  const [scope, setScope] = useState<'full' | 'filtered'>('full');
  const [savedNotice, setSavedNotice] = useState<string | null>(null);
  const [pdfNotice, setPdfNotice] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [generatingPdf, setGeneratingPdf] = useState(false);

  const [includeSummary, setIncludeSummary] = useState(true);
  const [includeMonthlyChart, setIncludeMonthlyChart] = useState(true);
  const [includeHistogram, setIncludeHistogram] = useState(true);
  const [includeQualityAndCorr, setIncludeQualityAndCorr] = useState(true);

  const targetRecords = scope === 'full' ? fullRecords : filtered;
  const hasAnyPdfSection =
    includeSummary || includeMonthlyChart || includeHistogram || includeQualityAndCorr;

  const handleDownloadCsv = () => {
    const stamp = getStamp();
    const csv = buildCsvExport(targetRecords);
    triggerDownload(csv, `climaps_dados_${stamp}.csv`, 'text/csv;charset=utf-8;');
  };

  const handleDownloadSql = () => {
    const stamp = getStamp();
    const sql = buildSqlScript(targetRecords);
    triggerDownload(sql, `climaps_dados_${stamp}.sql`, 'application/sql;charset=utf-8;');
  };

  const handleSaveCopy = () => {
    const stamp = getStamp();
    const filename = `dados_editados_${stamp}.csv`;
    const csv = buildCsvExport(targetRecords);
    onSaveExportCopy(filename, csv);
    setSavedNotice(`Cópia salva na sessão em exportacoes/${filename}`);
  };

  const handleGeneratePdf = () => {
    if (targetRecords.length === 0 || !hasAnyPdfSection) return;
    setGeneratingPdf(true);
    setPdfError(null);
    setPdfNotice(null);
    try {
      const filename = generateStructuredPdfReport({
        dataset,
        fullRecords,
        targetRecords,
        filterSpec,
        options: {
          scope,
          includeSummary,
          includeMonthlyChart,
          includeHistogram,
          includeQualityAndCorr,
        },
      });
      setPdfNotice(`Relatório gerado: ${filename}`);
    } catch (err) {
      setPdfError(
        err instanceof Error ? err.message : 'Não foi possível gerar o relatório em PDF.'
      );
    } finally {
      setGeneratingPdf(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      {/* Shared Scope Control */}
      <div className="surface-panel px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="m-0 text-[1rem] font-semibold">Escopo da Exportação</h2>
          <p className="mt-0.5 mb-0 text-[0.8rem]" style={{ color: 'var(--text-muted)' }}>
            Aplicado tanto ao relatório em PDF quanto aos arquivos CSV e SQL.
          </p>
        </div>
        <div className="segmented-track" role="group" aria-label="Escopo da exportação">
          <button
            type="button"
            onClick={() => setScope('full')}
            className={`segmented-item ${scope === 'full' ? 'segmented-item-active' : ''}`}
          >
            Base completa ({brNumber(fullRecords.length, 0)})
          </button>
          <button
            type="button"
            onClick={() => setScope('filtered')}
            className={`segmented-item ${scope === 'filtered' ? 'segmented-item-active' : ''}`}
          >
            Recorte filtrado ({brNumber(filtered.length, 0)})
          </button>
        </div>
      </div>

      {/* Structured PDF Report Panel */}
      <div className="surface-panel p-6 space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="m-0 text-[1.1rem] font-semibold">Relatório Estruturado em PDF</h2>
            <p className="mt-1 mb-0 text-[0.84rem]" style={{ color: 'var(--text-muted)' }}>
              Compila um documento A4 pronto para compartilhamento com KPIs, destaques, gráficos em alta resolução, auditoria de lacunas (&gt; 10%) e correlação de Pearson.
            </p>
          </div>
          <span className="font-mono-tabular text-[0.76rem]" style={{ color: 'var(--text-muted)' }}>
            Formato A4 · {brNumber(targetRecords.length, 0)} registros
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label className="surface-subtle px-4 py-3 flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={includeSummary}
              onChange={(e) => setIncludeSummary(e.target.checked)}
              className="mt-0.5 w-4 h-4 accent-sky-500 rounded"
            />
            <div>
              <div className="text-[0.85rem] font-medium" style={{ color: 'var(--text-primary)' }}>
                Resumo executivo, KPIs e tabela mensal
              </div>
              <div className="text-[0.76rem]" style={{ color: 'var(--text-muted)' }}>
                Indicadores principais, destaques automáticos e consolidado mês a mês
              </div>
            </div>
          </label>

          <label className="surface-subtle px-4 py-3 flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={includeMonthlyChart}
              onChange={(e) => setIncludeMonthlyChart(e.target.checked)}
              className="mt-0.5 w-4 h-4 accent-sky-500 rounded"
            />
            <div>
              <div className="text-[0.85rem] font-medium" style={{ color: 'var(--text-primary)' }}>
                Gráfico mensal de chuva e temperaturas
              </div>
              <div className="text-[0.76rem]" style={{ color: 'var(--text-muted)' }}>
                Barras de precipitação acumulada com curvas médias de máx. e mín.
              </div>
            </div>
          </label>

          <label className="surface-subtle px-4 py-3 flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={includeHistogram}
              onChange={(e) => setIncludeHistogram(e.target.checked)}
              className="mt-0.5 w-4 h-4 accent-sky-500 rounded"
            />
            <div>
              <div className="text-[0.85rem] font-medium" style={{ color: 'var(--text-primary)' }}>
                Histograma de precipitação e extremos
              </div>
              <div className="text-[0.76rem]" style={{ color: 'var(--text-muted)' }}>
                Densidade horária (&gt; 0 mm) destacando eventos acima do limite IQR
              </div>
            </div>
          </label>

          <label className="surface-subtle px-4 py-3 flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={includeQualityAndCorr}
              onChange={(e) => setIncludeQualityAndCorr(e.target.checked)}
              className="mt-0.5 w-4 h-4 accent-sky-500 rounded"
            />
            <div>
              <div className="text-[0.85rem] font-medium" style={{ color: 'var(--text-primary)' }}>
                Qualidade, lacunas por coluna e correlação
              </div>
              <div className="text-[0.76rem]" style={{ color: 'var(--text-muted)' }}>
                Auditoria INMET, colunas acima de 10% faltantes e matriz de Pearson
              </div>
            </div>
          </label>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <button
            type="button"
            onClick={handleGeneratePdf}
            disabled={generatingPdf || targetRecords.length === 0 || !hasAnyPdfSection}
            className="btn-primary py-2.5 px-5"
          >
            <FileText size={15} />
            <span>{generatingPdf ? 'Gerando relatório PDF...' : 'Baixar Relatório PDF'}</span>
          </button>

          {!hasAnyPdfSection && (
            <span className="text-[0.8rem]" style={{ color: 'var(--warning)' }}>
              Selecione ao menos uma seção para gerar o relatório.
            </span>
          )}
        </div>

        {pdfNotice && (
          <div className="flex items-center gap-2 text-[0.84rem] font-medium" style={{ color: 'var(--nominal)' }}>
            <CheckCircle2 size={15} />
            <span>{pdfNotice}</span>
          </div>
        )}

        {pdfError && (
          <div className="flex items-center gap-2 text-[0.84rem] font-medium" style={{ color: 'var(--danger)' }}>
            <AlertTriangle size={15} />
            <span>{pdfError}</span>
          </div>
        )}
      </div>

      {/* Tabular & Database Export Panel */}
      <div className="surface-panel p-6 space-y-5">
        <div>
          <h2 className="m-0 text-[1.1rem] font-semibold">Exportação de Dados Brutos (CSV / SQL)</h2>
          <p className="mt-1 mb-0 text-[0.84rem]" style={{ color: 'var(--text-muted)' }}>
            Gere arquivos CSV normalizados (padrão UTF-8-SIG, separador ponto-e-vírgula) ou script SQL completo com DDL e instruções INSERT.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-1">
          <button
            type="button"
            onClick={handleDownloadCsv}
            disabled={targetRecords.length === 0}
            className="btn-secondary py-2.5"
          >
            <FileSpreadsheet size={15} />
            <span>Baixar CSV normalizado</span>
          </button>
          <button
            type="button"
            onClick={handleDownloadSql}
            disabled={targetRecords.length === 0}
            className="btn-secondary py-2.5"
          >
            <FileCode2 size={15} />
            <span>Baixar Script SQL</span>
          </button>
        </div>

        <div
          className="pt-4 flex flex-wrap items-center justify-between gap-3"
          style={{ borderTop: '1px solid var(--border-hairline)' }}
        >
          <div className="text-[0.82rem]" style={{ color: 'var(--text-muted)' }}>
            Deseja reutilizar esta versão na aba de Comparação de Anos?
          </div>
          <button
            type="button"
            onClick={handleSaveCopy}
            disabled={targetRecords.length === 0}
            className="btn-secondary text-[0.8rem] py-1.5 px-3"
          >
            <FolderPlus size={14} />
            <span>Salvar em exportacoes/</span>
          </button>
        </div>

        {savedNotice && (
          <div className="flex items-center gap-2 text-[0.84rem] font-medium" style={{ color: 'var(--nominal)' }}>
            <CheckCircle2 size={15} />
            <span>{savedNotice}</span>
          </div>
        )}
      </div>
    </div>
  );
};

/* ============================================================================
   EMPTY STATE FOR HISTORICAL TABS
   ============================================================================ */
export const HistoricalEmptyState: React.FC<{
  loadingFile: boolean;
  onLoadSample: () => void;
  onGoToWorld: () => void;
}> = ({ loadingFile, onLoadSample, onGoToWorld }) => (
  <div className="surface-panel p-10 text-center max-w-xl mx-auto my-8 space-y-4">
    <div
      className="w-11 h-11 rounded-xl mx-auto flex items-center justify-center"
      style={{ backgroundColor: 'var(--accent-soft)', color: 'var(--accent-text)' }}
    >
      <Database size={20} />
    </div>
    <div className="space-y-1.5">
      <h2 className="m-0 text-[1.12rem] font-bold">Nenhuma série histórica carregada</h2>
      <p className="m-0 text-[0.86rem] leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        Carregue a estação de exemplo do INMET (Manaus A101 · 2014), importe um arquivo CSV na barra lateral ou baixe 30 dias / 1 ano completo na aba Mundo Ao Vivo.
      </p>
    </div>
    <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
      <button type="button" onClick={onLoadSample} disabled={loadingFile} className="btn-primary">
        <Download size={15} />
        <span>{loadingFile ? 'Carregando base...' : 'Carregar Manaus A101 (2014)'}</span>
      </button>
      <button type="button" onClick={onGoToWorld} className="btn-secondary">
        <span>Ir para Mundo Ao Vivo</span>
      </button>
    </div>
  </div>
);
