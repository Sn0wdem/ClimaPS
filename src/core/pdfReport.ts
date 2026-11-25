import { jsPDF } from 'jspdf';
import type {
  FilterSpec,
  MonthlySummaryRow,
  PrecipitationHistogramResult,
  StationDataset,
  WeatherRecord,
} from '../types/weather';
import {
  MISSING_ALERT_THRESHOLD_PCT,
  calculateColumnMissingStats,
  calculateKpis,
  correlationMatrix,
  generateInsights,
  monthlySummary,
  precipitationHistogram,
  qualityReport,
} from './analysis';
import { brNumber, formatDateBR, getStamp, safeFilename } from './formatters';

export interface PdfReportOptions {
  scope: 'full' | 'filtered';
  includeSummary: boolean;
  includeMonthlyChart: boolean;
  includeHistogram: boolean;
  includeQualityAndCorr: boolean;
}

export interface PdfReportInput {
  dataset: StationDataset;
  fullRecords: WeatherRecord[];
  targetRecords: WeatherRecord[];
  filterSpec: FilterSpec;
  options: PdfReportOptions;
}

/**
 * Ensures text uses WinAnsi-safe characters for jsPDF's built-in Helvetica font
 * while preserving all Portuguese diacritics (á, é, í, ó, ú, ã, õ, â, ê, ô, ç, °).
 */
function pdfText(raw: string): string {
  return raw
    .replace(/≤/g, '<=')
    .replace(/≥/g, '>=')
    .replace(/[–—]/g, '-')
    .replace(/•/g, '-')
    .replace(/×/g, 'x')
    .replace(/[^\x20-\xFF]/g, '');
}

/**
 * Renders the Monthly Precipitation (bars) + Mean Max/Min Temperature (lines) chart
 * onto a high-DPI offscreen canvas for crisp embedding in PDF.
 */
