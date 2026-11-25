import type { ColumnMissingStat, StationDataset, WeatherRecord } from '../types/weather';

const COLUNAS_INTERNAS: Record<string, string> = {
  'Data Medicao': 'data',
  'Hora Medicao': 'hora',
  'PRECIPITACAO TOTAL, HORARIO(mm)': 'precipitacao_mm',
  'TEMPERATURA MAXIMA NA HORA ANT. (AUT)(°C)': 'temp_max_c',
  'TEMPERATURA MINIMA NA HORA ANT. (AUT)(°C)': 'temp_min_c',
};

const NA_VALUES = new Set(['', '-9999', '-9999,0', '-9999.0', 'null', 'NULL', 'NaN', 'nan', 'None']);

function normalizarChave(texto: string): string {
  return texto
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

function localizarCabecalho(linhas: string[]): number {
  for (let i = 0; i < linhas.length; i++) {
    const limpa = linhas[i].replace(/^\ufeff/, '').trim().toLowerCase();
    if (limpa.startsWith('data medicao') || limpa.includes('data medicao;') || limpa.includes('data medicao,')) {
      return i;
    }
    if (limpa.includes('precipitacao_mm') && (limpa.includes('temp_max_c') || limpa.includes('data'))) {
      return i;
    }
    if (limpa.includes('data_hora') && (limpa.includes('temp') || limpa.includes('precipitacao') || limpa.includes('chuva'))) {
      return i;
    }
  }
  throw new Error(
    "Cabeçalho de dados meteorológicos não encontrado no arquivo CSV. O arquivo deve conter o padrão do INMET ('Data Medicao') ou o padrão exportado do ClimaPS ('data_hora', 'precipitacao_mm')."
  );
}

function parseNumeric(raw: string | undefined, decimalSep: ',' | '.'): number | null {
  if (raw === undefined) return null;
  const trimmed = raw.trim().replace(/^"|"$/g, '');
  if (NA_VALUES.has(trimmed)) return null;
  const normalized = decimalSep === ',' ? trimmed.replace(',', '.') : trimmed;
  const num = Number(normalized);
  return Number.isFinite(num) ? num : null;
}

function parseDateTimeComponents(dateStr: string, hourStr?: string): {
  dia: string;
  dataHora: string;
  horaNum: number;
  mes: number;
  timestamp: number;
} | null {
  const cleanDate = dateStr.trim().replace(/^"|"$/g, '');
  if (!cleanDate) return null;

  // Pattern 1: YYYY-MM-DD HH:MM(:SS) or YYYY-MM-DDTHH:MM(:SS)
  const fullIso = cleanDate.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?/);
  if (fullIso) {
    const y = Number(fullIso[1]);
    const m = Number(fullIso[2]);
    const d = Number(fullIso[3]);
    let hh = fullIso[4] !== undefined ? Number(fullIso[4]) : 0;
    let mm = fullIso[5] !== undefined ? Number(fullIso[5]) : 0;
    const ss = fullIso[6] !== undefined ? Number(fullIso[6]) : 0;

    if (fullIso[4] === undefined && hourStr !== undefined) {
      const digits = hourStr.trim().replace(/[^0-9]/g, '');
      if (digits.length > 0) {
        const padded = digits.padStart(4, '0');
        hh = Number(padded.slice(0, 2));
        mm = Number(padded.slice(2, 4));
      }
    }

    if (m < 1 || m > 12 || d < 1 || d > 31 || hh < 0 || hh > 23) return null;
    const pad2 = (n: number) => String(n).padStart(2, '0');
    const dia = `${y}-${pad2(m)}-${pad2(d)}`;
    const dataHora = `${dia} ${pad2(hh)}:${pad2(mm)}:${pad2(ss)}`;
    const timestamp = Date.UTC(y, m - 1, d, hh, mm, ss);
    return { dia, dataHora, horaNum: hh, mes: m, timestamp };
  }

  // Pattern 2: DD/MM/YYYY (HH:MM)
  const brMatch = cleanDate.match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2}))?/);
  if (brMatch) {
    const d = Number(brMatch[1]);
    const m = Number(brMatch[2]);
    const y = Number(brMatch[3]);
    let hh = brMatch[4] !== undefined ? Number(brMatch[4]) : 0;
    let mm = brMatch[5] !== undefined ? Number(brMatch[5]) : 0;

    if (brMatch[4] === undefined && hourStr !== undefined) {
      const digits = hourStr.trim().replace(/[^0-9]/g, '');
      if (digits.length > 0) {
        const padded = digits.padStart(4, '0');
        hh = Number(padded.slice(0, 2));
        mm = Number(padded.slice(2, 4));
      }
    }

    if (m < 1 || m > 12 || d < 1 || d > 31 || hh < 0 || hh > 23) return null;
    const pad2 = (n: number) => String(n).padStart(2, '0');
    const dia = `${y}-${pad2(m)}-${pad2(d)}`;
    const dataHora = `${dia} ${pad2(hh)}:${pad2(mm)}:00`;
    const timestamp = Date.UTC(y, m - 1, d, hh, mm, 0);
    return { dia, dataHora, horaNum: hh, mes: m, timestamp };
  }

  return null;
}

