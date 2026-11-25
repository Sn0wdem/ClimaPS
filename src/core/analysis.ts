import type {
  AirQualityInfo,
  ClimateAnomaly,
  ClimatologicalAlertFlag,
  ClimatologicalAlertRecord,
  ClimatologicalBaselineStat,
  ClimatologicalMonitorResult,
  ColumnMissingStat,
  DailySummaryRow,
  FilterSpec,
  KpiResult,
  LivePointWeather,
  MonthlySummaryRow,
  PrecipitationHistogramBin,
  PrecipitationHistogramResult,
  QualityReport,
  StormRisk,
  UvInfo,
  WeatherRecord,
} from '../types/weather';

export const MESES_PT: Record<number, string> = {
  1: 'Jan',
  2: 'Fev',
  3: 'Mar',
  4: 'Abr',
  5: 'Mai',
  6: 'Jun',
  7: 'Jul',
  8: 'Ago',
  9: 'Set',
  10: 'Out',
  11: 'Nov',
  12: 'Dez',
};

export const MESES_NOMES: string[] = [
  'Janeiro',
  'Fevereiro',
  'Março',
  'Abril',
  'Maio',
  'Junho',
  'Julho',
  'Agosto',
  'Setembro',
  'Outubro',
  'Novembro',
  'Dezembro',
];

export const MESES_EXTENSO: Record<number, string> = {
  1: 'janeiro',
  2: 'fevereiro',
  3: 'março',
  4: 'abril',
  5: 'maio',
  6: 'junho',
  7: 'julho',
  8: 'agosto',
  9: 'setembro',
  10: 'outubro',
  11: 'novembro',
  12: 'dezembro',
};

export function applyFilters(records: WeatherRecord[], spec: FilterSpec): WeatherRecord[] {
  return records.filter((row) => {
    if (spec.start && row.dia < spec.start) return false;
    if (spec.end && row.dia > spec.end) return false;
    if (row.hora_num < spec.hourStart || row.hora_num > spec.hourEnd) return false;
    if (spec.rainyOnly && !(row.precipitacao_mm !== null && row.precipitacao_mm > 0)) return false;
    return true;
  });
}

function mean(values: number[]): number | null {
  if (values.length === 0) return null;
  let sum = 0;
  for (let i = 0; i < values.length; i++) sum += values[i];
  return sum / values.length;
}

export function calculateKpis(records: WeatherRecord[]): KpiResult {
  const totalCells = records.length * 3;
  let validCells = 0;
  let rainSum = 0;
  let tMaxSum = 0;
  let tMaxCount = 0;
  let tMinSum = 0;
  let tMinCount = 0;

  for (let i = 0; i < records.length; i++) {
    const r = records[i];
    if (r.precipitacao_mm !== null && !Number.isNaN(r.precipitacao_mm)) {
      validCells++;
      rainSum += r.precipitacao_mm;
    }
    if (r.temp_max_c !== null && !Number.isNaN(r.temp_max_c)) {
      validCells++;
      tMaxSum += r.temp_max_c;
      tMaxCount++;
    }
    if (r.temp_min_c !== null && !Number.isNaN(r.temp_min_c)) {
      validCells++;
      tMinSum += r.temp_min_c;
      tMinCount++;
    }
  }

  return {
    registros: records.length,
    precipitacao_total: rainSum,
    temp_max_media: tMaxCount > 0 ? tMaxSum / tMaxCount : null,
    temp_min_media: tMinCount > 0 ? tMinSum / tMinCount : null,
    completude: totalCells > 0 ? (100 * validCells) / totalCells : 0,
  };
}

export function monthlySummary(records: WeatherRecord[]): MonthlySummaryRow[] {
  const groups = new Map<
    number,
    {
      registros: number;
      rainSum: number;
      tMaxSum: number;
      tMaxCount: number;
      tMinSum: number;
      tMinCount: number;
      rainyHours: number;
    }
  >();

  for (let i = 0; i < records.length; i++) {
    const r = records[i];
    let g = groups.get(r.mes);
    if (!g) {
      g = { registros: 0, rainSum: 0, tMaxSum: 0, tMaxCount: 0, tMinSum: 0, tMinCount: 0, rainyHours: 0 };
      groups.set(r.mes, g);
    }
    g.registros++;
    if (r.precipitacao_mm !== null && !Number.isNaN(r.precipitacao_mm)) {
      g.rainSum += r.precipitacao_mm;
      if (r.precipitacao_mm > 0) g.rainyHours++;
    }
    if (r.temp_max_c !== null && !Number.isNaN(r.temp_max_c)) {
      g.tMaxSum += r.temp_max_c;
      g.tMaxCount++;
    }
    if (r.temp_min_c !== null && !Number.isNaN(r.temp_min_c)) {
      g.tMinSum += r.temp_min_c;
      g.tMinCount++;
    }
  }

  return Array.from(groups.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([mes, g]) => ({
      mes,
      mes_nome: MESES_PT[mes] || String(mes),
      registros: g.registros,
      precipitacao_mm: g.rainSum,
      temp_max_media: g.tMaxCount > 0 ? g.tMaxSum / g.tMaxCount : null,
      temp_min_media: g.tMinCount > 0 ? g.tMinSum / g.tMinCount : null,
      horas_com_chuva: g.rainyHours,
    }));
}

