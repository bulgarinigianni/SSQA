// SSQA v2 — atoms, upload screen, single result

// ─── Atoms ───────────────────────────────────────────────

const HHeader = ({ apiKeySet, onApiKeyEdit }) => (
  <header className="hdr">
    <div className="hdr-logo">SQ</div>
    <h1>Sport Science Quality Analyzer <span>v2.0</span></h1>
    <div className="hdr-status" onClick={onApiKeyEdit} title="Clicca per modificare la API key">
      <div className={`status-dot ${apiKeySet ? '' : 'offline'}`}></div>
      <span>{apiKeySet ? 'API key configurata' : 'API key mancante — clicca per aggiungere'}</span>
    </div>
  </header>
);

const HTabs = ({ active, onTabChange }) => (
  <nav className="tabs">
    <button className={`tab ${active === 'single' ? 'active' : ''}`} onClick={() => onTabChange('single')}>Singolo PDF</button>
    <button className={`tab ${active === 'batch' ? 'active' : ''}`} onClick={() => onTabChange('batch')}>Analisi Batch</button>
  </nav>
);

const HSidebar = ({ collapsed, onToggle }) => {
  if (collapsed) {
    return (
      <aside className="sidebar collapsed-rail">
        <button className="sidebar-toggle" onClick={onToggle} title="Espandi">›</button>
      </aside>
    );
  }
  return (
    <aside className="sidebar">
      <div className="row between" style={{ marginBottom: 10 }}>
        <h4 style={{ margin: 0 }}>Verdict scale</h4>
        <button className="sidebar-toggle" onClick={onToggle} title="Collassa">‹</button>
      </div>
      <div className="sidebar-section">
        <div className="scale-row"><span className="cat-badge cat-gold_standard">🥇 Gold</span><span className="rng">≥ 8.5</span></div>
        <div className="scale-row"><span className="cat-badge cat-practical_evidence">🔵 Practical</span><span className="rng">7.0–8.4</span></div>
        <div className="scale-row"><span className="cat-badge cat-exploratory">🔬 Explor.</span><span className="rng">5.0–6.9</span></div>
        <div className="scale-row"><span className="cat-badge cat-weak">⚠️ Weak</span><span className="rng">&lt; 5.0</span></div>
        <div className="scale-row"><span className="cat-badge cat-black_flag">🏴 Black</span><span className="rng">predatory</span></div>
      </div>
      <div className="sidebar-section">
        <h4>Quality % (ring)</h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
          <span className="chip chip-gold">Excellent ≥ 85%</span>
          <span className="chip chip-silver">Good 70–84%</span>
          <span className="chip chip-bronze">Fair 50–69%</span>
          <span className="chip chip-blue">Poor 30–49%</span>
          <span className="chip chip-black">Critical &lt; 30%</span>
        </div>
      </div>
      <div className="sidebar-section">
        <h4>Methodology tools</h4>
        <div className="method-row"><strong>PEDro</strong><span className="arrow">→</span><span className="applies">RCT</span></div>
        <div className="method-row"><strong>AMSTAR-2</strong><span className="arrow">→</span><span className="applies">Meta / SR</span></div>
        <div className="method-row"><strong>NOS</strong><span className="arrow">→</span><span className="applies">Cohort / CS</span></div>
        <div className="method-row"><strong>GRADE</strong><span className="arrow">→</span><span className="applies">Consensus</span></div>
        <div className="method-row"><strong>Generic</strong><span className="arrow">→</span><span className="applies">Case / Review</span></div>
      </div>
      <div className="sidebar-section">
        <h4>Bonuses / Penalties</h4>
        <div style={{ fontSize: 12, lineHeight: 1.8, color: 'var(--text-secondary)' }}>
          <div>Elite institution <span className="mono" style={{ color: 'var(--green)' }}>+0.5</span></div>
          <div>Elite journal <span className="mono" style={{ color: 'var(--green)' }}>+0.5</span></div>
          <div>Registered protocol <span className="mono" style={{ color: 'var(--green)' }}>+0.5</span></div>
          <div>N ≥ 100 <span className="mono" style={{ color: 'var(--green)' }}>+0.4</span></div>
          <div>N ≥ 50 <span className="mono" style={{ color: 'var(--green)' }}>+0.3</span></div>
          <div>CoI obvio <span className="mono" style={{ color: 'var(--red)' }}>−3.0</span></div>
          <div>Predatory <span className="mono" style={{ color: 'var(--red)' }}>→ 1.0</span></div>
        </div>
      </div>
    </aside>
  );
};