export function parseStationCsv(csvText: string, sourceName = 'upload.csv'): StationDataset {
  const cleanText = csvText.replace(/^\ufeff/, '');
  const linhas = cleanText.split(/\r?\n/);
  const headerIndex = localizarCabecalho(linhas);

  const metadata: Record<string, string> = {};
  for (let i = 0; i < headerIndex; i++) {
    const line = linhas[i];
    const colonIdx = line.indexOf(':');
    if (colonIdx !== -1) {
      const chave = line.slice(0, colonIdx);
      const valor = line.slice(colonIdx + 1).trim();
      const normKey = normalizarChave(chave);
      if (normKey) metadata[normKey] = valor;
    }
  }

  const headerLine = linhas[headerIndex].replace(/^\ufeff/, '');
  const sep = headerLine.includes(';') ? ';' : ',';
  const decimalSep: ',' | '.' = sep === ';' ? ',' : '.';

  const rawHeaders = headerLine.split(sep).map((h) => h.trim().replace(/^"|"$/g, ''));
  const mappedHeaders = rawHeaders.map((h) => COLUNAS_INTERNAS[h] ?? h);

  const colIndex = (name: string): number => mappedHeaders.indexOf(name);

  let idxRain = colIndex('precipitacao_mm');
  if (idxRain === -1) idxRain = colIndex('chuva_mm');
  if (idxRain === -1) idxRain = colIndex('chuva');

  let idxMax = colIndex('temp_max_c');
  if (idxMax === -1) idxMax = colIndex('temperatura_c');
  if (idxMax === -1) idxMax = colIndex('temp_c');

  let idxMin = colIndex('temp_min_c');
  if (idxMin === -1) idxMin = idxMax;

  if (idxRain === -1) throw new Error("Coluna obrigatória ausente no CSV: 'precipitacao_mm'");
  if (idxMax === -1) throw new Error("Coluna obrigatória ausente no CSV: 'temp_max_c'");

  const idxDataHora = colIndex('data_hora');
  const idxData = colIndex('data');
  const idxHora = colIndex('hora');

  if (idxDataHora === -1 && idxData === -1) {
    throw new Error("O CSV precisa conter uma coluna de data/hora ('data_hora' ou 'data').");
  }

  const coreMappedIndices = new Set<number>([idxRain, idxMax, idxMin, idxDataHora, idxData, idxHora].filter((i) => i >= 0));
  const ignoredDerivedNames = new Set(['hora_num', 'mes', 'dia']);
  const extraColDefs: Array<{ idx: number; key: string; label: string; missingCount: number }> = [];
  rawHeaders.forEach((rawName, idx) => {
    const trimmed = rawName.trim();
    const mapped = mappedHeaders[idx];
    if (!trimmed || coreMappedIndices.has(idx) || ignoredDerivedNames.has(mapped)) return;
    extraColDefs.push({
      idx,
      key: normalizarChave(trimmed) || `col_${idx}`,
      label: trimmed,
      missingCount: 0,
    });
  });

  const records: WeatherRecord[] = [];
  for (let i = headerIndex + 1; i < linhas.length; i++) {
    const line = linhas[i].trim();
    if (!line) continue;
    const cols = line.split(sep);

    const parsedDt =
      idxDataHora !== -1 && cols[idxDataHora]?.trim()
        ? parseDateTimeComponents(cols[idxDataHora])
        : parseDateTimeComponents(cols[idxData] ?? '', idxHora !== -1 ? cols[idxHora] : undefined);

    if (!parsedDt) continue;

    for (let e = 0; e < extraColDefs.length; e++) {
      const def = extraColDefs[e];
      const cell = (cols[def.idx] ?? '').trim().replace(/^"|"$/g, '');
      if (NA_VALUES.has(cell) || cell.toLowerCase() === 'na' || cell.toLowerCase() === 'n/a') {
        def.missingCount++;
      }
    }

    const rain = parseNumeric(cols[idxRain], decimalSep);
    const tMax = parseNumeric(cols[idxMax], decimalSep);
    const tMin = idxMin !== -1 ? parseNumeric(cols[idxMin], decimalSep) : tMax;

    records.push({
      id: i,
      data: parsedDt.dia,
      hora: parsedDt.horaNum * 100,
      data_hora: parsedDt.dataHora,
      timestamp: parsedDt.timestamp,
      precipitacao_mm: rain,
      temp_max_c: tMax,
      temp_min_c: tMin,
      hora_num: parsedDt.horaNum,
      mes: parsedDt.mes,
      dia: parsedDt.dia,
    });
  }

  records.sort((a, b) => a.timestamp - b.timestamp);
  records.forEach((r, idx) => {
    r.id = idx;
  });

  const totalRows = records.length;
  const extraColumnMissing: ColumnMissingStat[] = extraColDefs.map((def) => {
    const missingPct = totalRows > 0 ? (def.missingCount / totalRows) * 100 : 0;
    return {
      key: def.key,
      label: def.label,
      total: totalRows,
      missingCount: def.missingCount,
      validCount: totalRows - def.missingCount,
      missingPct,
      exceedsThreshold: missingPct > 10,
      source: 'extra',
    };
  });

  if (Object.keys(metadata).length === 0) {
    const stem = sourceName.replace(/\.csv$/i, '');
    const cleanName = stem
      .replace('climaps_dados_', '')
      .replace('dados_editados_', '')
      .replace(/_/g, ' ')
      .trim();
    metadata.nome = cleanName ? cleanName.toUpperCase() : 'ARQUIVO CSV';
    metadata.codigo_estacao = 'EXPORT';
    metadata.fonte = 'ClimaPS / Exportação';
  }

  return {
    metadata,
    data: records,
    sourceName,
    extraColumnMissing: extraColumnMissing.length > 0 ? extraColumnMissing : undefined,
  };
}

