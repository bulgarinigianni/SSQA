// SSQA v2 — main App entry point

const App = () => {
  const [apiKey, setApiKey] = React.useState(() => localStorage.getItem('gemini_api_key') || '');
  const [showApiModal, setShowApiModal] = React.useState(!localStorage.getItem('gemini_api_key'));
  const [activeTab, setActiveTab] = React.useState('single');
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);

  // Single
  const [singleFile, setSingleFile] = React.useState(null);
  const [singleResult, setSingleResult] = React.useState(null);
  const [singleLoading, setSingleLoading] = React.useState(false);
  const [singleError, setSingleError] = React.useState(null);

  // Batch
  const [batchFiles, setBatchFiles] = React.useState([]);
  const [batchResults, setBatchResults] = React.useState(null);
  const [batchLoading, setBatchLoading] = React.useState(false);
  const [batchError, setBatchError] = React.useState(null);

  const saveApiKey = key => {
    setApiKey(key);
    localStorage.setItem('gemini_api_key', key);
  };

  const analyzeSingle = async () => {
    setSingleLoading(true);
    setSingleError(null);
    const fd = new FormData();
    fd.append('file', singleFile);
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'X-Gemini-API-Key': apiKey },
        body: fd,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      setSingleResult(data);
    } catch (e) {
      setSingleError(e.message);
    } finally {
      setSingleLoading(false);
    }
  };

  const analyzeBatch = async () => {
    setBatchLoading(true);
    setBatchError(null);
    const fd = new FormData();
    batchFiles.forEach(f => fd.append('files', f));
    try {
      const res = await fetch('/api/analyze/batch', {
        method: 'POST',
        headers: { 'X-Gemini-API-Key': apiKey },
        body: fd,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      setBatchResults(Array.isArray(data) ? data : []);
    } catch (e) {
      setBatchError(e.message);
    } finally {
      setBatchLoading(false);
    }
  };

  return (
    <div className="app">
      {showApiModal && (
        <ApiKeyModal
          currentKey={apiKey}
          onSave={saveApiKey}
          onClose={() => setShowApiModal(false)}
        />
      )}

      <HHeader apiKeySet={!!apiKey} onApiKeyEdit={() => setShowApiModal(true)} />
      <HTabs active={activeTab} onTabChange={tab => {
        setActiveTab(tab);
        setSingleError(null);
        setBatchError(null);
      }} />

      <div className={`layout ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <HSidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(v => !v)} />
        <div className="main">
          <div className="container">
            {activeTab === 'single' ? (
              singleResult ? (
                <SingleResult
                  result={singleResult}
                  filename={singleFile?.name || 'paper.pdf'}
                  onReset={() => { setSingleResult(null); setSingleFile(null); setSingleError(null); }}
                />
              ) : (
                <UploadScreen
                  apiKey={apiKey}
                  file={singleFile}
                  onFile={f => { setSingleFile(f); setSingleError(null); }}
                  onAnalyze={analyzeSingle}
                  loading={singleLoading}
                  error={singleError}
                />
              )
            ) : (
              batchResults ? (
                <BatchResultsScreen
                  results={batchResults}
                  onReset={() => { setBatchResults(null); setBatchFiles([]); setBatchError(null); }}
                />
              ) : (
                <BatchUploadScreen
                  apiKey={apiKey}
                  files={batchFiles}
                  onFiles={setBatchFiles}
                  onAnalyze={analyzeBatch}
                  loading={batchLoading}
                  error={batchError}
                />
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
