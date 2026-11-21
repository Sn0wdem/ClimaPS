import React, { useMemo, useState } from 'react';
import {
  Area,
  Bar,
  BarChart,
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
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Database,
  Download,
  FileCode2,
  FileSpreadsheet,
  FolderPlus,
  Save,
} from 'lucide-react';
import type { WeatherRecord } from '../types/weather';
import {
  MESES_PT,
  calculateKpis,
  correlationMatrix,
  dailySummary,
  generateInsights,
  monthlySummary,
  qualityReport,
} from '../core/analysis';
import { buildCsvExport, buildSqlScript } from '../core/dataLoader';
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
}> = ({ filtered, fullRecords }) => {
  const kpis = useMemo(() => calculateKpis(filtered), [filtered]);
  const insights = useMemo(() => generateInsights(filtered), [filtered]);
  const mensal = useMemo(() => monthlySummary(filtered), [filtered]);
  const report = useMemo(() => qualityReport(fullRecords), [fullRecords]);

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
    { indicador: 'Máxima < Mínima', valor: report.temp_inconsistente, warn: report.temp_inconsistente > 0 },
    { indicador: 'Ausentes em chuva', valor: report.valores_ausentes.precipitacao_mm, warn: report.valores_ausentes.precipitacao_mm > 0 },
    { indicador: 'Ausentes em temp. máx.', valor: report.valores_ausentes.temp_max_c, warn: report.valores_ausentes.temp_max_c > 0 },
    { indicador: 'Ausentes em temp. mín.', valor: report.valores_ausentes.temp_min_c, warn: report.valores_ausentes.temp_min_c > 0 },
    {
      indicador: 'Outliers detectados (IQR)',
      valor:
        report.outliers_iqr.precipitacao_mm +
        report.outliers_iqr.temp_max_c +
        report.outliers_iqr.temp_min_c,
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
  fullRecords: WeatherRecord[];
  filtered: WeatherRecord[];
  onSaveExportCopy: (filename: string, csvText: string) => void;
}> = ({ fullRecords, filtered, onSaveExportCopy }) => {
  const [scope, setScope] = useState<'full' | 'filtered'>('full');
  const [savedNotice, setSavedNotice] = useState<string | null>(null);

  const targetRecords = scope === 'full' ? fullRecords : filtered;

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

  return (
    <div className="max-w-3xl space-y-6">
      <div className="surface-panel p-6 space-y-5">
        <div>
          <h2 className="m-0 text-[1.1rem] font-semibold">Exportação de Dados</h2>
          <p className="mt-1 mb-0 text-[0.84rem]" style={{ color: 'var(--text-muted)' }}>
            Gere arquivos CSV normalizados (padrão UTF-8-SIG, separador ponto-e-vírgula) ou script SQL completo com DDL e instruções INSERT.
          </p>
        </div>

        <div className="space-y-2">
          <div className="text-[0.8rem] font-medium" style={{ color: 'var(--text-muted)' }}>
            Escopo da exportação
          </div>
          <div className="segmented-track">
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

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-1">
          <button type="button" onClick={handleDownloadCsv} className="btn-primary py-2.5">
            <FileSpreadsheet size={15} />
            <span>Baixar CSV normalizado</span>
          </button>
          <button type="button" onClick={handleDownloadSql} className="btn-secondary py-2.5">
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
          <button type="button" onClick={handleSaveCopy} className="btn-secondary text-[0.8rem] py-1.5 px-3">
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
