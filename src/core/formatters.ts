export function brNumber(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || Number.isNaN(value) || !Number.isFinite(value)) {
    return '-';
  }
  const fixed = value.toFixed(decimals);
  const [intPart, decPart] = fixed.split('.');
  const formattedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return decPart !== undefined ? `${formattedInt},${decPart}` : formattedInt;
}

export function formatDatetimeFriendly(value: string | null | undefined): string {
  if (!value) return '-';
  if (value.includes(' às ')) return value;

  // Match ISO like YYYY-MM-DDTHH:MM or YYYY-MM-DD HH:MM(:SS)
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/);
  if (match) {
    const [, y, m, d, hh = '00', mm = '00'] = match;
    return `${d}/${m}/${y} às ${hh}:${mm}`;
  }
  return value;
}

export function formatDateTimeBR(value: string | null | undefined): string {
  if (!value) return '-';
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/);
  if (match) {
    const [, y, m, d, hh = '00', mm = '00'] = match;
    return `${d}/${m}/${y} ${hh}:${mm}`;
  }
  return value;
}

export function formatDateBR(isoDate: string): string {
  const match = isoDate.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return isoDate;
  return `${match[3]}/${match[2]}/${match[1]}`;
}

export function safeFilename(name: string): string {
  const base = name.split(/[/\\]/).pop() || 'dados.csv';
  const cleaned = base.replace(/[^A-Za-z0-9_.-]+/g, '_').replace(/^[._]+|[._]+$/g, '');
  return cleaned || 'dados.csv';
}

export function getStamp(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}
