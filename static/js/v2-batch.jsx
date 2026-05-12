// SSQA v2 — batch upload screen + batch results

const BatchUploadScreen = ({ apiKey, files, onFiles, onAnalyze, loading, error }) => {
  const inputRef = React.useRef();
  const [dragging, setDragging] = React.useState(false);

  const addFiles = newFiles => {
    const pdfs = Array.from(newFiles).filter(f => f.type === 'application/pdf');
    onFiles(prev => {
      const existing = new Set(prev.map(f => f.name));
      return [...prev, ...pdfs.filter(f => !existing.has(f.name))].slice(0, 10);
    });
  };

  const removeFile = name => onFiles(prev => prev.filter(f => f.name !== name));

  const handleDrop = e => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const totalMB = files.reduce((s, f) => s + f.size, 0) / 1024 / 1024;

  return (
    <>
      {!apiKey && (
        <div className="alert-banner">
          ⚠️ Inserisci la tua API key Gemini cliccando sull'indicatore in alto a destra per abilitare l'analisi.
        </div>
      )}

      <div className="card">
        <h2>Analisi Batch</h2>
        <p className="sub">Carica fino a 10 PDF per confrontarli in un'unica run. I paper vengono analizzati in parallelo.</p>

        <div
          className={`drop ${dragging ? 'drag-over' : ''}`}
          style={{ padding: '32px 24px' }}
          onDrop={handleDrop}
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onClick={() => inputRef.current.click()}
        >
          <div className="drop-icon" style={{ fontSize: 32 }}>📁</div>
          <div className="drop-text">
            Trascina i PDF qui, oppure <strong>seleziona file</strong>
            <div style={{ fontSize: 12, marginTop: 4 }}>Puoi selezionare più file contemporaneamente · max 10</div>
          </div>
          <input ref={inputRef} type="file" accept=".pdf" multiple style={{ display: 'none' }}
            onChange={e => addFiles(e.target.files)} />
        </div>

        {files.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <div className="row between" style={{ marginBottom: 8 }}>
              <span className="eyebrow">{files.length} file · {totalMB.toFixed(2)} MB totali</span>
              <button className="btn btn-secondary btn-small" onClick={() => onFiles([])}>Rimuovi tutti</button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {files.map(f => (
                <div key={f.name} className="file-tag" style={{ justifyContent: 'space-between' }}>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>📄 {f.name}</span>
                  <div className="row" style={{ gap: 8, flexShrink: 0 }}>
                    <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{(f.size / 1024 / 1024).toFixed(2)} MB</span>
                    <span className="x" onClick={() => removeFile(f.name)}>✕</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {error && <div className="error-banner">❌ {error}</div>}

        <div style={{ marginTop: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
          <button className="btn btn-primary" disabled={files.length === 0 || !apiKey || loading} onClick={onAnalyze}>
            {loading
              ? <><span className="spinner"></span> Analisi in corso ({files.length} PDF)...</>
              : `Analizza ${files.length > 0 ? files.length + ' ' : ''}Paper`}
          </button>
          {files.length > 0 && !loading && (
            <button className="btn btn-secondary" onClick={() => onFiles([])}>Pulisci</button>
          )}
        </div>

        {loading && (
          <div className="progress-wrap">
            <div className="progress-track">
              <div className="progress-fill" style={{ width: '60%', animation: 'indeterminate 2s ease-in-out infinite' }}></div>
            </div>
            <div className="progress-label">Gemini sta analizzando i paper in parallelo — potrebbe richiedere qualche minuto</div>
            <style>{`@keyframes indeterminate { 0%{width:5%} 60%{width:75%} 100%{width:5%} }`}</style>
          </div>
        )}
      </div>
    </>
  );
};

const BatchResultsScreen = ({ results, onReset }) => {
  const [expanded, setExpanded] = React.useState(null);

  const categoryOrder = ['gold_standard', 'practical_evidence', 'exploratory', 'weak', 'black_flag'];
  const sorted = [...results].sort((a, b) => {
    const ai = categoryOrder.indexOf(a.scoring.category);
    const bi = categoryOrder.indexOf(b.scoring.category);
    if (ai !== bi) return ai - bi;
    return b.scoring.final_score - a.scoring.final_score;
  });

  const counts = {};
  results.forEach(r => { counts[r.scoring.category] = (counts[r.scoring.category] || 0) + 1; });

  const summaryDefs = [
    { key: 'gold_standard',      label: '🥇 Gold Standard',     cls: 'cat-gold_standard' },
    { key: 'practical_evidence', label: '🔵 Practical Evidence', cls: 'cat-practical_evidence' },
    { key: 'exploratory',        label: '🔬 Exploratory',        cls: 'cat-exploratory' },
    { key: 'weak',               label: '⚠️ Weak',              cls: 'cat-weak' },
    { key: 'black_flag',         label: '🏴 Black Flag',         cls: 'cat-black_flag' },
  ];

  const totalTime = results.reduce((s, r) => s + 0, 0);

  return (
    <>
      <div className="card compact" style={{ marginBottom: 18 }}>
        <div className="row between">
          <div className="row">
            <span className="eyebrow">RUN</span>
            <span style={{ fontWeight: 600 }}>{results.length} PDF analizzati</span>
          </div>
          <button className="btn btn-secondary btn-small" onClick={onReset}>↺ Nuovo batch</button>
        </div>
      </div>

      <div className="summary-row">
        {summaryDefs.filter(d => counts[d.key]).map(d => (
          <span key={d.key} className={`summary-pill ${d.cls}`}>
            {d.label} · {counts[d.key]}
          </span>
        ))}
      </div>

      {sorted.map((r, i) => {
        const ed = r.extracted;
        const sc = r.scoring;
        const isExpanded = expanded === i;
        const qualityPct = Math.round(sc.normalized_score);

        let toolLabel = sc.methodology_tool || 'Generic';
        if (sc.pedro_score != null) toolLabel += ` ${sc.pedro_score}/10`;
        else if (sc.nos_score != null) toolLabel += ` ${sc.nos_score}/9`;
        else if (sc.amstar2_met != null) toolLabel += ` ${sc.amstar2_met}/16`;

        const authorsStr = Array.isArray(ed.authors) ? ed.authors.slice(0, 2).join(', ') + (ed.authors.length > 2 ? ' et al.' : '') : '';

        return (
          <div key={i} className={`batch-row ${isExpanded ? 'expanded' : ''}`}>
            <div className="batch-row-head" onClick={() => setExpanded(isExpanded ? null : i)}>
              <span className={`cat-badge cat-${sc.category}`} style={{ minWidth: 150, textAlign: 'center', flexShrink: 0 }}>
                {sc.category_label}
              </span>
              <Ring pct={qualityPct} size={36} stroke={4} />
              <div className="name">
                {ed.title || r.filename || `Paper ${i + 1}`}
                {sc.predatory_journal_detected && <span className="mini-pill" style={{ marginLeft: 8, background: '#fef2f2', color: '#dc2626' }}>🏴 predatory</span>}
              </div>
              <span className="meta">{toolLabel}</span>
              {ed.sample_size && <span className="meta">n={ed.sample_size}</span>}
              <span className="score">{sc.final_score.toFixed(1)}<span className="cap"> /{sc.design_cap.toFixed(1)}</span></span>
              <button className="btn btn-secondary btn-small" style={{ minWidth: 90, flexShrink: 0 }}>
                {isExpanded ? 'Chiudi ▴' : 'Dettagli →'}
              </button>
            </div>

            {isExpanded && (
              <div className="batch-row-body">
                <div className="card" style={{ marginBottom: 14 }}>
                  <div className="result-header" style={{ borderBottom: 'none', marginBottom: 0, paddingBottom: 0 }}>
                    <Ring pct={qualityPct} />
                    <div>
                      <span className={`cat-badge cat-${sc.category}`}>{sc.category_label}</span>
                      <div className="result-title" style={{ marginTop: 10 }}>{ed.title || 'Titolo non estratto'}</div>
                      <div className="result-subtitle">
                        {[authorsStr, ed.journal, ed.year].filter(Boolean).join(' · ')}
                      </div>
                      <div className="score-stats">
                        <div className="score-stat">
                          <div className="num">{sc.final_score.toFixed(1)}<span className="cap"> /{sc.design_cap.toFixed(1)}</span></div>
                          <div className="lbl">Score / Cap</div>
                        </div>
                        <div style={{ borderLeft: '1px solid #e2e5ea' }}></div>
                        <div className="score-stat">
                          <div className="num" style={{ fontSize: 18 }}>{toolLabel}</div>
                          <div className="lbl">Tool</div>
                        </div>
                        {ed.sample_size && <>
                          <div style={{ borderLeft: '1px solid #e2e5ea' }}></div>
                          <div className="score-stat">
                            <div className="num" style={{ fontSize: 18 }}>n={ed.sample_size}</div>
                            <div className="lbl">{ed.population_type || 'partecipanti'}</div>
                          </div>
                        </>}
                      </div>
                    </div>
                  </div>
                </div>

                {sc.explanation && (
                  <div className="explanation" style={{ marginBottom: 14 }}>
                    <strong className="eyebrow">Verdetto AI</strong>
                    {sc.explanation}
                  </div>
                )}

                {ed.main_findings_summary && (
                  <div className="card" style={{ marginBottom: 14 }}>
                    <h3>Main finding</h3>
                    <p style={{ fontSize: 13.5, lineHeight: 1.65 }}>{ed.main_findings_summary}</p>
                  </div>
                )}

                <div className="card compact" style={{ marginBottom: 14 }}>
                  <h3>Score breakdown</h3>
                  <div className="brk">
                    <BRow label={`Base (${sc.methodology_tool || 'Generic'})`} val={sc.base_methodology_score.toFixed(1)} />
                    {((sc.sample_size_adjustment || 0) + (sc.large_sample_bonus || 0)) !== 0 && (
                      <BRow label="Sample bonus" val={`+${((sc.sample_size_adjustment || 0) + (sc.large_sample_bonus || 0)).toFixed(1)}`} />
                    )}
                    {sc.institutional_bonus > 0 && <BRow label="Istituzione elite" val={`+${sc.institutional_bonus.toFixed(1)}`} />}
                    {sc.journal_bonus > 0 && <BRow label="Journal elite" val={`+${sc.journal_bonus.toFixed(1)}`} />}
                    {sc.registered_protocol_bonus > 0 && <BRow label="Protocollo registrato" val={`+${sc.registered_protocol_bonus.toFixed(1)}`} />}
                    {sc.coi_penalty !== 0 && <BRow label="CoI penalty" val={sc.coi_penalty.toFixed(1)} muted />}
                    {sc.predatory_journal_detected && <BRow label="Predatory → 1.0" val="FLAG" muted />}
                    <div className="brk-row total">
                      <span className="lbl">Final</span>
                      <span className="val">{sc.final_score.toFixed(1)}</span>
                    </div>
                  </div>
                </div>

                {r.confidence && (
                  <div className="conf-row">
                    <span className="conf-label">Extraction confidence</span>
                    <div className="conf-bar">
                      <div className={`conf-fill ${r.confidence.level === 'high' ? 'high' : r.confidence.level === 'medium' ? 'med' : 'low'}`}
                        style={{ width: Math.round(r.confidence.confidence_pct) + '%' }}></div>
                    </div>
                    <span className="conf-text"
                      style={{ color: r.confidence.level === 'high' ? '#059669' : r.confidence.level === 'medium' ? '#ca8a04' : '#dc2626', fontSize: 11 }}>
                      {r.confidence.level?.toUpperCase()} · {r.confidence.extracted_fields}/{r.confidence.total_fields}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </>
  );
};

window.BatchUploadScreen = BatchUploadScreen;
window.BatchResultsScreen = BatchResultsScreen;