export function dailySummary(records: WeatherRecord[]): DailySummaryRow[] {
  const groups = new Map<
    string,
    { mes: number; rainSum: number; tMaxSum: number; tMaxCount: number; tMinSum: number; tMinCount: number }
  >();

  for (let i = 0; i < records.length; i++) {
    const r = records[i];
    let g = groups.get(r.dia);
    if (!g) {
      g = { mes: r.mes, rainSum: 0, tMaxSum: 0, tMaxCount: 0, tMinSum: 0, tMinCount: 0 };
      groups.set(r.dia, g);
    }
    if (r.precipitacao_mm !== null && !Number.isNaN(r.precipitacao_mm)) {
      g.rainSum += r.precipitacao_mm;
    }
    if (r.temp_max_c !== null && !Number.isNaN(r.temp_max_c)) {
      g.tMaxSum += r.temp_max_c;
      g.tMaxCount++;
    }
    if (r.temp_min_c !== null && !Number.isNaN(r.temp_min_c)) {
      g.tMinSum += r.temp_min_c;
      g.tMinCount++;
    }
  }

  return Array.from(groups.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([dia, g]) => {
      const parts = dia.split('-');
      const label = parts.length === 3 ? `${parts[2]}/${parts[1]}` : dia;
      return {
        dia,
        label,
        mes: g.mes,
        precipitacao_mm: g.rainSum,
        temp_max_media: g.tMaxCount > 0 ? g.tMaxSum / g.tMaxCount : null,
        temp_min_media: g.tMinCount > 0 ? g.tMinSum / g.tMinCount : null,
      };
    });
}

function quantile(sorted: number[], q: number): number {
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sorted[base + 1] !== undefined) {
    return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
  }
  return sorted[base];
}

export const MAX_HOURLY_RAIN_MM = 150;

function iqrOutlierCount(values: Array<number | null>): number {
  const clean = values.filter((v): v is number => v !== null && !Number.isNaN(v)).sort((a, b) => a - b);
  if (clean.length < 4) return 0;
  const q1 = quantile(clean, 0.25);
  const q3 = quantile(clean, 0.75);
  const iqr = q3 - q1;
  if (iqr === 0) return 0;
  const low = q1 - 1.5 * iqr;
  const high = q3 + 1.5 * iqr;
  return clean.filter((v) => v < low || v > high).length;
}

/**
 * Hourly precipitation is heavily zero-inflated (most hours are 0 mm), which causes
 * standard IQR across all hours to collapse to 0 and misclassify every rainy hour as an outlier.
 * Instead, evaluate the upper Tukey fence strictly across rainy hours (v > 0), falling back
 * to the physical plausibility ceiling when rainy samples are too sparse.
 */
function rainyHourOutlierCount(values: Array<number | null>): number {
  const rainy = values
    .filter((v): v is number => v !== null && !Number.isNaN(v) && v > 0)
    .sort((a, b) => a - b);
  if (rainy.length === 0) return 0;
  if (rainy.length < 4) {
    return rainy.filter((v) => v > MAX_HOURLY_RAIN_MM).length;
  }
  const q1 = quantile(rainy, 0.25);
  const q3 = quantile(rainy, 0.75);
  const iqr = q3 - q1;
  if (iqr === 0) {
    return rainy.filter((v) => v > MAX_HOURLY_RAIN_MM).length;
  }
  const high = q3 + 1.5 * iqr;
  return rainy.filter((v) => v > high).length;
}

export function qualityReport(records: WeatherRecord[]): QualityReport {
  const seenRows = new Set<string>();
  const seenTs = new Set<number>();
  let duplicadas = 0;
  let timestampsDuplicados = 0;
  let chuvaNegativa = 0;
  let chuvaExtremaFisica = 0;
  let tempInconsistente = 0;
  let nullRain = 0;
  let nullMax = 0;
  let nullMin = 0;

  let minTs = Infinity;
  let maxTs = -Infinity;

  const rainVals: Array<number | null> = [];
  const maxVals: Array<number | null> = [];
  const minVals: Array<number | null> = [];

  for (let i = 0; i < records.length; i++) {
    const r = records[i];
    const rowSig = `${r.data_hora}|${r.precipitacao_mm}|${r.temp_max_c}|${r.temp_min_c}`;
    if (seenRows.has(rowSig)) duplicadas++;
    else seenRows.add(rowSig);

    if (seenTs.has(r.timestamp)) timestampsDuplicados++;
    else seenTs.add(r.timestamp);

    if (r.timestamp < minTs) minTs = r.timestamp;
    if (r.timestamp > maxTs) maxTs = r.timestamp;

    if (r.precipitacao_mm === null) nullRain++;
    else {
      if (r.precipitacao_mm < 0) chuvaNegativa++;
      if (r.precipitacao_mm > MAX_HOURLY_RAIN_MM) chuvaExtremaFisica++;
    }

    if (r.temp_max_c === null) nullMax++;
    if (r.temp_min_c === null) nullMin++;
    if (r.temp_max_c !== null && r.temp_min_c !== null && r.temp_max_c < r.temp_min_c) {
      tempInconsistente++;
    }

    rainVals.push(r.precipitacao_mm);
    maxVals.push(r.temp_max_c);
    minVals.push(r.temp_min_c);
  }

  let missingTimestamps = 0;
  if (records.length > 0 && Number.isFinite(minTs) && Number.isFinite(maxTs) && maxTs >= minTs) {
    const hourMs = 3600 * 1000;
    const expectedCount = Math.floor((maxTs - minTs) / hourMs) + 1;
    // Cap sanity check so huge multi-decade gaps don't hang loops
    if (expectedCount <= 200000) {
      for (let ts = minTs; ts <= maxTs; ts += hourMs) {
        if (!seenTs.has(ts)) missingTimestamps++;
      }
    } else {
      missingTimestamps = Math.max(0, expectedCount - seenTs.size);
    }
  }

  return {
    linhas: records.length,
    duplicadas,
    timestamps_duplicados: timestampsDuplicados,
    timestamps_ausentes: missingTimestamps,
    datas_invalidas: 0,
    valores_ausentes: {
      precipitacao_mm: nullRain,
      temp_max_c: nullMax,
      temp_min_c: nullMin,
    },
    outliers_iqr: {
      precipitacao_mm: rainyHourOutlierCount(rainVals),
      temp_max_c: iqrOutlierCount(maxVals),
      temp_min_c: iqrOutlierCount(minVals),
    },
    chuva_negativa: chuvaNegativa,
    chuva_extrema_fisica: chuvaExtremaFisica,
    temp_inconsistente: tempInconsistente,
  };
}

