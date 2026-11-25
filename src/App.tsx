import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, X } from 'lucide-react';
import type { FilterSpec, SavedFileEntry, StationDataset, WeatherRecord } from './types/weather';
import { applyFilters } from './core/analysis';
import { parseStationCsv } from './core/dataLoader';
import { getStamp, safeFilename } from './core/formatters';
import { HeaderBanner } from './components/HeaderBanner';
import { Sidebar, type TabKey } from './components/Sidebar';
import { WorldLiveTab } from './components/WorldLiveTab';
import { ComparisonTab } from './components/ComparisonTab';
import {
  ChartsTab,
  EditableTableTab,
  ExplorerTab,
  ExportTab,
  HistoricalEmptyState,
  SummaryTab,
} from './components/AnalyticsTabs';

const INITIAL_SAVED_FILES: SavedFileEntry[] = [
  {
    id: 'sample_a101_2014',
    folder: 'data',
    name: 'dados_A101_H_2014.csv',
    url: '/data/dados_A101_H_2014.csv',
  },
];

export default function App() {
  const [isDark, setIsDark] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>('mundo');
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const [savedFiles, setSavedFiles] = useState<SavedFileEntry[]>(INITIAL_SAVED_FILES);
  const [selectedFileId, setSelectedFileId] = useState<string>(INITIAL_SAVED_FILES[0].id);
  const [loadingFile, setLoadingFile] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  const [dataset, setDataset] = useState<StationDataset | null>(null);
  const [records, setRecords] = useState<WeatherRecord[]>([]);
  const [filterSpec, setFilterSpec] = useState<FilterSpec>({
    start: '',
    end: '',
    hourStart: 0,
    hourEnd: 23,
    rainyOnly: false,
  });

  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
  }, [isDark]);

  const showToast = useCallback((message: string) => {
    setToast(message);
    window.setTimeout(() => {
      setToast((prev) => (prev === message ? null : prev));
    }, 4200);
  }, []);

  const activateDataset = useCallback(
    (ds: StationDataset, toastMessage?: string) => {
      setDataset(ds);
      setRecords(ds.data);
      if (ds.data.length > 0) {
        const minD = ds.data[0].dia;
        const maxD = ds.data[ds.data.length - 1].dia;
        setFilterSpec({
          start: minD,
          end: maxD,
          hourStart: 0,
          hourEnd: 23,
          rainyOnly: false,
        });
      }
      if (toastMessage) showToast(toastMessage);
    },
    [showToast]
  );

  const resolveSavedDataset = useCallback(async (entry: SavedFileEntry): Promise<StationDataset> => {
    if (entry.dataset) return entry.dataset;
    if (entry.csvText) {
      return parseStationCsv(entry.csvText, entry.name);
    }
    if (entry.url) {
      const resp = await fetch(entry.url);
      if (!resp.ok) throw new Error(`Falha ao carregar ${entry.name} (HTTP ${resp.status})`);
      const text = await resp.text();
      return parseStationCsv(text, entry.name);
    }
    throw new Error(`Fonte de arquivo inválida: ${entry.name}`);
  }, []);

  const handleLoadSavedFile = useCallback(
    async (fileId: string) => {
      const entry = savedFiles.find((f) => f.id === fileId);
      if (!entry) return;
      setLoadingFile(true);
      setFileError(null);
      try {
        const ds = await resolveSavedDataset(entry);
        activateDataset(ds, `Base carregada: ${entry.name}`);
        setMobileSidebarOpen(false);
      } catch (err) {
        setFileError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoadingFile(false);
      }
    },
    [savedFiles, resolveSavedDataset, activateDataset]
  );

  const handleUploadCsv = useCallback(
    async (file: File) => {
      setLoadingFile(true);
      setFileError(null);
      try {
        const text = await file.text();
        const savedName = `${getStamp()}_${safeFilename(file.name)}`;
        const ds = parseStationCsv(text, savedName);
        const newEntry: SavedFileEntry = {
          id: `imp_${Date.now()}`,
          folder: 'importados',
          name: savedName,
          csvText: text,
          dataset: ds,
        };
        setSavedFiles((prev) => [prev[0], newEntry, ...prev.slice(1)]);
        setSelectedFileId(newEntry.id);
        activateDataset(ds, `Arquivo importado: ${savedName}`);
        setMobileSidebarOpen(false);
      } catch (err) {
        setFileError(`Erro ao carregar o arquivo CSV: ${err instanceof Error ? err.message : String(err)}`);
      } finally {
        setLoadingFile(false);
      }
    },
    [activateDataset]
  );

  const handleLoadFromWorld = useCallback(
    (ds: StationDataset, message: string, csvText?: string) => {
      if (csvText) {
        const newEntry: SavedFileEntry = {
          id: `world_${Date.now()}`,
          folder: 'importados',
          name: ds.sourceName,
          csvText,
          dataset: ds,
        };
        setSavedFiles((prev) => {
          const filtered = prev.filter((f) => f.name !== ds.sourceName);
          return [filtered[0], newEntry, ...filtered.slice(1)];
        });
        setSelectedFileId(newEntry.id);
      }
      activateDataset(ds, message);
    },
    [activateDataset]
  );

  const handleSaveExportCopy = useCallback(
    (filename: string, csvText: string) => {
      try {
        const ds = parseStationCsv(csvText, filename);
        const entry: SavedFileEntry = {
          id: `exp_${Date.now()}`,
          folder: 'exportacoes',
          name: filename,
          csvText,
          dataset: ds,
        };
        setSavedFiles((prev) => [...prev, entry]);
        showToast(`Cópia salva em exportacoes/${filename}`);
      } catch {
        showToast(`Cópia registrada: ${filename}`);
      }
    },
    [showToast]
  );

  const { minDate, maxDate } = useMemo(() => {
    if (records.length === 0) return { minDate: '', maxDate: '' };
    return {
      minDate: records[0].dia,
      maxDate: records[records.length - 1].dia,
    };
  }, [records]);

  const filteredRecords = useMemo(() => {
    if (records.length === 0) return [];
    return applyFilters(records, filterSpec);
  }, [records, filterSpec]);

  const hasDataset = dataset !== null && records.length > 0;

  return (
    <div
      className="min-h-screen flex"
      style={{ backgroundColor: 'var(--bg-canvas)', color: 'var(--text-primary)' }}
    >
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        isDark={isDark}
        onChangeTheme={setIsDark}
        savedFiles={savedFiles}
        selectedFileId={selectedFileId}
        onSelectFileId={setSelectedFileId}
        onLoadSavedFile={handleLoadSavedFile}
        onUploadCsv={handleUploadCsv}
        loadingFile={loadingFile}
        fileError={fileError}
        hasDataset={hasDataset}
        minDate={minDate}
        maxDate={maxDate}
        filterSpec={filterSpec}
        onChangeFilter={setFilterSpec}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <HeaderBanner
          activeTab={activeTab}
          dataset={dataset}
          recordCount={records.length}
          loadingFile={loadingFile}
          onToggleSidebar={() => setMobileSidebarOpen((v) => !v)}
          onQuickLoadSample={() => void handleLoadSavedFile(INITIAL_SAVED_FILES[0].id)}
          onGoToExport={() => setActiveTab('exportar')}
        />

        <main className="flex-1 px-4 sm:px-6 lg:px-8 py-6 max-w-[1440px] mx-auto w-full">
          {activeTab === 'mundo' && (
            <WorldLiveTab
              isDark={isDark}
              activeRecords={hasDataset ? records : null}
              onLoadDatasetIntoSession={handleLoadFromWorld}
            />
          )}

          {activeTab === 'comp' && (
            <ComparisonTab
              isDark={isDark}
              savedFiles={savedFiles}
              resolveSavedDataset={resolveSavedDataset}
            />
          )}

          {activeTab !== 'mundo' && activeTab !== 'comp' && !hasDataset && (
            <HistoricalEmptyState
              loadingFile={loadingFile}
              onLoadSample={() => void handleLoadSavedFile(INITIAL_SAVED_FILES[0].id)}
              onGoToWorld={() => setActiveTab('mundo')}
            />
          )}

          {hasDataset && activeTab === 'resumo' && (
            <SummaryTab
              filtered={filteredRecords}
              fullRecords={records}
              extraColumns={dataset?.extraColumnMissing}
              isDark={isDark}
            />
          )}

          {hasDataset && activeTab === 'graficos' && (
            <ChartsTab filtered={filteredRecords} isDark={isDark} />
          )}

          {hasDataset && activeTab === 'tabela' && (
            <EditableTableTab
              records={records}
              onSaveEdits={(updated) => {
                setRecords(updated);
                if (dataset) setDataset({ ...dataset, data: updated });
                showToast('Edições salvas na sessão atual.');
              }}
            />
          )}

          {hasDataset && activeTab === 'explorador' && <ExplorerTab filtered={filteredRecords} />}

          {hasDataset && dataset && activeTab === 'exportar' && (
            <ExportTab
              dataset={dataset}
              fullRecords={records}
              filtered={filteredRecords}
              filterSpec={filterSpec}
              onSaveExportCopy={handleSaveExportCopy}
            />
          )}
        </main>
      </div>

      {/* Toast Notification */}
      {toast && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-5 right-5 z-50 pl-3.5 pr-3 py-2.5 rounded-xl shadow-lg text-[0.84rem] font-medium flex items-center gap-2.5 max-w-[380px]"
          style={{
            backgroundColor: 'var(--bg-surface)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-strong)',
          }}
        >
          <CheckCircle2 size={16} className="shrink-0" style={{ color: 'var(--nominal)' }} />
          <span className="truncate">{toast}</span>
          <button
            type="button"
            onClick={() => setToast(null)}
            className="p-0.5 rounded bg-transparent border-0 cursor-pointer shrink-0"
            style={{ color: 'var(--text-muted)' }}
            aria-label="Fechar notificação"
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