const Ring = ({ pct, size = 100, stroke = 6 }) => {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - pct / 100);
  const color = pct >= 85 ? '#ca8a04' : pct >= 70 ? '#475569' : pct >= 50 ? '#9a3412' : pct >= 30 ? '#2563eb' : '#111827';
  return (
    <div className="score-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#e2e5ea" strokeWidth={stroke} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={c} strokeDashoffset={off} strokeLinecap="round"
          transform={`rotate(-90 ${size/2} ${size/2})`} />
      </svg>
      <div className="ring-center" style={{ color, fontSize: size * 0.22 }}>{pct}%</div>
    </div>
  );
};

const Banner = ({ tone, icon, children }) => (
  <div className={`banner ${tone}`}>
    <div className="banner-icon">{icon}</div>
    <div style={{ flex: 1 }}>{children}</div>
  </div>
);

const Crit = ({ code, ok }) => {
  const cls = ok === null || ok === undefined ? 'unknown' : ok ? 'ok' : 'no';
  const sym = ok === null || ok === undefined ? '·' : ok ? '✓' : '✗';
  return (
    <div className={`crit ${cls}`} title={code}>
      <span>{sym}</span>
      <span>{code}</span>
    </div>
  );
};

const BRow = ({ label, val, note, bar, muted }) => (
  <div className={`brk-row ${muted ? 'muted-row' : ''}`}>
    <span className="lbl">{label}</span>
    {bar != null && <span className="bar"><i style={{ width: Math.min(bar, 100) + '%' }}></i></span>}
    {note && <span className="note">{note}</span>}
    <span className="val">{val}</span>
  </div>
);

// ─── API Key Modal ────────────────────────────────────────

const ApiKeyModal = ({ currentKey, onSave, onClose }) => {
  const [val, setVal] = React.useState(currentKey || '');
  const submit = () => { if (val.trim()) { onSave(val.trim()); onClose(); } };
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>Gemini API Key</h2>
        <p className="sub">Richiesta per analizzare i PDF. Salvata solo nel tuo browser (localStorage).</p>
        <input
          type="password"
          className="api-input"
          placeholder="AIzaSy..."
          value={val}
          onChange={e => setVal(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit()}
          autoFocus
        />
        <span className="modal-link">
          Non hai ancora una chiave? <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">Ottienila gratis su Google AI Studio →</a>
        </span>
        <div className="row" style={{ gap: 8, marginTop: 20 }}>
          <button className="btn btn-primary" onClick={submit} disabled={!val.trim()}>Salva</button>
          {currentKey && <button className="btn btn-secondary" onClick={onClose}>Annulla</button>}
        </div>
      </div>
    </div>
  );
};

// ─── Upload Screen (Single) ───────────────────────────────