export const MISSING_ALERT_THRESHOLD_PCT = 10;

const CORE_DATASET_COLUMNS: Array<{
  key: keyof WeatherRecord;
  label: string;
  isMissing: (r: WeatherRecord) => boolean;
}> = [
  {
    key: 'precipitacao_mm',
    label: 'Precipitação (mm)',
    isMissing: (r) => r.precipitacao_mm === null || r.precipitacao_mm === undefined || Number.isNaN(r.precipitacao_mm),
  },
  {
    key: 'temp_max_c',
    label: 'Temperatura Máxima (°C)',
    isMissing: (r) => r.temp_max_c === null || r.temp_max_c === undefined || Number.isNaN(r.temp_max_c),
  },
  {
    key: 'temp_min_c',
    label: 'Temperatura Mínima (°C)',
    isMissing: (r) => r.temp_min_c === null || r.temp_min_c === undefined || Number.isNaN(r.temp_min_c),
  },
  {
    key: 'data',
    label: 'Data',
    isMissing: (r) => !r.data || r.data.trim() === '',
  },
  {
    key: 'hora',
    label: 'Hora',
    isMissing: (r) => r.hora === null || r.hora === undefined || !Number.isFinite(r.hora),
  },
  {
    key: 'data_hora',
    label: 'Data e Hora (Timestamp)',
    isMissing: (r) => !r.data_hora || r.data_hora.trim() === '' || !Number.isFinite(r.timestamp),
  },
];

export function calculateColumnMissingStats(
  records: WeatherRecord[],
  extraColumns: ColumnMissingStat[] = [],
  thresholdPct = MISSING_ALERT_THRESHOLD_PCT
): ColumnMissingStat[] {
  const total = records.length;

  const coreStats: ColumnMissingStat[] = CORE_DATASET_COLUMNS.map((col) => {
    let missingCount = 0;
    for (let i = 0; i < total; i++) {
      if (col.isMissing(records[i])) missingCount++;
    }
    const missingPct = total > 0 ? (missingCount / total) * 100 : 0;
    return {
      key: String(col.key),
      label: col.label,
      total,
      missingCount,
      validCount: total - missingCount,
      missingPct,
      exceedsThreshold: missingPct > thresholdPct,
      source: 'core',
    };
  });

  const normalizedExtras: ColumnMissingStat[] = extraColumns.map((col) => ({
    ...col,
    exceedsThreshold: col.missingPct > thresholdPct,
  }));

  const combined = [...coreStats, ...normalizedExtras];
  return combined
    .map((item, idx) => ({ item, idx }))
    .sort((a, b) => {
      if (b.item.missingPct !== a.item.missingPct) {
        return b.item.missingPct - a.item.missingPct;
      }
      return a.idx - b.idx;
    })
    .map(({ item }) => item);
}

function formatBinEdge(value: number): string {
  return value.toFixed(1).replace('.', ',');
}

/**
 * Builds an hourly precipitation histogram strictly over rainy hours (v > 0),
 * aligning bin edges exactly to the Tukey upper fence (Q3 + 1.5 * IQR) so
 * normal rainfall intervals and extreme tail events never mix inside the same bar.
 */