function formatNumCsv(val: number | null): string {
  if (val === null || Number.isNaN(val)) return '';
  return String(val).replace('.', ',');
}

export function buildCsvExport(records: WeatherRecord[], headerMeta?: string[]): string {
  const cols = [
    'data',
    'hora',
    'precipitacao_mm',
    'temp_max_c',
    'temp_min_c',
    'data_hora',
    'hora_num',
    'mes',
    'dia',
  ];

  const lines: string[] = [];
  if (headerMeta && headerMeta.length > 0) {
    lines.push(...headerMeta);
  }
  lines.push(cols.join(';'));

  for (let i = 0; i < records.length; i++) {
    const r = records[i];
    lines.push(
      [
        r.data,
        String(r.hora),
        formatNumCsv(r.precipitacao_mm),
        formatNumCsv(r.temp_max_c),
        formatNumCsv(r.temp_min_c),
        r.data_hora.slice(0, 16),
        String(r.hora_num),
        String(r.mes),
        r.dia,
      ].join(';')
    );
  }

  return '\ufeff' + lines.join('\n') + '\n';
}

function sqlValue(value: string | number | null, isString: boolean): string {
  if (value === null || value === undefined || (typeof value === 'number' && Number.isNaN(value))) {
    return 'NULL';
  }
  if (isString) {
    return `'${String(value).replace(/'/g, "''")}'`;
  }
  return String(value);
}

export function buildSqlScript(records: WeatherRecord[]): string {
  const columns = [
    'data',
    'hora',
    'data_hora',
    'precipitacao_mm',
    'temp_max_c',
    'temp_min_c',
    'hora_num',
    'mes',
    'dia',
  ];

  const lines: string[] = [
    'DROP TABLE IF EXISTS observacoes_meteorologicas;',
    'CREATE TABLE observacoes_meteorologicas (',
    '    data DATE,',
    '    hora INTEGER,',
    '    data_hora TIMESTAMP,',
    '    precipitacao_mm REAL,',
    '    temp_max_c REAL,',
    '    temp_min_c REAL,',
    '    hora_num INTEGER,',
    '    mes INTEGER,',
    '    dia DATE',
    ');',
    '',
  ];

  for (let i = 0; i < records.length; i++) {
    const r = records[i];
    const values = [
      sqlValue(r.data, true),
      sqlValue(r.hora, false),
      sqlValue(r.data_hora, true),
      sqlValue(r.precipitacao_mm, false),
      sqlValue(r.temp_max_c, false),
      sqlValue(r.temp_min_c, false),
      sqlValue(r.hora_num, false),
      sqlValue(r.mes, false),
      sqlValue(r.dia, true),
    ].join(', ');
    lines.push(`INSERT INTO observacoes_meteorologicas (${columns.join(', ')}) VALUES (${values});`);
  }

  return lines.join('\n') + '\n';
}

export function identifyYearAndName(dataset: StationDataset): { nome: string; ano: string } {
  const rawName = dataset.metadata.nome || dataset.metadata.codigo_estacao || dataset.sourceName.replace(/\.csv$/i, '');
  const nome = rawName
    .replace(/^climaps_/i, '')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());

  let ano = dataset.metadata.ano;
  if (!ano && dataset.data.length > 0) {
    ano = dataset.data[0].dia.slice(0, 4);
  }
  return { nome, ano: ano || 'Série' };
}
