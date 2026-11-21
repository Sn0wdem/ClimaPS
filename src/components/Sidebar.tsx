import React, { useRef, useState } from 'react';
import {
  BarChart3,
  CloudRainWind,
  Download,
  FileSpreadsheet,
  GitCompare,
  Globe,
  LineChart,
  Moon,
  Search,
  SlidersHorizontal,
  Sun,
  Table2,
  Upload,
  X,
} from 'lucide-react';
import type { FilterSpec, SavedFileEntry } from '../types/weather';

export type TabKey = 'mundo' | 'comp' | 'resumo' | 'graficos' | 'tabela' | 'explorador' | 'exportar';

interface SidebarProps {
  activeTab: TabKey;
  onSelectTab: (tab: TabKey) => void;
  isDark: boolean;
  onChangeTheme: (dark: boolean) => void;
  savedFiles: SavedFileEntry[];
  selectedFileId: string;
  onSelectFileId: (id: string) => void;
  onLoadSavedFile: (id: string) => Promise<void>;
  onUploadCsv: (file: File) => Promise<void>;
  loadingFile: boolean;
  fileError: string | null;
  hasDataset: boolean;
  minDate: string;
  maxDate: string;
  filterSpec: FilterSpec;
  onChangeFilter: (next: FilterSpec) => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

const MONITORING_NAV: Array<{ key: TabKey; label: string; icon: React.ComponentType<{ size?: number }> }> = [
  { key: 'mundo', label: 'Mundo Ao Vivo', icon: Globe },
  { key: 'comp', label: 'Comparar Anos', icon: GitCompare },
];

const ANALYSIS_NAV: Array<{ key: TabKey; label: string; icon: React.ComponentType<{ size?: number }> }> = [
  { key: 'resumo', label: 'Resumo e Qualidade', icon: BarChart3 },
  { key: 'graficos', label: 'Gráficos e Correlação', icon: LineChart },
  { key: 'tabela', label: 'Tabela Editável', icon: Table2 },
  { key: 'explorador', label: 'Explorador', icon: Search },
  { key: 'exportar', label: 'Exportar CSV / SQL', icon: Download },
];

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  isDark,
  onChangeTheme,
  savedFiles,
  selectedFileId,
  onSelectFileId,
  onLoadSavedFile,
  onUploadCsv,
  loadingFile,
  fileError,
  hasDataset,
  minDate,
  maxDate,
  filterSpec,
  onChangeFilter,
  mobileOpen,
  onCloseMobile,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFile = async (file: File | undefined) => {
    if (!file) return;
    await onUploadCsv(file);
  };