export function precipitationHistogram(records: WeatherRecord[]): PrecipitationHistogramResult {
  let totalValid = 0;
  let zeroCount = 0;
  const rainy: number[] = [];

  for (let i = 0; i < records.length; i++) {
    const v = records[i].precipitacao_mm;
    if (v === null || Number.isNaN(v) || v < 0) continue;
    totalValid++;
    if (v === 0) zeroCount++;
    else rainy.push(v);
  }

  if (rainy.length === 0) {
    return {
      totalValid,
      zeroCount,
      rainyCount: 0,
      q1: null,
      median: null,
      q3: null,
      iqr: null,
      upperFence: null,
      p95: null,
      maxVal: null,
      extremeCount: 0,
      extremePct: 0,
      firstExtremeBinLabel: null,
      bins: [],
    };
  }

  rainy.sort((a, b) => a - b);
  const rainyCount = rainy.length;
  const minVal = rainy[0];
  const maxVal = rainy[rainyCount - 1];
  const q1 = quantile(rainy, 0.25);
  const median = quantile(rainy, 0.5);
  const q3 = quantile(rainy, 0.75);
  const iqr = q3 - q1;
  const p95 = quantile(rainy, 0.95);

  const upperFence =
    rainyCount >= 4 && iqr > 0 ? q3 + 1.5 * iqr : MAX_HOURLY_RAIN_MM;

  const normalValues = rainy.filter((v) => v <= upperFence);
  const extremeValues = rainy.filter((v) => v > upperFence);
  const extremeCount = extremeValues.length;
  const extremePct = (extremeCount / rainyCount) * 100;

  const bins: PrecipitationHistogramBin[] = [];

  const pushRangeBins = (
    values: number[],
    start: number,
    end: number,
    numBins: number,
    isExtreme: boolean,
    prefix: string
  ) => {
    if (values.length === 0) return;
    if (end <= start || numBins <= 1) {
      const label =
        end <= start
          ? `${formatBinEdge(start)}`
          : `${formatBinEdge(start)}–${formatBinEdge(end)}`;
      bins.push({
        id: `${prefix}_0`,
        rangeLabel: label,
        min: start,
        max: end,
        count: values.length,
        densityPct: (values.length / rainyCount) * 100,
        isExtreme,
      });
      return;
    }

    const width = (end - start) / numBins;
    const counts = new Array<number>(numBins).fill(0);
    for (let i = 0; i < values.length; i++) {
      const rawIdx = Math.floor((values[i] - start) / width);
      const clamped = Math.min(numBins - 1, Math.max(0, rawIdx));
      counts[clamped]++;
    }

    for (let b = 0; b < numBins; b++) {
      const bMin = start + b * width;
      const bMax = b === numBins - 1 ? end : start + (b + 1) * width;
      bins.push({
        id: `${prefix}_${b}`,
        rangeLabel: `${formatBinEdge(bMin)}–${formatBinEdge(bMax)}`,
        min: bMin,
        max: bMax,
        count: counts[b],
        densityPct: (counts[b] / rainyCount) * 100,
        isExtreme,
      });
    }
  };

  if (extremeCount > 0) {
    const normalEnd = upperFence;
    const normalStart = Math.min(0, minVal);
    const normalBinCount = normalValues.length >= 24 ? 6 : Math.max(2, Math.min(5, normalValues.length));
    pushRangeBins(normalValues, normalStart, normalEnd, normalBinCount, false, 'norm');

    const extremeBinCount = extremeCount >= 20 ? 6 : Math.max(2, Math.min(5, extremeCount));
    pushRangeBins(extremeValues, upperFence, maxVal, extremeBinCount, true, 'ext');
  } else {
    const singleRangeStart = Math.min(0, minVal);
    const binCount = rainyCount >= 24 ? 8 : Math.max(2, Math.min(6, rainyCount));
    pushRangeBins(normalValues, singleRangeStart, maxVal, binCount, false, 'norm');
  }

  const firstExtremeBin = bins.find((b) => b.isExtreme);

  return {
    totalValid,
    zeroCount,
    rainyCount,
    q1,
    median,
    q3,
    iqr,
    upperFence,
    p95,
    maxVal,
    extremeCount,
    extremePct,
    firstExtremeBinLabel: firstExtremeBin ? firstExtremeBin.rangeLabel : null,
    bins,
  };
}

function computeMeanStd(values: number[]): { mean: number | null; std: number | null } {
  if (values.length < 2) {
    return { mean: values.length === 1 ? values[0] : null, std: null };
  }
  let sum = 0;
  for (let i = 0; i < values.length; i++) sum += values[i];
  const mean = sum / values.length;
  let sqDiffSum = 0;
  for (let i = 0; i < values.length; i++) {
    const d = values[i] - mean;
    sqDiffSum += d * d;
  }
  const std = Math.sqrt(sqDiffSum / values.length);
  return { mean, std };
}

/**
 * Monitors meteorological records against historical climatological baselines (mean +/- k*sigma).
 * Baselines are computed from fullRecords (using rainy hours > 0 for precipitation to avoid
 * zero-inflation distortion) and evaluated across targetRecords.
 */