const UploadScreen = ({ apiKey, file, onFile, onAnalyze, loading, error }) => {
  const inputRef = React.useRef();
  const [dragging, setDragging] = React.useState(false);

  const handleDrop = e => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && f.type === 'application/pdf') onFile(f);
  };

  return (
    <>
      {!apiKey && (
        <div className="alert-banner">
          ⚠️ Inserisci la tua API key Gemini cliccando sull'indicatore in alto a destra per abilitare l'analisi.
        </div>
      )}
      <div className="card">
        <h2>Upload Research Paper</h2>
        <p className="sub">Carica un PDF per la valutazione di qualità metodologica. Max 50 MB · Abstract, Methods e Funding estratti automaticamente.</p>

        {file ? (
          <div style={{ marginBottom: 8 }}>
            <div className="file-tag">
              📄 {file.name}
              <span className="x" onClick={() => onFile(null)}>✕</span>
            </div>
            <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>{(file.size / 1024 / 1024).toFixed(2)} MB</div>
          </div>
        ) : (
          <div
            className={`drop ${dragging ? 'drag-over' : ''}`}
            onDrop={handleDrop}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onClick={() => inputRef.current.click()}
          >
            <div className="drop-icon">📄</div>
            <div className="drop-text">Trascina il PDF qui, oppure <strong>seleziona file</strong></div>
            <input ref={inputRef} type="file" accept=".pdf" style={{ display: 'none' }}
              onChange={e => { if (e.target.files[0]) onFile(e.target.files[0]); }} />
          </div>
        )}

        {error && <div className="error-banner">❌ {error}</div>}

        <div style={{ marginTop: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
          <button className="btn btn-primary" disabled={!file || !apiKey || loading} onClick={onAnalyze}>
            {loading ? <><span className="spinner"></span> Analisi in corso...</> : 'Analizza Paper'}
          </button>
          {file && !loading && <button className="btn btn-secondary" onClick={() => onFile(null)}>Pulisci</button>}
        </div>
      </div>

      <div className="card">
        <h2>Come funziona</h2>
        <p className="sub">Pipeline di estrazione e scoring automatica.</p>
        <ol style={{ paddingLeft: 18, fontSize: 13.5, lineHeight: 1.9, color: '#1a1d23' }}>
          <li><b>Estrazione</b> · L'AI legge abstract, metodi, sample, funding e conflitti di interessi</li>
          <li><b>Selezione strumento</b> · PEDro (RCT) / AMSTAR-2 (SR/Meta) / NOS (Cohort) / GRADE (Consensus) / Generic</li>
          <li><b>Scoring</b> · Punteggio grezzo + bonus istituzione/rivista/sample + penalty CoI</li>
          <li><b>Verdetto</b> · Scala 5 tier (Gold → Black Flag) + ring di qualità normalizzato per confronto equo</li>
        </ol>
        <div className="row wrap" style={{ gap: 6, marginTop: 14 }}>
          <span className="chip chip-silver">⚡ caching 24h</span>
          <span className="chip chip-silver">🛡 CoI detector</span>
          <span className="chip chip-silver">🏴 predatory check</span>
        </div>
      </div>
    </>
  );
};

// ─── Single Result Screen ─────────────────────────────────
// Field mapping from AnalysisResult:
//   result.extracted   → ExtractedData
//   result.scoring     → ScoringBreakdown
//   scoring.category, scoring.category_label, scoring.explanation, scoring.normalized_score
//   extracted.sample_size, extracted.population_type, extracted.conflict_of_interest_statement
//   extracted.main_findings_summary, extracted.authors (list), extracted.registered_protocol
//   scoring.base_methodology_score, scoring.institutional_bonus, scoring.journal_bonus
//   scoring.registered_protocol_bonus, scoring.sample_size_adjustment, scoring.large_sample_bonus
//   scoring.predatory_journal_detected, scoring.methodology_tool
//   confidence.extracted_fields, confidence.total_fields, confidence.level

const SingleResult = ({ result, filename, onReset }) => {
  const ed = result.extracted;
  const sc = result.scoring;
  const confidence = result.confidence;
  const qualityPct = Math.round(sc.normalized_score);
  const category = sc.category;
  const categoryLabel = sc.category_label;
  const explanation = sc.explanation;

  const renderMethodology = () => {
    const tool = sc.methodology_tool;

    if (tool === 'PEDro' && ed.pedro_criteria) {
      const p = ed.pedro_criteria;
      const crits = [
        { code: 'C1', ok: p.c1_eligibility_specified },
        { code: 'C2', ok: p.c2_random_allocation },
        { code: 'C3', ok: p.c3_concealed_allocation },
        { code: 'C4', ok: p.c4_baseline_comparable },
        { code: 'C5', ok: p.c5_blinding_subjects },
        { code: 'C6', ok: p.c6_blinding_therapists },
        { code: 'C7', ok: p.c7_blinding_assessors },
        { code: 'C8', ok: p.c8_adequate_followup },
        { code: 'C9', ok: p.c9_intention_to_treat },
        { code: 'C10', ok: p.c10_between_group },
        { code: 'C11', ok: p.c11_point_variability },
      ];
      const score = sc.pedro_score != null ? sc.pedro_score : crits.slice(1).filter(c => c.ok === true).length;
      const barPct = Math.round((score / 10) * 100);
      return (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="row between" style={{ marginBottom: 10 }}>
            <div><h2 style={{ display: 'inline' }}>🔬 PEDro</h2><span className="muted" style={{ marginLeft: 8, fontSize: 13 }}>scala 0–10</span></div>
            <div className="mono" style={{ fontSize: 20, fontWeight: 700 }}>{score}<span className="muted" style={{ fontSize: 14 }}> / 10</span></div>
          </div>
          <div style={{ height: 6, background: '#e2e5ea', borderRadius: 3, overflow: 'hidden', marginBottom: 4 }}>
            <div style={{ width: barPct + '%', height: '100%', background: '#475569' }}></div>
          </div>
          <div className="crit-grid">{crits.map(({ code, ok }) => <Crit key={code} code={code} ok={ok} />)}</div>
        </div>
      );
    }

    if (tool === 'AMSTAR-2' && ed.amstar2_criteria) {
      const a = ed.amstar2_criteria;
      const crits = [
        { code: 'A1', ok: a.a1_pico }, { code: 'A2', ok: a.a2_protocol_registered },
        { code: 'A3', ok: a.a3_study_design_explained }, { code: 'A4', ok: a.a4_comprehensive_search },
        { code: 'A5', ok: a.a5_duplicate_selection }, { code: 'A6', ok: a.a6_duplicate_extraction },
        { code: 'A7', ok: a.a7_excluded_studies_listed }, { code: 'A8', ok: a.a8_studies_described },
        { code: 'A9', ok: a.a9_risk_of_bias_assessed }, { code: 'A10', ok: a.a10_funding_reported },
        { code: 'A11', ok: a.a11_statistical_methods }, { code: 'A12', ok: a.a12_rob_impact_assessed },
        { code: 'A13', ok: a.a13_rob_in_interpretation }, { code: 'A14', ok: a.a14_heterogeneity_discussed },
        { code: 'A15', ok: a.a15_publication_bias }, { code: 'A16', ok: a.a16_coi_disclosed },
      ];
      const met = sc.amstar2_met != null ? sc.amstar2_met : crits.filter(c => c.ok === true).length;
      const barPct = Math.round((met / 16) * 100);
      return (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="row between" style={{ marginBottom: 10 }}>
            <div><h2 style={{ display: 'inline' }}>🔬 AMSTAR-2</h2><span className="muted" style={{ marginLeft: 8, fontSize: 13 }}>16 criteri (7 critici)</span></div>
            <div className="mono" style={{ fontSize: 20, fontWeight: 700 }}>{met}<span className="muted" style={{ fontSize: 14 }}> / 16</span></div>
          </div>
          <div style={{ height: 6, background: '#e2e5ea', borderRadius: 3, overflow: 'hidden', marginBottom: 4 }}>
            <div style={{ width: barPct + '%', height: '100%', background: '#475569' }}></div>
          </div>
          <div className="crit-grid">{crits.map(({ code, ok }) => <Crit key={code} code={code} ok={ok} />)}</div>
          <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>Criteri critici (★): A2, A4, A7, A9, A11, A13, A15 — peso 1.5× nel punteggio</p>
        </div>
      );
    }

    if (tool === 'NOS' && ed.nos_criteria) {
      const n = ed.nos_criteria;
      const crits = [
        { code: 'S1', ok: n.s1_representativeness }, { code: 'S2', ok: n.s2_non_exposed_selection },
        { code: 'S3', ok: n.s3_exposure_ascertainment }, { code: 'S4', ok: n.s4_outcome_not_present },
        { code: 'C1', ok: n.c1_primary_factor }, { code: 'C2', ok: n.c2_additional_factor },
        { code: 'O1', ok: n.o1_outcome_assessment }, { code: 'O2', ok: n.o2_followup_length },
        { code: 'O3', ok: n.o3_followup_adequacy },
      ];
      const score = sc.nos_score != null ? sc.nos_score : crits.filter(c => c.ok === true).length;
      const barPct = Math.round((score / 9) * 100);
      return (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="row between" style={{ marginBottom: 10 }}>
            <div><h2 style={{ display: 'inline' }}>🔬 Newcastle-Ottawa Scale</h2></div>
            <div className="mono" style={{ fontSize: 20, fontWeight: 700 }}>{score}<span className="muted" style={{ fontSize: 14 }}> / 9</span></div>
          </div>
          <div style={{ height: 6, background: '#e2e5ea', borderRadius: 3, overflow: 'hidden', marginBottom: 4 }}>
            <div style={{ width: barPct + '%', height: '100%', background: '#475569' }}></div>
          </div>
          <div className="crit-grid">{crits.map(({ code, ok }) => <Crit key={code} code={code} ok={ok} />)}</div>
        </div>
      );
    }

    if (tool === 'GRADE' && ed.grade_criteria) {
      const g = ed.grade_criteria;
      const crits = [
        { code: 'G1', ok: g.g1_systematic_search }, { code: 'G2', ok: g.g2_evidence_graded },
        { code: 'G3', ok: g.g3_consensus_method }, { code: 'G4', ok: g.g4_panel_composition },
        { code: 'G5', ok: g.g5_coi_management }, { code: 'G6', ok: g.g6_recommendation_strength },
        { code: 'G7', ok: g.g7_evidence_gaps }, { code: 'G8', ok: g.g8_external_review },
      ];
      const met = sc.grade_met != null ? sc.grade_met : crits.filter(c => c.ok === true).length;
      return (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="row between" style={{ marginBottom: 10 }}>
            <div><h2 style={{ display: 'inline' }}>🔬 GRADE</h2><span className="muted" style={{ marginLeft: 8, fontSize: 13 }}>Consensus assessment</span></div>
            <div className="mono" style={{ fontSize: 20, fontWeight: 700 }}>{met}<span className="muted" style={{ fontSize: 14 }}> / 8</span></div>
          </div>
          <div className="crit-grid">{crits.map(({ code, ok }) => <Crit key={code} code={code} ok={ok} />)}</div>
        </div>
      );
    }

    return (
      <div className="card" style={{ marginTop: 20 }}>
        <div className="row between">
          <h2>🔬 {tool || 'Generic'}</h2>
          <div className="mono" style={{ fontSize: 20, fontWeight: 700 }}>
            {sc.base_methodology_score.toFixed(1)}<span className="muted" style={{ fontSize: 14 }}> / {sc.design_cap.toFixed(1)}</span>
          </div>
        </div>
      </div>
    );
  };

  const sampleBonus = (sc.sample_size_adjustment || 0) + (sc.large_sample_bonus || 0);

  const banners = [];
  if (sc.institutional_bonus > 0) banners.push({ tone: 'blue', icon: '★', text: `Elite institution · ${(sc.institutional_matches || []).join(', ')}`, mod: `+${sc.institutional_bonus.toFixed(1)}` });
  if (sc.journal_bonus > 0) banners.push({ tone: 'purple', icon: '🏆', text: `Elite journal · ${sc.journal_match || ed.journal || ''}`, mod: `+${sc.journal_bonus.toFixed(1)}` });
  if (sc.registered_protocol_bonus > 0) banners.push({ tone: 'green', icon: '✓', text: 'Protocollo registrato a priori (ClinicalTrials.gov / PROSPERO / OSF)', mod: `+${sc.registered_protocol_bonus.toFixed(1)}` });
  if (sampleBonus > 0) banners.push({ tone: 'blue', icon: '★', text: `Sample bonus · ${ed.population_type || `n=${ed.sample_size}`}`, mod: `+${sampleBonus.toFixed(1)}` });
  if (sc.coi_detected && sc.coi_penalty < 0) banners.push({ tone: 'amber', icon: '⚠', text: `Conflict of interest (${sc.coi_severity}) · ${ed.conflict_of_interest_statement || ''}`, mod: sc.coi_penalty.toFixed(1) });
  if (sc.predatory_journal_detected) banners.push({ tone: 'black', icon: '🏴', text: `Predatory journal · ${sc.predatory_journal_match || ''}` });

  const authorsStr = Array.isArray(ed.authors) ? ed.authors.slice(0, 3).join(', ') + (ed.authors.length > 3 ? ' et al.' : '') : (ed.authors || '');
  const subtitle = [authorsStr, ed.journal, ed.year].filter(Boolean).join(' · ');

  let toolLabel = sc.methodology_tool || 'Generic';
  if (sc.pedro_score != null) toolLabel += ` ${sc.pedro_score}/10`;
  else if (sc.nos_score != null) toolLabel += ` ${sc.nos_score}/9`;
  else if (sc.amstar2_met != null) toolLabel += ` ${sc.amstar2_met}/16`;

  const confPct = confidence?.extracted_fields && confidence?.total_fields
    ? Math.round(confidence.extracted_fields / confidence.total_fields * 100) : 0;
  const confLevel = confidence?.level?.toUpperCase() || 'LOW';
  const confClass = confLevel === 'HIGH' ? 'high' : confLevel === 'MEDIUM' ? 'med' : 'low';
  const confColor = confLevel === 'HIGH' ? '#059669' : confLevel === 'MEDIUM' ? '#ca8a04' : '#dc2626';

  return (
    <>
      <div className="row between" style={{ marginBottom: 14 }}>
        <div className="row">
          <span className="eyebrow">FILE</span>
          <span style={{ fontWeight: 600, maxWidth: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{filename}</span>
        </div>
        <button className="btn btn-secondary btn-small" onClick={onReset}>↺ Nuovo paper</button>
      </div>

      <div className="card">
        <div className="result-header">
          <Ring pct={qualityPct} />
          <div>
            <span className={`cat-badge cat-${category}`}>{categoryLabel}</span>
            <div className="result-title" style={{ marginTop: 10 }}>{ed.title || filename}</div>
            {subtitle && <div className="result-subtitle">{subtitle}</div>}
            <div className="score-stats">
              <div className="score-stat">
                <div className="num">{sc.final_score.toFixed(1)}<span className="cap"> /{sc.design_cap.toFixed(1)}</span></div>
                <div className="lbl">Score / Cap</div>
              </div>
              <div style={{ borderLeft: '1px solid #e2e5ea' }}></div>
              <div className="score-stat">
                <div className="num" style={{ fontSize: 20 }}>{toolLabel}</div>
                <div className="lbl">Tool</div>
              </div>
              {ed.sample_size && <>
                <div style={{ borderLeft: '1px solid #e2e5ea' }}></div>
                <div className="score-stat">
                  <div className="num" style={{ fontSize: 20 }}>n={ed.sample_size}</div>
                  <div className="lbl">{ed.population_type || 'partecipanti'}</div>
                </div>
              </>}
            </div>
          </div>
        </div>

        {explanation && (
          <div className="explanation">
            <strong className="eyebrow">Verdetto AI</strong>
            {explanation}
          </div>
        )}
      </div>

      {banners.length > 0 && (
        <div className="stack">
          {banners.map((b, i) => (
            <Banner key={i} tone={b.tone} icon={b.icon}>
              {b.text}
              {b.mod && <span className="banner-mod">{b.mod}</span>}
            </Banner>
          ))}
        </div>
      )}

      {renderMethodology()}

      {(ed.study_design || ed.sample_size || ed.journal) && (
        <div className="metric-grid" style={{ marginTop: 20 }}>
          {ed.study_design && (
            <div className="metric">
              <div className="lbl">Study design</div>
              <div className="val" style={{ fontSize: 14, textTransform: 'capitalize' }}>{ed.study_design.replace(/_/g, ' ')}</div>
            </div>
          )}
          {ed.sample_size && (
            <div className="metric">
              <div className="lbl">Sample</div>
              <div className="val">n = {ed.sample_size}</div>
              {ed.population_type && <div className="sub2" style={{ textTransform: 'capitalize' }}>{ed.population_type.replace(/_/g, ' ')}</div>}
            </div>
          )}
          {ed.journal && (
            <div className="metric">
              <div className="lbl">Journal</div>
              <div className="val" style={{ fontSize: 14 }}>{ed.journal}</div>
              {ed.year && <div className="sub2">{ed.year}</div>}
            </div>
          )}
        </div>
      )}

      <div className="card" style={{ marginTop: 20 }}>
        <h3>Score breakdown</h3>
        <div className="brk">
          <BRow label={`Base score (${sc.methodology_tool || 'Generic'})`} val={sc.base_methodology_score.toFixed(1)} bar={Math.round(sc.base_methodology_score / sc.design_cap * 100)} />
          {sampleBonus !== 0 && <BRow label="Sample bonus" val={`+${sampleBonus.toFixed(1)}`} note={ed.elite_exception_applied ? 'elite exception' : ''} />}
          {sc.institutional_bonus > 0 && <BRow label="Elite institution" val={`+${sc.institutional_bonus.toFixed(1)}`} note={(sc.institutional_matches || []).join(', ')} />}
          {sc.journal_bonus > 0 && <BRow label="Elite journal" val={`+${sc.journal_bonus.toFixed(1)}`} note={sc.journal_match} />}
          {sc.registered_protocol_bonus > 0 && <BRow label="Protocol registered" val={`+${sc.registered_protocol_bonus.toFixed(1)}`} />}
          {sc.coi_penalty !== 0 && <BRow label="CoI penalty" val={sc.coi_penalty.toFixed(1)} muted />}
          {sc.predatory_journal_detected && <BRow label="Predatory → score forced 1.0" val="FLAG" muted />}
          <div className="brk-row total">
            <span className="lbl">Final score</span>
            <span className="val">
              {sc.raw_score.toFixed(1)}
              {sc.raw_score !== sc.final_score && <span className="muted"> → capped {sc.final_score.toFixed(1)}</span>}
            </span>
          </div>
        </div>
      </div>

      {ed.main_findings_summary && (
        <div className="card" style={{ marginTop: 20 }}>
          <h3>Main finding</h3>
          <p style={{ fontSize: 14.5, lineHeight: 1.65 }}>{ed.main_findings_summary}</p>
        </div>
      )}

      {(ed.funding_sources?.length > 0 || ed.conflict_of_interest_statement) && (
        <div className="card compact" style={{ marginTop: 20 }}>
          {ed.funding_sources?.length > 0 && <>
            <div className="eyebrow" style={{ marginBottom: 4 }}>Funding</div>
            <div style={{ fontSize: 13.5, marginBottom: 6 }}>{ed.funding_sources.join(', ')}</div>
          </>}
          {ed.conflict_of_interest_statement && (
            <div className="muted" style={{ fontSize: 12.5 }}>CoI: {ed.conflict_of_interest_statement}</div>
          )}
        </div>
      )}

      {confidence && (
        <div className="card compact" style={{ marginTop: 20 }}>
          <div className="conf-row">
            <span className="conf-label">Extraction confidence</span>
            <div className="conf-bar"><div className={`conf-fill ${confClass}`} style={{ width: confPct + '%' }}></div></div>
            <span className="conf-text" style={{ color: confColor }}>
              {confLevel} · {confidence.extracted_fields} / {confidence.total_fields}
            </span>
          </div>
        </div>
      )}
    </>
  );
};

window.HHeader = HHeader;
window.HTabs = HTabs;
window.HSidebar = HSidebar;
window.Ring = Ring;
window.Banner = Banner;
window.Crit = Crit;
window.BRow = BRow;
window.ApiKeyModal = ApiKeyModal;
window.UploadScreen = UploadScreen;
window.SingleResult = SingleResult;
