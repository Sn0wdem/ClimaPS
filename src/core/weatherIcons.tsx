import React from 'react';
import {
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudLightning,
  CloudRain,
  CloudSun,
  Sun,
} from 'lucide-react';

/** Removes leading emoji glyphs from WMO strings so typography stays clean and uniform. */
export function cleanConditionText(raw: string): string {
  return raw
    .replace(/^[\p{Extended_Pictographic}\uFE0F\u200D\s]+/u, '')
    .trim() || raw;
}

export const WeatherConditionIcon: React.FC<{ condition: string; size?: number; className?: string }> = ({
  condition,
  size = 18,
  className = '',
}) => {
  const lower = condition.toLowerCase();
  if (lower.includes('tempestade') || lower.includes('granizo')) {
    return <CloudLightning size={size} className={className} />;
  }
  if (lower.includes('chuva') || lower.includes('pancadas')) {
    return <CloudRain size={size} className={className} />;
  }
  if (lower.includes('garoa')) {
    return <CloudDrizzle size={size} className={className} />;
  }
  if (lower.includes('neblina') || lower.includes('nevoeiro')) {
    return <CloudFog size={size} className={className} />;
  }
  if (lower.includes('nublado') && !lower.includes('parcialmente')) {
    return <Cloud size={size} className={className} />;
  }
  if (lower.includes('parcialmente') || lower.includes('predominantemente')) {
    return <CloudSun size={size} className={className} />;
  }
  return <Sun size={size} className={className} />;
};