export function climatologicalThresholdMonitor(
  fullRecords: WeatherRecord[],
  targetRecords: WeatherRecord[],
  sigmaThreshold = 2.0
): ClimatologicalMonitorResult {
  const histRain: number[] = [];
  const histMax: number[] = [];
  const histMin: number[] = [];

  for (let i = 0; i < fullRecords.length; i++) {
    const r = fullRecords[i];
    if (r.precipitacao_mm !== null && !Number.isNaN(r.precipitacao_mm) && r.precipitacao_mm > 0) {
      histRain.push(r.precipitacao_mm);
    }
    if (r.temp_max_c !== null && !Number.isNaN(r.temp_max_c)) {
      histMax.push(r.temp_max_c);
    }
    if (r.temp_min_c !== null && !Number.isNaN(r.temp_min_c)) {
      histMin.push(r.temp_min_c);
    }
  }

  const rainStats = computeMeanStd(histRain);
  const maxStats = computeMeanStd(histMax);
  const minStats = computeMeanStd(histMin);

  const rainBase: ClimatologicalBaselineStat = {
    mean: rainStats.mean,
    std: rainStats.std,
    low: null,
    high:
      rainStats.mean !== null && rainStats.std !== null && rainStats.std > 0
        ? rainStats.mean + sigmaThreshold * rainStats.std
        : null,
    sampleCount: histRain.length,
  };

  const maxBase: ClimatologicalBaselineStat = {
    mean: maxStats.mean,
    std: maxStats.std,
    low:
      maxStats.mean !== null && maxStats.std !== null && maxStats.std > 0
        ? maxStats.mean - sigmaThreshold * maxStats.std
        : null,
    high:
      maxStats.mean !== null && maxStats.std !== null && maxStats.std > 0
        ? maxStats.mean + sigmaThreshold * maxStats.std
        : null,
    sampleCount: histMax.length,
  };

  const minBase: ClimatologicalBaselineStat = {
    mean: minStats.mean,
    std: minStats.std,
    low:
      minStats.mean !== null && minStats.std !== null && minStats.std > 0
        ? minStats.mean - sigmaThreshold * minStats.std
        : null,
    high:
      minStats.mean !== null && minStats.std !== null && minStats.std > 0
        ? minStats.mean + sigmaThreshold * minStats.std
        : null,
    sampleCount: histMin.length,
  };

  const criticalCutoff = sigmaThreshold + 1.0;
  const alerts: ClimatologicalAlertRecord[] = [];
  let rainCount = 0;
  let tempMaxCount = 0;
  let tempMinCount = 0;
  let criticalCount = 0;

  for (let i = 0; i < targetRecords.length; i++) {
    const r = targetRecords[i];
    const flags: ClimatologicalAlertFlag[] = [];

    if (
      r.precipitacao_mm !== null &&
      !Number.isNaN(r.precipitacao_mm) &&
      r.precipitacao_mm > 0 &&
      rainBase.mean !== null &&
      rainBase.std !== null &&
      rainBase.std > 0 &&
      rainBase.high !== null &&
      r.precipitacao_mm > rainBase.high
    ) {
      const z = (r.precipitacao_mm - rainBase.mean) / rainBase.std;
      flags.push({
        variable: 'rain',
        label: 'Chuva extrema',
        zScore: z,
        severity: Math.abs(z) >= criticalCutoff ? 'critico' : 'alerta',
      });
      rainCount++;
    }

    if (
      r.temp_max_c !== null &&
      !Number.isNaN(r.temp_max_c) &&
      maxBase.mean !== null &&
      maxBase.std !== null &&
      maxBase.std > 0 &&
      maxBase.low !== null &&
      maxBase.high !== null
    ) {
      if (r.temp_max_c > maxBase.high) {
        const z = (r.temp_max_c - maxBase.mean) / maxBase.std;
        flags.push({
          variable: 'tempMax',
          label: 'Calor extremo',
          zScore: z,
          severity: Math.abs(z) >= criticalCutoff ? 'critico' : 'alerta',
        });
        tempMaxCount++;
      } else if (r.temp_max_c < maxBase.low) {
        const z = (r.temp_max_c - maxBase.mean) / maxBase.std;
        flags.push({
          variable: 'tempMax',
          label: 'Máx. muito baixa',
          zScore: z,
          severity: Math.abs(z) >= criticalCutoff ? 'critico' : 'alerta',
        });
        tempMaxCount++;
      }
    }

    if (
      r.temp_min_c !== null &&
      !Number.isNaN(r.temp_min_c) &&
      minBase.mean !== null &&
      minBase.std !== null &&
      minBase.std > 0 &&
      minBase.low !== null &&
      minBase.high !== null
    ) {
      if (r.temp_min_c < minBase.low) {
        const z = (r.temp_min_c - minBase.mean) / minBase.std;
        flags.push({
          variable: 'tempMin',
          label: 'Frio atípico',
          zScore: z,
          severity: Math.abs(z) >= criticalCutoff ? 'critico' : 'alerta',
        });
        tempMinCount++;
      } else if (r.temp_min_c > minBase.high) {
        const z = (r.temp_min_c - minBase.mean) / minBase.std;
        flags.push({
          variable: 'tempMin',
          label: 'Mín. muito alta',
          zScore: z,
          severity: Math.abs(z) >= criticalCutoff ? 'critico' : 'alerta',
        });
        tempMinCount++;
      }
    }

    if (flags.length > 0) {
      let peakFlag = flags[0];
      for (let f = 1; f < flags.length; f++) {
        if (Math.abs(flags[f].zScore) > Math.abs(peakFlag.zScore)) {
          peakFlag = flags[f];
        }
      }
      const severity: 'alerta' | 'critico' = flags.some((f) => f.severity === 'critico')
        ? 'critico'
        : 'alerta';
      if (severity === 'critico') criticalCount++;
      alerts.push({
        record: r,
        flags,
        maxAbsZ: Math.abs(peakFlag.zScore),
        signedPeakZ: peakFlag.zScore,
        severity,
      });
    }
  }

  return {
    sigmaThreshold,
    totalEvaluated: targetRecords.length,
    alertCount: alerts.length,
    criticalCount,
    countsByVar: {
      rain: rainCount,
      tempMax: tempMaxCount,
      tempMin: tempMinCount,
    },
    baselines: {
      rain: rainBase,
      tempMax: maxBase,
      tempMin: minBase,
    },
    alerts,
  };
}