  const renderNavItem = (item: { key: TabKey; label: string; icon: React.ComponentType<{ size?: number }> }) => {
    const Icon = item.icon;
    const isActive = activeTab === item.key;
    return (
      <button
        key={item.key}
        type="button"
        onClick={() => {
          onSelectTab(item.key);
          onCloseMobile();
        }}
        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[0.86rem] transition-colors cursor-pointer text-left whitespace-nowrap"
        style={{
          backgroundColor: isActive ? 'var(--accent-soft)' : 'transparent',
          color: isActive ? 'var(--accent-text)' : 'var(--text-secondary)',
          fontWeight: isActive ? 600 : 500,
        }}
      >
        <Icon size={16} />
        <span className="truncate">{item.label}</span>
      </button>
    );
  };

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/55 z-30 lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      <aside
        className={`fixed lg:sticky top-0 left-0 z-40 h-screen w-[272px] shrink-0 flex flex-col transition-transform duration-200 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderRight: '1px solid var(--border-hairline)',
        }}
      >
        {/* Brand Header */}
        <div
          className="h-[58px] px-5 flex items-center justify-between shrink-0"
          style={{ borderBottom: '1px solid var(--border-hairline)' }}
        >
          <button
            type="button"
            onClick={() => onSelectTab('mundo')}
            className="flex items-center gap-2.5 bg-transparent border-0 p-0 cursor-pointer"
          >
            <span
              className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
              style={{ backgroundColor: 'var(--accent-soft)', color: 'var(--accent-text)' }}
            >
              <CloudRainWind size={16} />
            </span>
            <span
              className="font-display text-[1.05rem] font-bold tracking-tight whitespace-nowrap"
              style={{ color: 'var(--text-primary)' }}
            >
              CLIMAPS
            </span>
          </button>

          <button
            type="button"
            onClick={onCloseMobile}
            className="lg:hidden p-1.5 rounded-md cursor-pointer bg-transparent border-0"
            style={{ color: 'var(--text-muted)' }}
            aria-label="Fechar menu"
          >
            <X size={18} />
          </button>
        </div>

        {/* Scrollable Navigation & Data Controls */}
        <div className="flex-1 overflow-y-auto px-3.5 py-4 space-y-5">
          {/* Navigation Groups */}
          <nav aria-label="Navegação principal" className="space-y-4">
            <div className="space-y-0.5">
              <div
                className="px-3 pb-1.5 text-[0.72rem] font-semibold tracking-wide"
                style={{ color: 'var(--text-muted)' }}
              >
                Monitoramento
              </div>
              {MONITORING_NAV.map(renderNavItem)}
            </div>

            <div className="space-y-0.5">
              <div
                className="px-3 pb-1.5 flex items-center justify-between text-[0.72rem] font-semibold tracking-wide"
                style={{ color: 'var(--text-muted)' }}
              >
                <span>Análise Histórica</span>
                {!hasDataset && <span className="font-normal opacity-75">Sem CSV</span>}
              </div>
              {ANALYSIS_NAV.map(renderNavItem)}
            </div>
          </nav>

          <hr style={{ borderColor: 'var(--border-hairline)' }} />

          {/* CSV Dataset Loader */}
          <div className="px-1 space-y-2.5">
            <div className="flex items-center gap-2 text-[0.78rem] font-semibold" style={{ color: 'var(--text-primary)' }}>
              <FileSpreadsheet size={14} style={{ color: 'var(--text-muted)' }} />
              <span>Base Histórica (CSV)</span>
            </div>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragActive(false);
                void handleFile(e.dataTransfer.files?.[0]);
              }}
              className="rounded-lg p-3 text-center transition-colors"
              style={{
                backgroundColor: 'var(--bg-subtle)',
                border: `1px dashed ${dragActive ? 'var(--accent)' : 'var(--border-strong)'}`,
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={(e) => {
                  void handleFile(e.target.files?.[0]);
                  e.target.value = '';
                }}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={loadingFile}
                className="btn-secondary w-full text-[0.8rem] py-1.5"
              >
                <Upload size={14} />
                <span>Importar INMET / ClimaPS</span>
              </button>
              <p className="mt-1.5 mb-0 text-[0.73rem]" style={{ color: 'var(--text-muted)' }}>
                Arraste ou selecione um arquivo .csv
              </p>
            </div>

            {fileError && (
              <div
                className="rounded-lg px-3 py-2 text-[0.78rem]"
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.25)',
                  color: 'var(--danger)',
                }}
              >
                {fileError}
              </div>
            )}

            {savedFiles.length > 0 && (
              <div className="space-y-2 pt-1">
                <label className="block text-[0.75rem] font-medium" style={{ color: 'var(--text-muted)' }}>
                  Arquivos disponíveis
                </label>
                <select
                  value={selectedFileId}
                  onChange={(e) => onSelectFileId(e.target.value)}
                  className="field-input text-[0.8rem] py-1.5"
                >
                  {savedFiles.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.folder}/{f.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => void onLoadSavedFile(selectedFileId)}
                  disabled={loadingFile || !selectedFileId}
                  className="btn-primary w-full text-[0.8rem] py-1.5"
                >
                  {loadingFile ? 'Carregando...' : 'Carregar base selecionada'}
                </button>
              </div>
            )}
          </div>

          {/* Active Dataset Filters */}
          {hasDataset && (
            <>
              <hr style={{ borderColor: 'var(--border-hairline)' }} />
              <div className="px-1 space-y-3">
                <div className="flex items-center gap-2 text-[0.78rem] font-semibold" style={{ color: 'var(--text-primary)' }}>
                  <SlidersHorizontal size={14} style={{ color: 'var(--text-muted)' }} />
                  <span>Filtros do Recorte</span>
                </div>

                <div className="space-y-2">
                  <label className="block text-[0.74rem] font-medium" style={{ color: 'var(--text-muted)' }}>
                    Período
                  </label>
                  <div className="grid grid-cols-1 gap-1.5">
                    <input
                      type="date"
                      value={filterSpec.start}
                      min={minDate}
                      max={filterSpec.end || maxDate}
                      onChange={(e) =>
                        onChangeFilter({ ...filterSpec, start: e.target.value || minDate })
                      }
                      className="field-input font-mono-tabular text-[0.78rem] py-1.5"
                      aria-label="Data inicial"
                    />
                    <input
                      type="date"
                      value={filterSpec.end}
                      min={filterSpec.start || minDate}
                      max={maxDate}
                      onChange={(e) =>
                        onChangeFilter({ ...filterSpec, end: e.target.value || maxDate })
                      }
                      className="field-input font-mono-tabular text-[0.78rem] py-1.5"
                      aria-label="Data final"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[0.74rem]">
                    <span style={{ color: 'var(--text-muted)' }}>Janela horária</span>
                    <span className="font-mono-tabular font-medium" style={{ color: 'var(--accent-text)' }}>
                      {String(filterSpec.hourStart).padStart(2, '0')}h – {String(filterSpec.hourEnd).padStart(2, '0')}h
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[0.72rem]" style={{ color: 'var(--text-muted)' }}>
                    <span className="w-7">Início</span>
                    <input
                      type="range"
                      min={0}
                      max={23}
                      value={filterSpec.hourStart}
                      onChange={(e) => {
                        const v = Number(e.target.value);
                        onChangeFilter({
                          ...filterSpec,
                          hourStart: v,
                          hourEnd: Math.max(v, filterSpec.hourEnd),
                        });
                      }}
                      className="w-full accent-sky-500"
                    />
                  </div>
                  <div className="flex items-center gap-2 text-[0.72rem]" style={{ color: 'var(--text-muted)' }}>
                    <span className="w-7">Fim</span>
                    <input
                      type="range"
                      min={0}
                      max={23}
                      value={filterSpec.hourEnd}
                      onChange={(e) => {
                        const v = Number(e.target.value);
                        onChangeFilter({
                          ...filterSpec,
                          hourStart: Math.min(filterSpec.hourStart, v),
                          hourEnd: v,
                        });
                      }}
                      className="w-full accent-sky-500"
                    />
                  </div>
                </div>

                <label className="flex items-center gap-2.5 pt-0.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filterSpec.rainyOnly}
                    onChange={(e) =>
                      onChangeFilter({ ...filterSpec, rainyOnly: e.target.checked })
                    }
                    className="w-4 h-4 accent-sky-500 rounded"
                  />
                  <span className="text-[0.8rem]" style={{ color: 'var(--text-secondary)' }}>
                    Somente horas com chuva
                  </span>
                </label>
              </div>
            </>
          )}
        </div>

        {/* Bottom Theme Switcher */}
        <div
          className="px-4 py-3 shrink-0"
          style={{ borderTop: '1px solid var(--border-hairline)' }}
        >
          <div className="segmented-track w-full">
            <button
              type="button"
              onClick={() => onChangeTheme(true)}
              className={`segmented-item flex-1 justify-center ${isDark ? 'segmented-item-active' : ''}`}
            >
              <Moon size={13} />
              <span>Escuro</span>
            </button>
            <button
              type="button"
              onClick={() => onChangeTheme(false)}
              className={`segmented-item flex-1 justify-center ${!isDark ? 'segmented-item-active' : ''}`}
            >
              <Sun size={13} />
              <span>Claro</span>
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};
