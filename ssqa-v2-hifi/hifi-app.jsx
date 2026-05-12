// Hi-fi components & screens — uses repo design tokens

// ─────── Shared atoms ─────────────────────────────────────
const HHeader = () => (
  <header className="hdr">
    <div className="hdr-logo">SQ</div>
    <h1>Sport Science Quality Analyzer <span>v2.0</span></h1>
    <div className="hdr-status">
      <div className="status-dot"></div>
      <span>API key · personal</span>
    </div>
  </header>
);

const HTabs = ({ active = 'single' }) => (
  <nav className="tabs">
    <button className={`tab ${active === 'single' ? 'active' : ''}`}>Singolo PDF</button>
    <button className={`tab ${active === 'batch' ? 'active' : ''}`}>Analisi Cartella</button>
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
        <div className="scale-row"><span className="cat-badge cat-gold_standard">🥇 Gold</span><span className="rng" style={{ marginLeft: 'auto' }}>≥ 8.5</span></div>
        <div className="scale-row"><span className="cat-badge cat-practical_evidence">🔵 Practical</span><span className="rng" style={{ marginLeft: 'auto' }}>7.0–8.4</span></div>
        <div className="scale-row"><span className="cat-badge cat-exploratory">🔬 Explor.</span><span className="rng" style={{ marginLeft: 'auto' }}>5.0–6.9</span></div>
        <div className="scale-row"><span className="cat-badge cat-weak">⚠️ Weak</span><span className="rng" style={{ marginLeft: 'auto' }}>&lt; 5.0</span></div>
        <div className="scale-row"><span className="cat-badge cat-black_flag">🏴 Black</span><span className="rng" style={{ marginLeft: 'auto' }}>predatory</span></div>
      </div>

      <div className="sidebar-section">
        <h4>Quality % (ring)</h4>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
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
    </aside>
  );
};

const CollapsibleHSidebar = ({ defaultCollapsed = false }) => {
  const [c, setC] = React.useState(defaultCollapsed);
  return <HSidebar collapsed={c} onToggle={() => setC(v => !v)} />;
};

const Ring = ({ pct, size = 100, stroke = 6, color }) => {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - pct / 100);
  const ringColor = color || (
    pct >= 85 ? '#ca8a04' :
    pct >= 70 ? '#475569' :
    pct >= 50 ? '#9a3412' :
    pct >= 30 ? '#2563eb' : '#111827'
  );
  return (
    <div className="score-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#e2e5ea" strokeWidth={stroke} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={ringColor} strokeWidth={stroke}
          strokeDasharray={c} strokeDashoffset={off} strokeLinecap="round"
          transform={`rotate(-90 ${size/2} ${size/2})`} />
      </svg>
      <div className="ring-center" style={{ color: ringColor, fontSize: size * 0.22 }}>{pct}%</div>
    </div>
  );
};

const Banner = ({ tone, icon, children }) => (
  <div className={`banner ${tone}`}>
    <div className="banner-icon">{icon}</div>
    <div style={{ flex: 1 }}>{children}</div>
  </div>
);

const Crit = ({ code, ok }) => (
  <div className={`crit ${ok ? 'ok' : 'no'}`} title={code}>
    <span>{ok ? '✓' : '✗'}</span>
    <span>{code}</span>
  </div>
);