export function generateInsights(records: WeatherRecord[]): string[] {
  if (records.length === 0) {
    return ['Nenhum registro atende aos filtros atuais.'];
  }
  const mensal = monthlySummary(records);
  const diario = dailySummary(records);

  const insights: string[] = [];

  if (mensal.length > 0) {
    const chuvaMes = mensal.reduce((best, cur) => (cur.precipitacao_mm > best.precipitacao_mm ? cur : best), mensal[0]);
    insights.push(
      `${chuvaMes.mes_nome} foi o mês mais chuvoso do recorte, com ${chuvaMes.precipitacao_mm.toFixed(1)} mm.`
    );

    const validTempMonths = mensal.filter((m) => m.temp_max_media !== null);
    if (validTempMonths.length > 0) {
      const quente = validTempMonths.reduce(
        (best, cur) => ((cur.temp_max_media ?? -999) > (best.temp_max_media ?? -999) ? cur : best),
        validTempMonths[0]
      );
      insights.push(
        `${quente.mes_nome} teve a maior temperatura máxima média: ${(quente.temp_max_media ?? 0).toFixed(1)} °C.`
      );
    }
  }

  let pico: WeatherRecord | null = null;
  for (let i = 0; i < records.length; i++) {
    const r = records[i];
    if (r.precipitacao_mm !== null) {
      if (!pico || r.precipitacao_mm > (pico.precipitacao_mm ?? -1)) {
        pico = r;
      }
    }
  }
  if (pico && pico.precipitacao_mm !== null) {
    const m = pico.data_hora.match(/^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})/);
    const dtStr = m ? `${m[3]}/${m[2]}/${m[1]} às ${m[4]}:${m[5]}` : pico.data_hora;
    insights.push(`O maior registro horário de chuva foi ${pico.precipitacao_mm.toFixed(1)} mm em ${dtStr}.`);
  }

  const diasSecos = diario.filter((d) => d.precipitacao_mm === 0).length;
  insights.push(`O recorte contém ${diasSecos} dias sem precipitação registrada.`);

  return insights;
}

function pearsonCorr(xs: Array<number | null>, ys: Array<number | null>): number | null {
  const pairs: Array<[number, number]> = [];
  for (let i = 0; i < xs.length; i++) {
    const x = xs[i];
    const y = ys[i];
    if (x !== null && y !== null && !Number.isNaN(x) && !Number.isNaN(y)) {
      pairs.push([x, y]);
    }
  }
  if (pairs.length < 2) return null;
  const meanX = mean(pairs.map((p) => p[0]))!;
  const meanY = mean(pairs.map((p) => p[1]))!;
  let num = 0;
  let denX = 0;
  let denY = 0;
  for (let i = 0; i < pairs.length; i++) {
    const dx = pairs[i][0] - meanX;
    const dy = pairs[i][1] - meanY;
    num += dx * dy;
    denX += dx * dx;
    denY += dy * dy;
  }
  const denom = Math.sqrt(denX * denY);
  if (denom === 0 || !Number.isFinite(denom)) return null;
  return num / denom;
}

export function correlationMatrix(records: WeatherRecord[]): {
  labels: string[];
  values: Array<Array<number | null>>;
} {
  const cols = [
    records.map((r) => r.precipitacao_mm),
    records.map((r) => r.temp_max_c),
    records.map((r) => r.temp_min_c),
  ];
  const labels = ['Chuva', 'Temp. máx.', 'Temp. mín.'];
  const values: Array<Array<number | null>> = cols.map((colA, i) =>
    cols.map((colB, j) => (i === j ? 1.0 : pearsonCorr(colA, colB)))
  );
  return { labels, values };
}

export function calculateDewPoint(tempC: number | null | undefined, humidityPct: number | null | undefined): number | null {
  if (tempC === null || tempC === undefined || humidityPct === null || humidityPct === undefined) {
    return null;
  }
  const t = Number(tempC);
  const rh = Math.max(1.0, Math.min(100.0, Number(humidityPct)));
  if (Number.isNaN(t) || Number.isNaN(rh)) return null;
  const a = 17.27;
  const b = 237.7;
  const alpha = (a * t) / (b + t) + Math.log(rh / 100.0);
  return Math.round(((b * alpha) / (a - alpha)) * 10) / 10;
}