function renderMonthlyChartImage(mensal: MonthlySummaryRow[]): string | null {
  if (mensal.length === 0) return null;

  const width = 1400;
  const height = 560;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  // Clean clinical light canvas
  ctx.fillStyle = '#FFFFFF';
  ctx.fillRect(0, 0, width, height);

  // Subtle card border
  ctx.strokeStyle = '#E2E8F0';
  ctx.lineWidth = 2;
  ctx.strokeRect(1, 1, width - 2, height - 2);

  const padLeft = 92;
  const padRight = 92;
  const padTop = 74;
  const padBottom = 78;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  // Title & Legend
  ctx.fillStyle = '#0F172A';
  ctx.font = '700 22px "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('Precipitação Mensal (mm) e Temperaturas Médias (°C)', padLeft, 36);

  // Legend items right-aligned
  const legendItems = [
    { label: 'Chuva (mm)', color: '#0284C7', type: 'bar' as const },
    { label: 'Temp. máx. média (°C)', color: '#D97706', type: 'line' as const },
    { label: 'Temp. mín. média (°C)', color: '#0F766E', type: 'line' as const },
  ];
  ctx.font = '500 16px "DM Sans", -apple-system, sans-serif';
  let lx = width - padRight;
  for (let i = legendItems.length - 1; i >= 0; i--) {
    const item = legendItems[i];
    const tw = ctx.measureText(item.label).width;
    lx -= tw;
    ctx.fillStyle = '#475569';
    ctx.textAlign = 'left';
    ctx.fillText(item.label, lx, 36);
    lx -= 24;
    if (item.type === 'bar') {
      ctx.fillStyle = item.color;
      ctx.fillRect(lx, 24, 16, 12);
    } else {
      ctx.strokeStyle = item.color;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(lx, 30);
      ctx.lineTo(lx + 16, 30);
      ctx.stroke();
    }
    lx -= 24;
  }

  // Scales
  const maxRain = Math.max(10, ...mensal.map((m) => m.precipitacao_mm));
  const rainCeiling = Math.ceil(maxRain / 50) * 50 || 50;

  const temps = mensal.flatMap((m) =>
    [m.temp_max_media, m.temp_min_media].filter((v): v is number => v !== null)
  );
  const tMinRaw = temps.length > 0 ? Math.min(...temps) : 15;
  const tMaxRaw = temps.length > 0 ? Math.max(...temps) : 35;
  const tFloor = Math.floor(tMinRaw - 2);
  const tCeil = Math.ceil(tMaxRaw + 2);
  const tSpan = Math.max(4, tCeil - tFloor);

  // Gridlines + Left (Rain) and Right (Temp) axis ticks
  const ticks = 5;
  ctx.font = '500 15px "JetBrains Mono", ui-monospace, monospace';
  for (let t = 0; t <= ticks; t++) {
    const frac = t / ticks;
    const y = padTop + plotH - frac * plotH;

    ctx.strokeStyle = t === 0 ? '#94A3B8' : '#E2E8F0';
    ctx.lineWidth = t === 0 ? 1.5 : 1;
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(padLeft + plotW, y);
    ctx.stroke();

    // Left tick (mm)
    const rainVal = rainCeiling * frac;
    ctx.fillStyle = '#0284C7';
    ctx.textAlign = 'right';
    ctx.fillText(`${Math.round(rainVal)}`, padLeft - 14, y + 5);

    // Right tick (°C)
    const tempVal = tFloor + tSpan * frac;
    ctx.fillStyle = '#B45309';
    ctx.textAlign = 'left';
    ctx.fillText(`${tempVal.toFixed(0)}°`, padLeft + plotW + 14, y + 5);
  }

  // Axis Titles
  ctx.fillStyle = '#64748B';
  ctx.font = '600 14px "DM Sans", sans-serif';
  ctx.textAlign = 'right';
  ctx.fillText('mm', padLeft - 14, padTop - 14);
  ctx.textAlign = 'left';
  ctx.fillText('°C', padLeft + plotW + 14, padTop - 14);

  // Bars & X labels
  const step = plotW / mensal.length;
  const barW = Math.min(58, step * 0.56);

  mensal.forEach((m, idx) => {
    const cx = padLeft + step * idx + step / 2;
    const barH = (m.precipitacao_mm / rainCeiling) * plotH;
    const bx = cx - barW / 2;
    const by = padTop + plotH - barH;

    ctx.fillStyle = 'rgba(2, 132, 199, 0.78)';
    ctx.fillRect(bx, by, barW, barH);

    // X-axis label
    ctx.fillStyle = '#334155';
    ctx.font = '600 16px "DM Sans", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(m.mes_nome, cx, padTop + plotH + 28);

    // Rain value above bar if room
    if (m.precipitacao_mm > 0) {
      ctx.fillStyle = '#0369A1';
      ctx.font = '500 13px "JetBrains Mono", monospace';
      ctx.fillText(brNumber(m.precipitacao_mm, 0), cx, Math.max(padTop + 14, by - 8));
    }
  });

  // Helper to draw temperature line
  const drawTempSeries = (getter: (m: MonthlySummaryRow) => number | null, color: string) => {
    const pts: Array<{ x: number; y: number }> = [];
    mensal.forEach((m, idx) => {
      const val = getter(m);
      if (val === null) return;
      const cx = padLeft + step * idx + step / 2;
      const y = padTop + plotH - ((val - tFloor) / tSpan) * plotH;
      pts.push({ x: cx, y });
    });
    if (pts.length === 0) return;

    ctx.strokeStyle = color;
    ctx.lineWidth = 3.5;
    ctx.beginPath();
    pts.forEach((p, idx) => {
      if (idx === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.stroke();

    pts.forEach((p) => {
      ctx.fillStyle = '#FFFFFF';
      ctx.beginPath();
      ctx.arc(p.x, p.y, 5.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.stroke();
    });
  };

  drawTempSeries((m) => m.temp_max_media, '#D97706');
  drawTempSeries((m) => m.temp_min_media, '#0F766E');

  return canvas.toDataURL('image/png');
}

/**
 * Renders the Precipitation Distribution Histogram highlighting extreme events (> Q3 + 1.5*IQR)
 * onto a high-DPI offscreen canvas for crisp embedding in PDF.
 */
function renderHistogramChartImage(hist: PrecipitationHistogramResult): string | null {
  if (hist.rainyCount === 0 || hist.bins.length === 0) return null;

  const width = 1400;
  const height = 540;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  ctx.fillStyle = '#FFFFFF';
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = '#E2E8F0';
  ctx.lineWidth = 2;
  ctx.strokeRect(1, 1, width - 2, height - 2);

  const padLeft = 88;
  const padRight = 46;
  const padTop = 76;
  const padBottom = 104;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  ctx.fillStyle = '#0F172A';
  ctx.font = '700 22px "Plus Jakarta Sans", -apple-system, sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('Histograma de Precipitação (> 0 mm) e Densidade de Extremos', padLeft, 36);

  // Legend right
  const legendItems = [
    { label: `Intervalo normal (<= ${brNumber(hist.upperFence)} mm/h)`, color: '#0284C7' },
    { label: `Cauda extrema (> ${brNumber(hist.upperFence)} mm/h)`, color: '#DC2626' },
  ];
  ctx.font = '500 15px "DM Sans", sans-serif';
  let lx = width - padRight;
  for (let i = legendItems.length - 1; i >= 0; i--) {
    const item = legendItems[i];
    const tw = ctx.measureText(item.label).width;
    lx -= tw;
    ctx.fillStyle = '#475569';
    ctx.textAlign = 'left';
    ctx.fillText(item.label, lx, 36);
    lx -= 22;
    ctx.fillStyle = item.color;
    ctx.fillRect(lx, 24, 14, 14);
    lx -= 22;
  }

  const maxDensity = Math.max(5, ...hist.bins.map((b) => b.densityPct));
  const yCeiling = Math.ceil(maxDensity / 10) * 10 || 10;

  // Grid & Y-axis ticks (%)
  const ticks = 5;
  ctx.font = '500 15px "JetBrains Mono", monospace';
  for (let t = 0; t <= ticks; t++) {
    const frac = t / ticks;
    const y = padTop + plotH - frac * plotH;

    ctx.strokeStyle = t === 0 ? '#94A3B8' : '#E2E8F0';
    ctx.lineWidth = t === 0 ? 1.5 : 1;
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(padLeft + plotW, y);
    ctx.stroke();

    ctx.fillStyle = '#475569';
    ctx.textAlign = 'right';
    ctx.fillText(`${Math.round(yCeiling * frac)}%`, padLeft - 14, y + 5);
  }

  const bins = hist.bins;
  const step = plotW / bins.length;
  const barW = Math.min(72, step * 0.72);
  let firstExtremeX: number | null = null;

  bins.forEach((bin, idx) => {
    const cx = padLeft + step * idx + step / 2;
    const barH = (bin.densityPct / yCeiling) * plotH;
    const bx = cx - barW / 2;
    const by = padTop + plotH - barH;

    if (bin.isExtreme && firstExtremeX === null) {
      firstExtremeX = padLeft + step * idx;
    }

    ctx.fillStyle = bin.isExtreme ? 'rgba(220, 38, 38, 0.88)' : 'rgba(2, 132, 199, 0.82)';
    ctx.fillRect(bx, by, barW, barH);

    // Value label above bar
    if (bin.count > 0) {
      ctx.fillStyle = bin.isExtreme ? '#B91C1C' : '#0369A1';
      ctx.font = '600 13px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`${brNumber(bin.densityPct, 1)}% (${bin.count}h)`, cx, Math.max(padTop + 14, by - 8));
    }

    // Angled X label
    ctx.save();
    ctx.translate(cx, padTop + plotH + 16);
    ctx.rotate(-Math.PI / 7);
    ctx.fillStyle = bin.isExtreme ? '#B91C1C' : '#334155';
    ctx.font = '500 14px "JetBrains Mono", monospace';
    ctx.textAlign = 'right';
    ctx.fillText(bin.rangeLabel, 0, 0);
    ctx.restore();
  });

  // Dashed vertical threshold line right before the first extreme bin
  if (firstExtremeX !== null) {
    ctx.save();
    ctx.strokeStyle = '#DC2626';
    ctx.lineWidth = 2.5;
    ctx.setLineDash([7, 5]);
    ctx.beginPath();
    ctx.moveTo(firstExtremeX, padTop - 6);
    ctx.lineTo(firstExtremeX, padTop + plotH);
    ctx.stroke();
    ctx.restore();

    ctx.fillStyle = '#DC2626';
    ctx.font = '700 14px "JetBrains Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`Limite IQR: ${brNumber(hist.upperFence)} mm/h`, firstExtremeX + 8, padTop + 14);
  }

  ctx.fillStyle = '#64748B';
  ctx.font = '500 14px "DM Sans", sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(
    'Intensidade horária (mm/h) · Densidade calculada sobre horas chuvosas (> 0 mm)',
    padLeft + plotW / 2,
    height - 16
  );

  return canvas.toDataURL('image/png');
}

export function generateStructuredPdfReport(input: PdfReportInput): string {
  const { dataset, fullRecords, targetRecords, filterSpec, options } = input;
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const pageW = doc.internal.pageSize.getWidth(); // 210 mm
  const pageH = doc.internal.pageSize.getHeight(); // 297 mm
  const margin = 15;
  const contentW = pageW - margin * 2;

  const kpis = calculateKpis(targetRecords);
  const insights = generateInsights(targetRecords);
  const mensal = monthlySummary(targetRecords);
  const rainHist = precipitationHistogram(targetRecords);
  const report = qualityReport(fullRecords);
  const missingCols = calculateColumnMissingStats(
    targetRecords,
    options.scope === 'full' ? dataset.extraColumnMissing ?? [] : [],
    MISSING_ALERT_THRESHOLD_PCT
  );
  const corr = correlationMatrix(targetRecords);

  const stationName = dataset.metadata.nome || 'Estação Meteorológica';
  const stationCode = dataset.metadata.codigo_estacao || 'CSV';
  const scopeLabel = options.scope === 'full' ? 'Base completa' : 'Recorte filtrado';
  const periodStart =
    targetRecords.length > 0 ? formatDateBR(targetRecords[0].dia) : formatDateBR(filterSpec.start);
  const periodEnd =
    targetRecords.length > 0
      ? formatDateBR(targetRecords[targetRecords.length - 1].dia)
      : formatDateBR(filterSpec.end);
  const generatedAt = new Date().toLocaleString('pt-BR');

  let y = margin;
  let hasContentOnCurrentPage = false;

  const ensureSpace = (neededMm: number) => {
    if (y + neededMm > pageH - 18) {
      doc.addPage();
      y = margin + 4;
      hasContentOnCurrentPage = false;
    }
  };

  const drawSectionTitle = (title: string, subtitle?: string) => {
    ensureSpace(16);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.setTextColor(15, 23, 42);
    doc.text(pdfText(title), margin, y);
    y += 1.8;
    doc.setDrawColor(2, 132, 199);
    doc.setLineWidth(0.6);
    doc.line(margin, y, margin + 22, y);
    y += 4.2;
    if (subtitle) {
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8.5);
      doc.setTextColor(100, 116, 139);
      doc.text(pdfText(subtitle), margin, y);
      y += 5;
    }
    hasContentOnCurrentPage = true;
  };

  // =========================================================================
  // HEADER BANNER (Page 1)
  // =========================================================================
  doc.setFillColor(15, 23, 42);
  doc.rect(0, 0, pageW, 34, 'F');
  doc.setFillColor(2, 132, 199);
  doc.rect(0, 34, pageW, 1.4, 'F');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16);
  doc.setTextColor(248, 250, 252);
  doc.text('CLIMAPS', margin, 13);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9.5);
  doc.setTextColor(148, 163, 184);
  doc.text(pdfText('Relatório Analítico e Auditoria Meteorológica'), margin + 31, 13);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10.5);
  doc.setTextColor(241, 245, 249);
  doc.text(pdfText(`${stationName} (${stationCode})`), margin, 22);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.2);
  doc.setTextColor(203, 213, 225);
  doc.text(
    pdfText(`Escopo: ${scopeLabel}  |  Período: ${periodStart} a ${periodEnd}  |  Emitido em: ${generatedAt}`),
    margin,
    29
  );

  y = 43;

  // =========================================================================
  // SECTION 1: EXECUTIVE SUMMARY, KPIs, INSIGHTS & MONTHLY TABLE
  // =========================================================================
  if (options.includeSummary) {
    drawSectionTitle(
      '1. Resumo Executivo e Indicadores',
      `Consolidado de ${brNumber(targetRecords.length, 0)} observações horárias no escopo selecionado.`
    );

    // 5 KPI cards across contentW
    const kpiItems = [
      { label: 'Registros', val: `${brNumber(kpis.registros, 0)} h`, accent: false },
      { label: 'Chuva acumulada', val: `${brNumber(kpis.precipitacao_total)} mm`, accent: true },
      { label: 'Máx. média', val: `${brNumber(kpis.temp_max_media)} °C`, accent: false },
      { label: 'Mín. média', val: `${brNumber(kpis.temp_min_media)} °C`, accent: false },
      { label: 'Completude', val: `${brNumber(kpis.completude)}%`, accent: false },
    ];
    const gap = 3;
    const cardW = (contentW - gap * 4) / 5;
    const cardH = 17;

    kpiItems.forEach((item, i) => {
      const cx = margin + i * (cardW + gap);
      doc.setFillColor(248, 250, 252);
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(0.3);
      doc.roundedRect(cx, y, cardW, cardH, 2, 2, 'FD');

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.5);
      doc.setTextColor(100, 116, 139);
      doc.text(pdfText(item.label), cx + 3, y + 5.5);

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(11);
      if (item.accent) doc.setTextColor(2, 132, 199);
      else doc.setTextColor(15, 23, 42);
      doc.text(pdfText(item.val), cx + 3, y + 13);
    });
    y += cardH + 7;

    // Automated Insights
    if (insights.length > 0) {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9.5);
      doc.setTextColor(30, 41, 59);
      doc.text('Destaques Automáticos', margin, y);
      y += 4.5;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8.5);
      doc.setTextColor(51, 65, 85);
      insights.forEach((ins) => {
        const lines = doc.splitTextToSize(pdfText(`- ${ins}`), contentW - 4);
        ensureSpace(lines.length * 4.2 + 2);
        doc.text(lines, margin + 2, y);
        y += lines.length * 4.2 + 1.2;
      });
      y += 4;
    }

    // Monthly Summary Table
    if (mensal.length > 0) {
      ensureSpace(18 + mensal.length * 6.2);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9.5);
      doc.setTextColor(30, 41, 59);
      doc.text('Resumo Mensal', margin, y);
      y += 4;

      const cols = [
        { header: 'Mês', x: margin + 2, align: 'left' as const },
        { header: 'Registros', x: margin + 52, align: 'right' as const },
        { header: 'Chuva (mm)', x: margin + 84, align: 'right' as const },
        { header: 'Máx. média (°C)', x: margin + 118, align: 'right' as const },
        { header: 'Mín. média (°C)', x: margin + 150, align: 'right' as const },
        { header: 'Horas c/ chuva', x: margin + contentW - 2, align: 'right' as const },
      ];

      // Table Header
      doc.setFillColor(241, 245, 249);
      doc.rect(margin, y, contentW, 6.8, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7.8);
      doc.setTextColor(71, 85, 105);
      cols.forEach((c) => doc.text(pdfText(c.header), c.x, y + 4.7, { align: c.align }));
      y += 6.8;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8.2);
      mensal.forEach((m, idx) => {
        ensureSpace(6.2);
        if (idx % 2 === 1) {
          doc.setFillColor(248, 250, 252);
          doc.rect(margin, y, contentW, 5.8, 'F');
        }
        doc.setTextColor(15, 23, 42);
        doc.text(pdfText(m.mes_nome), cols[0].x, y + 4.1);
        doc.text(brNumber(m.registros, 0), cols[1].x, y + 4.1, { align: 'right' });
        doc.setFont('helvetica', 'bold');
        doc.text(brNumber(m.precipitacao_mm), cols[2].x, y + 4.1, { align: 'right' });
        doc.setFont('helvetica', 'normal');
        doc.text(brNumber(m.temp_max_media), cols[3].x, y + 4.1, { align: 'right' });
        doc.text(brNumber(m.temp_min_media), cols[4].x, y + 4.1, { align: 'right' });
        doc.text(brNumber(m.horas_com_chuva, 0), cols[5].x, y + 4.1, { align: 'right' });
        y += 5.8;
      });
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(0.25);
      doc.line(margin, y, margin + contentW, y);
      y += 8;
    }
  }

  // =========================================================================
  // SECTION 2: CHARTS (MONTHLY SERIES & PRECIPITATION HISTOGRAM)
  // =========================================================================
  if (options.includeMonthlyChart || options.includeHistogram) {
    if (hasContentOnCurrentPage && y > 130) {
      doc.addPage();
      y = margin + 4;
      hasContentOnCurrentPage = false;
    }

    drawSectionTitle(
      '2. Visualizações Analíticas',
      'Gráficos renderizados em alta resolução diretamente a partir da série ativa.'
    );

    if (options.includeMonthlyChart) {
      const monthlyImg = renderMonthlyChartImage(mensal);
      if (monthlyImg) {
        const imgH = (contentW * 560) / 1400;
        ensureSpace(imgH + 6);
        doc.addImage(monthlyImg, 'PNG', margin, y, contentW, imgH);
        y += imgH + 7;
      }
    }

    if (options.includeHistogram) {
      const histImg = renderHistogramChartImage(rainHist);
      if (histImg) {
        const imgH = (contentW * 540) / 1400;
        ensureSpace(imgH + 22);
        doc.addImage(histImg, 'PNG', margin, y, contentW, imgH);
        y += imgH + 4;

        // Compact histogram stats callout row
        doc.setFillColor(248, 250, 252);
        doc.setDrawColor(226, 232, 240);
        doc.roundedRect(margin, y, contentW, 12, 2, 2, 'FD');
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(8);
        doc.setTextColor(51, 65, 85);
        const histSummaryLine = pdfText(
          `Horas chuvosas (> 0 mm): ${brNumber(rainHist.rainyCount, 0)} h  |  Mediana: ${brNumber(rainHist.median)} mm  |  Q3: ${brNumber(rainHist.q3)} mm  |  Limite IQR: ${brNumber(rainHist.upperFence)} mm/h  |  Extremos: ${brNumber(rainHist.extremeCount, 0)} (${brNumber(rainHist.extremePct, 1)}%)  |  Pico: ${brNumber(rainHist.maxVal)} mm/h`
        );
        const wrapped = doc.splitTextToSize(histSummaryLine, contentW - 6);
        doc.text(wrapped, margin + 3, y + 5.2);
        y += 17;
      }
    }
  }

  // =========================================================================
  // SECTION 3: MISSING DATA BY COLUMN, QUALITY AUDIT & CORRELATION
  // =========================================================================
  if (options.includeQualityAndCorr) {
    if (hasContentOnCurrentPage && y > 105) {
      doc.addPage();
      y = margin + 4;
      hasContentOnCurrentPage = false;
    }

    drawSectionTitle(
      '3. Auditoria de Qualidade, Lacunas e Correlação',
      `Verificação de integridade física/temporal, dados faltantes por coluna (alerta > ${MISSING_ALERT_THRESHOLD_PCT}%) e correlação de Pearson.`
    );

    // 3A. Missing data by column
    ensureSpace(16 + missingCols.length * 6);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9.5);
    doc.setTextColor(30, 41, 59);
    doc.text('Dados Faltantes por Coluna (Nulos / NaN)', margin, y);
    y += 4;

    const mCols = [
      { header: 'Coluna', x: margin + 2, align: 'left' as const },
      { header: 'Válidos', x: margin + 96, align: 'right' as const },
      { header: 'Faltantes', x: margin + 122, align: 'right' as const },
      { header: '% Faltante', x: margin + 148, align: 'right' as const },
      { header: 'Situação', x: margin + contentW - 2, align: 'right' as const },
    ];
    doc.setFillColor(241, 245, 249);
    doc.rect(margin, y, contentW, 6.8, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7.8);
    doc.setTextColor(71, 85, 105);
    mCols.forEach((c) => doc.text(pdfText(c.header), c.x, y + 4.7, { align: c.align }));
    y += 6.8;

    missingCols.forEach((col, idx) => {
      ensureSpace(6);
      if (col.exceedsThreshold) {
        doc.setFillColor(254, 242, 242);
        doc.rect(margin, y, contentW, 5.8, 'F');
      } else if (idx % 2 === 1) {
        doc.setFillColor(248, 250, 252);
        doc.rect(margin, y, contentW, 5.8, 'F');
      }

      doc.setFont('helvetica', col.exceedsThreshold ? 'bold' : 'normal');
      doc.setFontSize(8.1);
      if (col.exceedsThreshold) doc.setTextColor(185, 28, 28);
      else doc.setTextColor(15, 23, 42);
      doc.text(pdfText(`${col.label} (${col.key})`), mCols[0].x, y + 4.1);

      doc.setFont('helvetica', 'normal');
      doc.setTextColor(15, 23, 42);
      doc.text(brNumber(col.validCount, 0), mCols[1].x, y + 4.1, { align: 'right' });
      doc.text(brNumber(col.missingCount, 0), mCols[2].x, y + 4.1, { align: 'right' });

      doc.setFont('helvetica', 'bold');
      if (col.exceedsThreshold) doc.setTextColor(185, 28, 28);
      else if (col.missingCount > 0) doc.setTextColor(180, 83, 9);
      else doc.setTextColor(5, 150, 105);
      doc.text(`${brNumber(col.missingPct, 2)}%`, mCols[3].x, y + 4.1, { align: 'right' });

      const status = col.exceedsThreshold
        ? 'Crítico (> 10%)'
        : col.missingCount > 0
          ? 'Lacunas leves (<= 10%)'
          : 'Completa';
      doc.text(pdfText(status), mCols[4].x, y + 4.1, { align: 'right' });
      y += 5.8;
    });
    doc.setDrawColor(226, 232, 240);
    doc.setLineWidth(0.25);
    doc.line(margin, y, margin + contentW, y);
    y += 8;

    // 3B. Side-by-side Quality Audit + Pearson Correlation Matrix
    ensureSpace(74);
    const leftW = contentW * 0.54;
    const rightX = margin + leftW + 6;
    const rightW = contentW - leftW - 6;
    const blockStartY = y;

    // Left: Quality Audit Table
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9.5);
    doc.setTextColor(30, 41, 59);
    doc.text('Auditoria de Qualidade (Base Completa)', margin, y);
    y += 4;

    const qualityItems = [
      { label: 'Lacunas de timestamp', val: report.timestamps_ausentes, warn: report.timestamps_ausentes > 0 },
      { label: 'Timestamps duplicados', val: report.timestamps_duplicados, warn: report.timestamps_duplicados > 0 },
      { label: 'Chuva negativa', val: report.chuva_negativa, warn: report.chuva_negativa > 0 },
      { label: 'Chuva > limite físico (150 mm/h)', val: report.chuva_extrema_fisica, warn: report.chuva_extrema_fisica > 0 },
      { label: 'Violação física (Máxima < Mínima)', val: report.temp_inconsistente, warn: report.temp_inconsistente > 0 },
      { label: 'Outliers chuva (IQR horas chuvosas)', val: report.outliers_iqr.precipitacao_mm, warn: false },
      { label: 'Outliers térmicos (IQR máx./mín.)', val: report.outliers_iqr.temp_max_c + report.outliers_iqr.temp_min_c, warn: false },
    ];

    doc.setFillColor(241, 245, 249);
    doc.rect(margin, y, leftW, 6.4, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7.6);
    doc.setTextColor(71, 85, 105);
    doc.text('Indicador', margin + 2, y + 4.4);
    doc.text('Ocorrências', margin + leftW - 2, y + 4.4, { align: 'right' });
    y += 6.4;

    qualityItems.forEach((qi, idx) => {
      if (idx % 2 === 1) {
        doc.setFillColor(248, 250, 252);
        doc.rect(margin, y, leftW, 5.8, 'F');
      }
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(15, 23, 42);
      doc.text(pdfText(qi.label), margin + 2, y + 4.1);
      doc.setFont('helvetica', 'bold');
      if (qi.warn) doc.setTextColor(180, 83, 9);
      else doc.setTextColor(15, 23, 42);
      doc.text(brNumber(qi.val, 0), margin + leftW - 2, y + 4.1, { align: 'right' });
      y += 5.8;
    });

    // Right: Pearson Correlation Matrix
    let ry = blockStartY;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9.5);
    doc.setTextColor(30, 41, 59);
    doc.text('Correlação de Pearson (r)', rightX, ry);
    ry += 5;

    const shortLabels = ['Chuva', 'T. Máx.', 'T. Mín.'];
    const labelColW = 19;
    const cellW = (rightW - labelColW) / 3;
    const cellH = 11;

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7.6);
    doc.setTextColor(71, 85, 105);
    shortLabels.forEach((lbl, cIdx) => {
      doc.text(pdfText(lbl), rightX + labelColW + cIdx * cellW + cellW / 2, ry + 3.5, { align: 'center' });
    });
    ry += 5.5;

    corr.values.forEach((rowVals, rIdx) => {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7.6);
      doc.setTextColor(71, 85, 105);
      doc.text(pdfText(shortLabels[rIdx]), rightX, ry + cellH / 2 + 1.5);

      rowVals.forEach((val, cIdx) => {
        const cx = rightX + labelColW + cIdx * cellW;
        if (val === null) {
          doc.setFillColor(241, 245, 249);
        } else if (val >= 0) {
          const intensity = Math.min(1, val);
          doc.setFillColor(
            255,
            Math.round(240 - intensity * 120),
            Math.round(240 - intensity * 120)
          );
        } else {
          const intensity = Math.min(1, Math.abs(val));
          doc.setFillColor(
            Math.round(240 - intensity * 125),
            Math.round(248 - intensity * 60),
            255
          );
        }
        doc.setDrawColor(226, 232, 240);
        doc.rect(cx, ry, cellW - 1, cellH - 1, 'FD');

        doc.setFont('helvetica', 'bold');
        doc.setFontSize(8.2);
        doc.setTextColor(15, 23, 42);
        doc.text(
          val !== null ? brNumber(val, 2) : '-',
          cx + (cellW - 1) / 2,
          ry + (cellH - 1) / 2 + 1.5,
          { align: 'center' }
        );
      });
      ry += cellH;
    });

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.4);
    doc.setTextColor(100, 116, 139);
    const noteLines = doc.splitTextToSize(
      pdfText('Escala: +1,00 indica correlação linear positiva perfeita; -1,00 indica correlação inversa perfeita.'),
      rightW
    );
    doc.text(noteLines, rightX, ry + 4);
  }

  // =========================================================================
  // FOOTER ON EVERY PAGE
  // =========================================================================
  const totalPages = doc.getNumberOfPages();
  for (let p = 1; p <= totalPages; p++) {
    doc.setPage(p);
    doc.setDrawColor(226, 232, 240);
    doc.setLineWidth(0.25);
    doc.line(margin, pageH - 12, pageW - margin, pageH - 12);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(100, 116, 139);
    doc.text(pdfText(`CLIMAPS · ${stationName} (${stationCode}) · ${scopeLabel}`), margin, pageH - 7.5);
    doc.text(`Página ${p} de ${totalPages}`, pageW - margin, pageH - 7.5, { align: 'right' });
  }

  const stamp = getStamp();
  const safeStation = safeFilename(stationName.toLowerCase()).slice(0, 28) || 'estacao';
  const filename = `climaps_relatorio_${safeStation}_${stamp}.pdf`;
  doc.save(filename);
  return filename;
}
