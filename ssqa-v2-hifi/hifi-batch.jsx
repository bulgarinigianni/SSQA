// Hi-fi batch screen — uses repo design tokens

const BatchHi = () => {
  const [c, setC] = React.useState(false);
  const [expanded, setExpanded] = React.useState(2); // expand 3rd row

  const rows = [
    { tier: 'gold_standard', tierLabel: '🥇 Gold Standard', pct: 92,
      name: 'Maughan_2024_protein_synthesis_elite.pdf', score: '9.0', cap: '10.0',
      tool: 'PEDro 9/10', n: 'n=120', cached: true },
    { tier: 'gold_standard', tierLabel: '🥇 Gold Standard', pct: 90,
      name: 'Bangsbo_2023_HIIT_football_systematic_review.pdf', score: '9.0', cap: '10.0',
      tool: 'AMSTAR-2 14/16', n: 'k=23', cached: false },
    { tier: 'practical_evidence', tierLabel: '🔵 Practical Evidence', pct: 97,
      name: 'BJSM_2024_HIIT_elite_runners.pdf', score: '7.8', cap: '8.0',
      tool: 'PEDro 7/10', n: 'n=45', cached: true },
    { tier: 'practical_evidence', tierLabel: '🔵 Practical Evidence', pct: 82,
      name: 'Iaia_2024_repeated_sprint_youth.pdf', score: '7.2', cap: '8.0',
      tool: 'PEDro 6/10', n: 'n=58', cached: false },
    { tier: 'practical_evidence', tierLabel: '🔵 Practical Evidence', pct: 75,
      name: 'Buchheit_cohort_running_economy.pdf', score: '7.0', cap: '8.0',
      tool: 'NOS 7/9', n: 'n=210', cached: false },
    { tier: 'exploratory', tierLabel: '🔬 Exploratory', pct: 64,
      name: 'Pyne_2023_cooling_strategies_case_series.pdf', score: '5.7', cap: '6.0',
      tool: 'Generic', n: 'n=12', cached: false },
    { tier: 'weak', tierLabel: '⚠️ Weak', pct: 40,
      name: 'preprint_supplements_endurance_2024.pdf', score: '4.5', cap: '8.0',
      tool: 'PEDro 4/10', n: 'n=18', cached: false },
    { tier: 'black_flag', tierLabel: '🏴 Black Flag', pct: 20,
      name: 'JSSE_2024_recovery_modality.pdf', score: '1.0', cap: '10.0',
      tool: 'Generic', n: 'n=24', cached: false, predatory: true },
  ];

  return (
    <div className="app">
      <HHeader />
      <HTabs active="batch" />
      <div className={`layout ${c ? 'collapsed' : ''}`}>
        <HSidebar collapsed={c} onToggle={() => setC(v => !v)} />
        <div className="main">
          <div className="container">

            {/* Header bar */}
            <div className="card compact" style={{ marginBottom: 18 }}>
              <div className="row between">
                <div className="row">
                  <span className="eyebrow">RUN</span>
                  <span style={{ fontWeight: 600 }}>8 PDF analizzati</span>
                  <span className="muted" style={{ fontSize: 12 }}>· 67 s · 9.140 tokens · 2 cached</span>
                </div>
                <div className="row">
                  <button className="btn btn-secondary btn-small">⬇ Export CSV</button>
                  <button className="btn btn-secondary btn-small">↺ New batch</button>
                </div>
              </div>
            </div>

            {/* Summary pills */}
            <div className="summary-row">
              <span className="summary-pill cat-gold_standard">🥇 2 Gold Standard</span>
              <span className="summary-pill cat-practical_evidence">🔵 3 Practical Evidence</span>
              <span className="summary-pill cat-exploratory">🔬 1 Exploratory</span>
              <span className="summary-pill cat-weak">⚠️ 1 Weak</span>
              <span className="summary-pill cat-black_flag">🏴 1 Black Flag</span>
            </div>

            {/* Inner tabs */}
            <div className="inner-tabs">
              <button className="inner-tab active">Lista qualità</button>
              <button className="inner-tab">Tabella comparativa</button>
              <button className="inner-tab">Reports dettagliati</button>
            </div>

            {/* List */}
            {rows.map((r, i) => (
              <div key={i} className={`batch-row ${expanded === i ? 'expanded' : ''}`}>
                <div className="batch-row-head" onClick={() => setExpanded(expanded === i ? -1 : i)}>
                  <span className={`cat-badge cat-${r.tier}`} style={{ minWidth: 152, textAlign: 'center' }}>
                    {r.tierLabel}
                  </span>
                  <Ring pct={r.pct} size={36} stroke={4} />
                  <div className="name">
                    {r.name}
                    {r.cached && <span className="mini-pill" style={{ marginLeft: 8 }}>⚡ cached</span>}
                    {r.predatory && <span className="mini-pill" style={{ marginLeft: 8, background: '#fef2f2', color: '#dc2626' }}>🏴 predatory</span>}
                  </div>
                  <span className="meta">{r.tool}</span>
                  <span className="meta">{r.n}</span>
                  <span className="score">{r.score}<span className="cap"> / {r.cap}</span></span>
                  <button className="btn btn-secondary btn-small" style={{ minWidth: 96 }}>
                    {expanded === i ? 'Chiudi ▴' : 'Dettagli →'}
                  </button>
                </div>

                {expanded === i && (
                  <div className="batch-row-body">
                    {/* Mini hero */}
                    <div className="card" style={{ marginBottom: 14 }}>
                      <div className="result-header" style={{ borderBottom: 'none', marginBottom: 0, paddingBottom: 0 }}>
                        <Ring pct={r.pct} />
                        <div>
                          <span className={`cat-badge cat-${r.tier}`}>{r.tierLabel}</span>
                          <div className="result-title" style={{ marginTop: 10 }}>
                            HIIT integration improves VO₂max in elite distance runners
                          </div>
                          <div className="result-subtitle">Smith, J. et al. · BJSM · 2024</div>
                          <div className="score-stats">
                            <div className="score-stat">
                              <div className="num">{r.score}<span className="cap"> /{r.cap}</span></div>
                              <div className="lbl">Score / Cap</div>
                            </div>
                            <div style={{ borderLeft: '1px solid #e2e5ea' }}></div>
                            <div className="score-stat">
                              <div className="num" style={{ fontSize: 22 }}>{r.tool}</div>
                              <div className="lbl">Tool</div>
                            </div>
                            <div style={{ borderLeft: '1px solid #e2e5ea' }}></div>
                            <div className="score-stat">
                              <div className="num" style={{ fontSize: 22 }}>{r.n}</div>
                              <div className="lbl">Sample</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="explanation" style={{ marginBottom: 14 }}>
                      <strong className="eyebrow">Verdetto AI</strong>
                      RCT ben condotto su atleti d'élite con campione adeguato, registrazione del
                      protocollo e pubblicazione su rivista di prestigio. Bonus istituzione elite e
                      rivista indicizzata top-tier. Nessun conflitto di interessi rilevato.
                    </div>

                    {/* Signal banners */}
                    <div className="stack" style={{ marginBottom: 14 }}>
                      <Banner tone="blue" icon="★">
                        <b>Elite athlete bonus</b> · sample composto da atleti professionisti
                        <span className="banner-mod">+0.5</span>
                      </Banner>
                      <Banner tone="purple" icon="🏆">
                        <b>Elite journal</b> · British Journal of Sports Medicine
                        <span className="banner-mod">+0.5</span>
                      </Banner>
                    </div>

                    {/* PEDro grid mini */}
                    <div className="card" style={{ marginBottom: 14 }}>
                      <div className="row between" style={{ marginBottom: 10 }}>
                        <h3 style={{ margin: 0 }}>🔬 PEDro · 7 / 10</h3>
                        <span className="muted mono" style={{ fontSize: 12 }}>70% scale</span>
                      </div>
                      <div className="crit-grid">
                        <Crit code="C1" ok /><Crit code="C2" ok /><Crit code="C3" ok />
                        <Crit code="C4" ok /><Crit code="C5" ok={false} /><Crit code="C6" ok={false} />
                        <Crit code="C7" ok /><Crit code="C8" ok /><Crit code="C9" ok />
                        <Crit code="C10" ok={false} /><Crit code="C11" ok />
                      </div>
                    </div>

                    {/* Metrics */}
                    <div className="metric-grid">
                      <div className="metric">
                        <div className="lbl">Design</div>
                        <div className="val">RCT</div>
                      </div>
                      <div className="metric">
                        <div className="lbl">Sample</div>
                        <div className="val">{r.n}</div>
                        <div className="sub2">elite · professional</div>
                      </div>
                      <div className="metric">
                        <div className="lbl">Journal</div>
                        <div className="val">BJSM</div>
                        <div className="sub2"><span className="chip chip-silver">Excellent</span></div>
                      </div>
                    </div>

                    <div className="row" style={{ marginTop: 14 }}>
                      <button className="btn btn-secondary btn-small">↗ Apri vista completa</button>
                      <span className="muted" style={{ fontSize: 12 }}>14 / 16 campi estratti · HIGH confidence</span>
                    </div>
                  </div>
                )}
              </div>
            ))}

          </div>
        </div>
      </div>
    </div>
  );
};

window.BatchHi = BatchHi;