export function calculateHeatIndex(
  tempC: number | null | undefined,
  humidityPct: number | null | undefined
): { value: number | null; description: string; level: string } {
  if (tempC === null || tempC === undefined || humidityPct === null || humidityPct === undefined) {
    return { value: null, description: 'Indisponível', level: 'baixo' };
  }
  const tC = Number(tempC);
  const rh = Math.max(1.0, Math.min(100.0, Number(humidityPct)));
  if (Number.isNaN(tC) || Number.isNaN(rh)) {
    return { value: null, description: 'Indisponível', level: 'baixo' };
  }

  const tF = (tC * 9.0) / 5.0 + 32.0;
  let hiF: number;

  if (tF < 80.0) {
    hiF = 0.5 * (tF + 61.0 + (tF - 68.0) * 1.2 + rh * 0.094);
  } else {
    hiF =
      -42.379 +
      2.04901523 * tF +
      10.14333127 * rh -
      0.22475541 * tF * rh -
      0.00683783 * tF * tF -
      0.05481717 * rh * rh +
      0.00122874 * tF * tF * rh +
      0.00085282 * tF * rh * rh -
      0.00000199 * tF * tF * rh * rh;

    if (rh < 13.0 && tF >= 80.0 && tF <= 112.0) {
      hiF -= ((13.0 - rh) / 4.0) * Math.sqrt((17.0 - Math.abs(tF - 95.0)) / 17.0);
    } else if (rh > 85.0 && tF >= 80.0 && tF <= 87.0) {
      hiF += ((rh - 85.0) / 10.0) * ((87.0 - tF) / 5.0);
    }
  }

  const hiC = Math.round((((hiF - 32.0) * 5.0) / 9.0) * 10) / 10;
  if (hiC < 27.0) return { value: hiC, description: 'Normal / Confortável', level: 'baixo' };
  if (hiC < 32.0) return { value: hiC, description: 'Atenção (Fadiga com exposição)', level: 'cuidado' };
  if (hiC < 41.0) return { value: hiC, description: 'Cuidado Extremo (Cãibras/Insolação)', level: 'cuidado_extremo' };
  if (hiC < 54.0) return { value: hiC, description: 'Perigo (Insolação Provável)', level: 'perigo' };
  return { value: hiC, description: 'Perigo Extremo (Alto Risco Térmico)', level: 'perigo_extremo' };
}

export function evaluateStormRisk(
  pressaoHpa: number | null | undefined,
  umidadePct: number | null | undefined,
  ventoKmh: number | null | undefined,
  rajadasKmh: number | null | undefined,
  precipitacaoMm: number | null | undefined = 0.0
): StormRisk {
  if (pressaoHpa === null || pressaoHpa === undefined || Number.isNaN(pressaoHpa)) {
    return {
      nivel: 'Atmosfera Estável',
      cor: '#10B981',
      classe: 'storm-low',
      icone: '🟢',
      detalhe: 'Sem leitura barométrica no momento.',
    };
  }

  const p = Number(pressaoHpa);
  const rh = Number(umidadePct ?? 0);
  const v = Number(ventoKmh ?? 0);
  const gust = Number(rajadasKmh ?? v);
  const rain = Number(precipitacaoMm ?? 0);

  if ((p < 1005.0 && rh >= 75.0 && (gust >= 30.0 || v >= 20.0 || rain > 0.5)) || (p < 1002.0 && gust >= 25.0)) {
    return {
      nivel: 'Alto Risco de Tempestade',
      cor: '#EF4444',
      classe: 'storm-high',
      icone: '⚡',
      detalhe: `Queda barométrica crítica (${p.toFixed(0)} hPa) combinada com umidade elevada (${rh.toFixed(0)}%) e rajadas (${gust.toFixed(1)} km/h). Risco de temporal severo.`,
    };
  }
  if (p < 1008.0 && (rh >= 70.0 || gust >= 35.0)) {
    return {
      nivel: 'Alerta de Instabilidade',
      cor: '#F59E0B',
      classe: 'storm-med',
      icone: '⚠️',
      detalhe: `Baixa pressão barométrica (${p.toFixed(0)} hPa) indicando instabilidade atmosférica e potencial para pancadas de chuva.`,
    };
  }
  if (gust >= 45.0) {
    return {
      nivel: 'Alerta de Rajadas Intensas',
      cor: '#F59E0B',
      classe: 'storm-med',
      icone: '💨',
      detalhe: `Rajadas intensas de vento (${gust.toFixed(1)} km/h) detectadas nas proximidades.`,
    };
  }
  return {
    nivel: 'Atmosfera Estável',
    cor: '#10B981',
    classe: 'storm-low',
    icone: '🟢',
    detalhe: `Pressão atmosférica estável (${p.toFixed(0)} hPa) e sem indicativo de tempestades severas imediatas.`,
  };
}