// ─────── Screen 1: empty state ───────────────────────────
const EmptyHi = () => {
  const [c, setC] = React.useState(false);
  return (
    <div className="app">
      <HHeader />
      <HTabs active="single" />
      <div className={`layout ${c ? 'collapsed' : ''}`}>
        <HSidebar collapsed={c} onToggle={() => setC(v => !v)} />
        <div className="main">
          <div className="container">
            <div className="card">
              <h2>Upload Research Paper</h2>
              <p className="sub">Carica un PDF per la valutazione di qualità metodologica. Max 50 MB · Abstract, Methods e Funding estratti automaticamente.</p>
              <div className="drop">
                <div className="drop-icon">📄</div>
                <div className="drop-text">
                  Trascina il PDF qui, oppure <strong>seleziona file</strong>
                </div>
              </div>
              <div style={{ marginTop: 16, display: 'flex', gap: 12 }}>
                <button className="btn btn-primary">Analizza Paper</button>
                <button className="btn btn-secondary">Pulisci</button>
              </div>
            </div>

            <div className="card">
              <h2>Come funziona</h2>
              <p className="sub">Pipeline di estrazione e scoring.</p>
              <ol style={{ paddingLeft: 18, fontSize: 13.5, lineHeight: 1.9, color: '#1a1d23' }}>
                <li><b>Estrazione</b> · L'AI legge abstract, metodi, sample, funding</li>
                <li><b>Selezione strumento</b> · PEDro (RCT) / AMSTAR-2 (SR) / NOS / GRADE / Generic</li>
                <li><b>Scoring</b> · punteggio grezzo + bonus istituzione/rivista/sample + penalty CoI</li>
                <li><b>Verdetto</b> · scala 5 tier (Gold → Black Flag) + ring di qualità normalizzato</li>
              </ol>
              <div className="row wrap" style={{ gap: 6, marginTop: 14 }}>
                <span className="chip chip-silver">⚡ caching 24h</span>
                <span className="chip chip-silver">🛡 CoI detector</span>
                <span className="chip chip-silver">🏴 predatory check</span>
              </div>
            </div>

            <div className="card compact">
              <div className="row between">
                <div>
                  <div className="eyebrow">Ultimo analizzato</div>
                  <div style={{ marginTop: 4, fontWeight: 500 }}>Maughan et al. 2018 — Nutrition for athletes</div>
                </div>
                <span className="cat-badge cat-practical_evidence">Practical Evidence</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ─────── Screen 2: single result ─────────────────────────
const SingleHi = () => {
  const [c, setC] = React.useState(false);
  return (
    <div className="app">
      <HHeader />
      <HTabs active="single" />
      <div className={`layout ${c ? 'collapsed' : ''}`}>
        <HSidebar collapsed={c} onToggle={() => setC(v => !v)} />
        <div className="main">
          <div className="container">

            {/* File strip */}
            <div className="row between" style={{ marginBottom: 14 }}>
              <div className="row">
                <span className="eyebrow">FILE</span>
                <span style={{ fontWeight: 600 }}>BJSM_2024_HIIT_elite_runners.pdf</span>
                <span className="mini-pill">⚡ cached</span>
              </div>
              <div className="row">
                <button className="btn btn-secondary btn-small">↺ Ri-analizza</button>
                <button className="btn btn-secondary btn-small">⬇ Export</button>
              </div>
            </div>

            {/* HERO — Hero B layout */}
            <div className="card">
              <div className="result-header">
                <Ring pct={97} />
                <div>
                  <span className="cat-badge cat-practical_evidence">🔵 Practical Evidence</span>
                  <div className="result-title" style={{ marginTop: 10 }}>
                    HIIT integration improves VO₂max in elite distance runners
                  </div>
                  <div className="result-subtitle">Smith, J. et al. · British Journal of Sports Medicine · 2024</div>
                  <div className="score-stats">
                    <div className="score-stat">
                      <div className="num">7.8<span className="cap"> /8.0</span></div>
                      <div className="lbl">Score / Cap</div>
                    </div>
                    <div style={{ borderLeft: '1px solid #e2e5ea' }}></div>
                    <div className="score-stat">
                      <div className="num" style={{ fontSize: 22 }}>PEDro 7/10</div>
                      <div className="lbl">Tool</div>
                    </div>
                    <div style={{ borderLeft: '1px solid #e2e5ea' }}></div>
                    <div className="score-stat">
                      <div className="num" style={{ fontSize: 22 }}>n=45</div>
                      <div className="lbl">Elite runners</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="explanation">
                <strong className="eyebrow">Verdetto AI</strong>
                RCT ben condotto su atleti d'élite con campione adeguato, registrazione del protocollo
                e pubblicazione su rivista di prestigio. Punteggio massimo grazie a bonus istituzione
                d'élite e rivista indicizzata top-tier. Nessun conflitto di interessi rilevato.
              </div>
            </div>

            {/* Signal banners */}
            <div className="stack">
              <Banner tone="blue" icon="★">
                <b>Elite athlete bonus</b> · sample composto da atleti professionisti
                <span className="banner-mod">+0.5</span>
              </Banner>
              <Banner tone="purple" icon="🏆">
                <b>Elite journal</b> · British Journal of Sports Medicine (IF 18.4)
                <span className="banner-mod">+0.5</span>
              </Banner>
              <Banner tone="green" icon="✓">
                <b>CoI assente</b> — funding pubblico dichiarato (NIH grant R01-XXXX)
              </Banner>
            </div>

            {/* Methodology PEDro */}
            <div className="card" style={{ marginTop: 20 }}>
              <div className="row between" style={{ marginBottom: 10 }}>
                <div>
                  <h2 style={{ display: 'inline' }}>🔬 PEDro</h2>
                  <span className="muted" style={{ marginLeft: 8, fontSize: 13 }}>scala 0–10</span>
                </div>
                <div className="mono" style={{ fontSize: 20, fontWeight: 700 }}>
                  7<span className="muted" style={{ fontSize: 14 }}> / 10</span>
                </div>
              </div>
              <div style={{ height: 6, background: '#e2e5ea', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: '70%', height: '100%', background: '#475569' }}></div>
              </div>
              <div className="crit-grid">
                <Crit code="C1" ok /><Crit code="C2" ok /><Crit code="C3" ok /><Crit code="C4" ok />
                <Crit code="C5" ok={false} /><Crit code="C6" ok={false} /><Crit code="C7" ok />
                <Crit code="C8" ok /><Crit code="C9" ok /><Crit code="C10" ok={false} /><Crit code="C11" ok />
              </div>
              <p className="muted" style={{ fontSize: 12.5, marginTop: 12, lineHeight: 1.55 }}>
                <i>Cieco-soggetto e cieco-terapista non applicabili per intervento di training fisico.
                Penalità per assenza di confronto statistico esplicito sul secondario.</i>
              </p>
            </div>

            {/* Metrics */}
            <div className="metric-grid" style={{ marginTop: 20 }}>
              <div className="metric">
                <div className="lbl">Study design</div>
                <div className="val">RCT</div>
                <div className="sub2">parallel groups · 12 weeks</div>
              </div>
              <div className="metric">
                <div className="lbl">Sample</div>
                <div className="val">n = 45</div>
                <div className="sub2">elite runners · professional</div>
              </div>
              <div className="metric">
                <div className="lbl">Journal</div>
                <div className="val">BJSM</div>
                <div className="sub2"><span className="chip chip-silver">Excellent</span> · IF 18.4</div>
              </div>
            </div>

            {/* Score breakdown */}
            <div className="card" style={{ marginTop: 20 }}>
              <h3>Score breakdown</h3>
              <div className="brk">
                <BRow label="Base score (PEDro)" val="7.0" bar={70} />
                <BRow label="Sample bonus (elite, n≥30)" val="+0.4" />
                <BRow label="Elite institution" val="+0.5" note="Aspetar" />
                <BRow label="Elite journal" val="+0.5" note="BJSM" />
                <BRow label="Protocol registered" val="+0.5" note="ClinicalTrials.gov" />
                <BRow label="CoI penalty" val="0.0" note="none" muted />
                <div className="brk-row total">
                  <span className="lbl">Final score</span>
                  <span className="val">8.9 <span className="muted">→ capped 8.0</span></span>
                </div>
              </div>
            </div>

            {/* Main finding */}
            <div className="card" style={{ marginTop: 20 }}>
              <h3>Main finding</h3>
              <p style={{ fontSize: 14.5, lineHeight: 1.65 }}>
                "L'aggiunta di 2 sessioni settimanali di HIIT al training di base migliora il VO₂max
                di <b>+4.8 ml/kg/min</b> (95% CI 2.1–7.5) rispetto al solo training continuo,
                mantenendo invariato il volume settimanale complessivo."
              </p>
            </div>

            {/* Pros / Cons */}
            <div className="card" style={{ marginTop: 20 }}>
              <h3>Analisi critica</h3>
              <div className="proscons">
                <div className="pros">
                  <h4>Punti di forza</h4>
                  <ul>
                    <li>Protocollo registrato a priori (ClinicalTrials.gov)</li>
                    <li>Sample di atleti elite reali, non sub-elite</li>
                    <li>Intention-to-treat analysis</li>
                    <li>Outcome misurato in laboratorio</li>
                    <li>Funding pubblico — no CoI</li>
                  </ul>
                </div>
                <div className="cons">
                  <h4>Punti di debolezza</h4>
                  <ul>
                    <li>Sample size limitato (n=45)</li>
                    <li>Durata follow-up corta (12 wk)</li>
                    <li>Confronto statistico secondario poco esplicito</li>
                    <li>Drop-out 18% nel braccio HIIT</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Confidence */}
            <div className="card compact" style={{ marginTop: 20 }}>
              <div className="conf-row">
                <span className="conf-label">Extraction confidence</span>
                <div className="conf-bar"><div className="conf-fill high" style={{ width: '88%' }}></div></div>
                <span className="conf-text" style={{ color: '#059669' }}>HIGH · 14 / 16</span>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};

const BRow = ({ label, val, note, bar, muted }) => (
  <div className={`brk-row ${muted ? 'muted' : ''}`}>
    <span className="lbl">{label}</span>
    {bar != null && <span className="bar"><i style={{ width: bar + '%' }}></i></span>}
    {note && <span className="note">{note}</span>}
    <span className="val">{val}</span>
  </div>
);

window.EmptyHi = EmptyHi;
window.SingleHi = SingleHi;
window.HHeader = HHeader;
window.HTabs = HTabs;
window.HSidebar = HSidebar;
window.CollapsibleHSidebar = CollapsibleHSidebar;
window.Ring = Ring;
window.Banner = Banner;
window.Crit = Crit;
window.BRow = BRow;
