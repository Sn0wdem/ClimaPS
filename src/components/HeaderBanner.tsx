import React from 'react';
import { Download, FileSpreadsheet, Menu } from 'lucide-react';
import type { StationDataset } from '../types/weather';
import type { TabKey } from './Sidebar';
import { brNumber } from '../core/formatters';

interface HeaderBannerProps {
  activeTab: TabKey;
  dataset: StationDataset | null;
  recordCount: number;
  loadingFile: boolean;
  onToggleSidebar: () => void;
  onQuickLoadSample: () => void;
  onGoToExport: () => void;
}

const TAB_TITLES: Record<TabKey, string> = {
  mundo: 'Mundo Ao Vivo',
  comp: 'Comparar Anos',
  resumo: 'Resumo e Qualidade',
  graficos: 'Gráficos e Correlação',
  tabela: 'Tabela Editável',
  explorador: 'Explorador de Registros',
  exportar: 'Exportar Dados',
};

export const HeaderBanner: React.FC<HeaderBannerProps> = ({
  activeTab,
  dataset,
  recordCount,
  loadingFile,
  onToggleSidebar,
  onQuickLoadSample,
  onGoToExport,
}) => {
  return (
    <header
      className="sticky top-0 z-20 h-[58px] px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-6"
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-hairline)',
      }}
    >
      {/* Left Zone: Breadcrumb + quiet unboxed station metadata */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="lg:hidden p-1.5 rounded-lg border cursor-pointer shrink-0"
          style={{
            backgroundColor: 'var(--bg-subtle)',
            borderColor: 'var(--border-hairline)',
            color: 'var(--text-primary)',
          }}
          aria-label="Abrir navegação"
        >
          <Menu size={18} />
        </button>

        <div className="flex items-center gap-2 min-w-0 text-[0.88rem]">
          <span className="font-display font-semibold whitespace-nowrap shrink-0" style={{ color: 'var(--text-primary)' }}>
            {TAB_TITLES[activeTab]}
          </span>

          {dataset && recordCount > 0 ? (
            <div
              className="hidden md:flex items-center gap-2 text-[0.8rem] min-w-0 truncate"
              style={{ color: 'var(--text-muted)' }}
            >
              <span aria-hidden="true">/</span>
              <span className="truncate" style={{ color: 'var(--text-secondary)' }}>
                {dataset.metadata.nome || 'Estação'}
              </span>
              <span aria-hidden="true">·</span>
              <span className="font-mono-tabular whitespace-nowrap">
                {dataset.metadata.codigo_estacao || 'CSV'}
              </span>
              <span aria-hidden="true">·</span>
              <span className="font-mono-tabular whitespace-nowrap">
                {brNumber(recordCount, 0)} registros
              </span>
            </div>
          ) : (
            <div
              className="hidden md:flex items-center gap-2 text-[0.8rem] truncate"
              style={{ color: 'var(--text-muted)' }}
            >
              <span aria-hidden="true">/</span>
              <span className="truncate">Open-Meteo · Reanálise ERA5 · Séries INMET</span>
            </div>
          )}
        </div>
      </div>

      {/* Right Zone: Single focused contextual action */}
      <div className="shrink-0">
        {dataset && recordCount > 0 ? (
          <button
            type="button"
            onClick={onGoToExport}
            className="btn-secondary text-[0.82rem] py-1.5 px-3.5"
          >
            <Download size={14} />
            <span>Exportar base</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={onQuickLoadSample}
            disabled={loadingFile}
            className="btn-primary text-[0.82rem] py-1.5 px-3.5"
          >
            <FileSpreadsheet size={14} />
            <span>{loadingFile ? 'Carregando...' : 'Abrir Manaus 2014'}</span>
          </button>
        )}
      </div>
    </header>
  );
};