export function calculateClimateAnomaly(
  records: WeatherRecord[] | null,
  currentWeather: LivePointWeather | null
): ClimateAnomaly | null {
  if (!records || records.length === 0 || !currentWeather) return null;

  const rawDt = currentWeather.horario_raw || currentWeather.horario;
  let mesAtual = new Date().getMonth() + 1;
  const m = rawDt.match(/^(\d{4})-(\d{2})-/);
  if (m) mesAtual = Number(m[2]);

  const nomeMes = MESES_EXTENSO[mesAtual] || String(mesAtual);
  let dfMes = records.filter((r) => r.mes === mesAtual);
  if (dfMes.length === 0) dfMes = records;

  const maxVals = dfMes.map((r) => r.temp_max_c).filter((v): v is number => v !== null);
  const minVals = dfMes.map((r) => r.temp_min_c).filter((v): v is number => v !== null);
  const histMax = mean(maxVals) ?? 0;
  const histMin = mean(minVals) ?? 0;
  const histTempMean = histMax && histMin ? (histMax + histMin) / 2.0 : histMax || histMin;

  const uniqueDays = new Set(dfMes.map((r) => r.dia));
  const daysCount = Math.max(1, uniqueDays.size);
  const totalRain = dfMes.reduce((acc, r) => acc + (r.precipitacao_mm ?? 0), 0);
  const histRainDailyAvg = totalRain / daysCount;

  const currTemp = currentWeather.temperatura_c;
  const currRain = Number(currentWeather.precipitacao_mm ?? 0);
  const local = currentWeather.local || 'O local';

  if (currTemp === null || !histTempMean) return null;

  const deltaTemp = currTemp - histTempMean;
  const deltaRain = currRain - histRainDailyAvg;
  const sinalTemp = deltaTemp >= 0 ? '+' : '';
  const adjetivo = deltaTemp >= 0 ? 'acima da' : 'abaixo da';

  const summaryText =
    `${local} está ${sinalTemp}${deltaTemp.toFixed(1)} °C ${adjetivo} média histórica para ${nomeMes} ` +
    `(${currTemp.toFixed(1)} °C atual vs. ${histTempMean.toFixed(1)} °C média histórica).`;

  return {
    has_history: true,
    mes_num: mesAtual,
    mes_nome: nomeMes.charAt(0).toUpperCase() + nomeMes.slice(1),
    hist_temp_mean: Math.round(histTempMean * 10) / 10,
    hist_max_mean: Math.round(histMax * 10) / 10,
    hist_min_mean: Math.round(histMin * 10) / 10,
    hist_rain_daily_avg: Math.round(histRainDailyAvg * 10) / 10,
    curr_temp: Math.round(currTemp * 10) / 10,
    curr_rain: Math.round(currRain * 10) / 10,
    delta_temp: Math.round(deltaTemp * 10) / 10,
    delta_rain: Math.round(deltaRain * 10) / 10,
    summary_text: summaryText,
    status: deltaTemp > 0.5 ? 'quente' : deltaTemp < -0.5 ? 'frio' : 'neutro',
  };
}

export function classifyAirQuality(
  usAqi: number | null | undefined,
  pm25: number | null | undefined
): AirQualityInfo {
  if ((usAqi === null || usAqi === undefined) && (pm25 === null || pm25 === undefined)) {
    return {
      status: 'Sem Dados',
      cor: '#94A3B8',
      badge_class: 'aqi-unknown',
      icone: '⚪',
      recomendacao: 'Dados de qualidade do ar não disponíveis para esta coordenada.',
    };
  }
  const val = usAqi !== null && usAqi !== undefined ? Number(usAqi) : Number(pm25 ?? 0) * 3.0;
  if (val <= 50) {
    return {
      status: 'Boa',
      cor: '#10B981',
      badge_class: 'aqi-good',
      icone: '🟢',
      recomendacao: 'Qualidade do ar satisfatória; sem risco à saúde da população.',
    };
  }
  if (val <= 100) {
    return {
      status: 'Moderada',
      cor: '#F59E0B',
      badge_class: 'aqi-moderate',
      icone: '🟡',
      recomendacao: 'Qualidade aceitável. Indivíduos hipersensíveis a partículas devem monitorar sintomas.',
    };
  }
  if (val <= 150) {
    return {
      status: 'Alerta p/ Grupos Sensíveis',
      cor: '#F97316',
      badge_class: 'aqi-sensitive',
      icone: '🟠',
      recomendacao:
        'Fumaça / material particulado perceptível. Crianças, idosos e pessoas com asma devem evitar esforço externo prolongado.',
    };
  }
  if (val <= 200) {
    return {
      status: 'Não Saudável',
      cor: '#EF4444',
      badge_class: 'aqi-unhealthy',
      icone: '🔴',
      recomendacao:
        'Fumaça densa de queimadas. Toda a população pode sofrer irritação ocular e respiratória. Evite exercícios ao ar livre.',
    };
  }
  return {
    status: 'Muito Prejudicial / Crítico',
    cor: '#7C3AED',
    badge_class: 'aqi-hazardous',
    icone: '🟣',
    recomendacao:
      'Alerta de emergência de saúde por poluição severa. Permaneça em ambientes fechados com purificadores ou use máscaras de proteção.',
  };
}

export function classifyUv(uvIndex: number | null | undefined): UvInfo {
  if (uvIndex === null || uvIndex === undefined || Number.isNaN(uvIndex)) {
    return { status: 'Indisponível', cor: '#94A3B8', icone: '⚪', recomendacao: 'Sem leitura UV.' };
  }
  const val = Number(uvIndex);
  if (val < 3.0) return { status: 'Baixo', cor: '#10B981', icone: '🟢', recomendacao: 'Baixo risco. Proteção mínima.' };
  if (val < 6.0) return { status: 'Moderado', cor: '#F59E0B', icone: '🟡', recomendacao: 'Use protetor solar e óculos de sol.' };
  if (val < 8.0)
    return {
      status: 'Alto',
      cor: '#F97316',
      icone: '🟠',
      recomendacao: 'Proteção necessária: filtro solar FPS 30+, boné e sombra ao meio-dia.',
    };
  if (val < 11.0)
    return {
      status: 'Muito Alto',
      cor: '#EF4444',
      icone: '🔴',
      recomendacao: 'Risco elevado de queimaduras. Evite exposição direta entre 10h e 16h.',
    };
  return {
    status: 'Extremo',
    cor: '#7C3AED',
    icone: '🟣',
    recomendacao: 'Risco extremo à pele e aos olhos em poucos minutos. Procure sombra.',
  };
}
