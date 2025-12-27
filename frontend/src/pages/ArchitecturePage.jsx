import React, { useState } from 'react';

/**
 * XLR8 Platform Architecture - Multi-Page View
 * Version: 3.0 | Updated: December 27, 2025
 * 
 * CHANGELOG:
 * - v3.0: Complete redesign - tabbed pages per tier, NO overlaps
 * - v2.2: Added Consultative Synthesis Layer
 * - v2.1: Added layman-friendly explanations
 * 
 * Deploy to: frontend/src/pages/ArchitecturePage.jsx
 */

const ArchitecturePage = () => {
  const [activeTab, setActiveTab] = useState('overview');

  const c = {
    bg: '#f5f6f8', card: '#ffffff', border: '#e4e7ec', text: '#2d3643', muted: '#6b7a8f', light: '#9aa5b5',
    primary: '#83b16d', primaryLight: 'rgba(131,177,109,0.12)',
    slate: '#6b7a8f', slateLight: 'rgba(107,122,143,0.12)',
    dustyBlue: '#7889a0', dustyBlueLight: 'rgba(120,137,160,0.12)',
    taupe: '#9b8f82', taupeLight: 'rgba(155,143,130,0.12)',
    sage: '#7a9b87', sageLight: 'rgba(122,155,135,0.12)',
    warning: '#b5956a', warningLight: 'rgba(181,149,106,0.12)',
    error: '#a07070', errorLight: 'rgba(160,112,112,0.12)',
    wip: '#9aa5b5', wipLight: 'rgba(154,165,181,0.15)',
    purple: '#8b7aa0', purpleLight: 'rgba(139,122,160,0.12)',
    synth: '#5d8aa8', synthLight: 'rgba(93,138,168,0.12)',
  };

  const tabs = [
    { id: 'overview', label: '🏠 Overview', color: c.text },
    { id: 'tier1', label: '📥 Tier 1: API', color: c.dustyBlue },
    { id: 'tier2', label: '🚦 Tier 2: Router', color: c.primary },
    { id: 'tier3', label: '⚙️ Tier 3: Processors', color: c.sage },
    { id: 'tier4', label: '🧠 Tier 4: Intelligence', color: c.taupe },
    { id: 'tier5', label: '💾 Tier 5: Storage', color: c.slate },
    { id: 'flows', label: '🔄 Data Flows', color: c.synth },
    { id: 'wip', label: '🚧 WIP', color: c.wip },
  ];

  // Reusable card component
  const Card = ({ title, subtitle, color, children, style = {} }) => (
    <div style={{
      background: c.card,
      border: `1px solid ${c.border}`,
      borderRadius: 12,
      overflow: 'hidden',
      ...style
    }}>
      {title && (
        <div style={{ background: color || c.primary, padding: '12px 16px' }}>
          <div style={{ color: '#fff', fontWeight: 700, fontSize: 14 }}>{title}</div>
          {subtitle && <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: 11, marginTop: 2 }}>{subtitle}</div>}
        </div>
      )}
      <div style={{ padding: 16 }}>{children}</div>
    </div>
  );

  // Reusable function box
  const FnBox = ({ name, desc, items, color }) => (
    <div style={{
      background: c.card,
      border: `1px solid ${color || c.border}`,
      borderRadius: 8,
      padding: 12,
      height: '100%'
    }}>
      <div style={{ color: color || c.primary, fontWeight: 600, fontSize: 12, marginBottom: 4 }}>{name}</div>
      {desc && <div style={{ color: c.text, fontSize: 11, marginBottom: 8 }}>{desc}</div>}
      {items?.map((item, i) => (
        <div key={i} style={{ color: c.muted, fontSize: 10, marginBottom: 2 }}>{item}</div>
      ))}
    </div>
  );

  // Explanation box
  const Explain = ({ title, children }) => (
    <div style={{
      background: '#f0f4f8',
      border: '1px solid #c5d1de',
      borderRadius: 8,
      padding: 16,
      marginBottom: 20
    }}>
      <div style={{ fontWeight: 600, color: c.text, marginBottom: 8, fontSize: 14 }}>{title}</div>
      <div style={{ color: c.muted, fontSize: 12, lineHeight: 1.6 }}>{children}</div>
    </div>
  );

  // ============================================================================
  // OVERVIEW PAGE
  // ============================================================================
  const OverviewPage = () => (
    <div>
      <h2 style={{ color: c.text, marginBottom: 8 }}>XLR8 Platform Architecture</h2>
      <p style={{ color: c.muted, marginBottom: 24 }}>Level 5 DFD • Function-Level Detail • v3.0 December 2025</p>
      
      <Explain title="📖 How to Read This">
        This architecture is organized into 5 tiers that data flows through. Each tier has a specific job.
        Click the tabs above to explore each tier in detail.
      </Explain>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
        {[
          { tier: 'Tier 1', name: 'API Entry', desc: 'Receives all requests from the UI', color: c.dustyBlue, icon: '📥' },
          { tier: 'Tier 2', name: 'Smart Router + Security', desc: 'Routes files, redacts PII, encrypts', color: c.primary, icon: '🚦' },
          { tier: 'Tier 3', name: 'Processors', desc: 'Specialized handlers for each file type', color: c.sage, icon: '⚙️' },
          { tier: 'Tier 4', name: 'Intelligence', desc: 'Five Truths + Consultative Synthesis', color: c.taupe, icon: '🧠' },
          { tier: 'Tier 5', name: 'Storage', desc: 'DuckDB, ChromaDB, Supabase, LLMs', color: c.slate, icon: '💾' },
          { tier: 'Flows', name: 'Data Flows', desc: '5 critical flows that connect everything', color: c.synth, icon: '🔄' },
        ].map((t, i) => (
          <div
            key={i}
            onClick={() => setActiveTab(t.tier === 'Flows' ? 'flows' : `tier${i + 1}`)}
            style={{
              background: c.card,
              border: `2px solid ${t.color}`,
              borderRadius: 12,
              padding: 20,
              cursor: 'pointer',
              transition: 'transform 0.15s',
            }}
            onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
            onMouseOut={(e) => e.currentTarget.style.transform = 'translateY(0)'}
          >
            <div style={{ fontSize: 28, marginBottom: 8 }}>{t.icon}</div>
            <div style={{ color: t.color, fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{t.tier}: {t.name}</div>
            <div style={{ color: c.muted, fontSize: 12 }}>{t.desc}</div>
          </div>
        ))}
      </div>

      <Card title="Key Files" color={c.slate}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          {[
            ['intelligence_engine.py', '5,937 lines', 'Core AI orchestrator - Five Truths'],
            ['structured_data_handler.py', '4,800+ lines', 'DuckDB storage and queries'],
            ['smart_router.py', '983 lines', 'Universal upload routing'],
            ['consultative_synthesis.py', '650 lines', 'LLM synthesis layer'],
            ['project_intelligence.py', '2,197 lines', 'Auto-discovery on upload'],
            ['register_extractor.py', '1,932 lines', 'Pay register AI extraction'],
          ].map(([file, lines, desc], i) => (
            <div key={i} style={{ display: 'flex', gap: 12, padding: 8, background: c.bg, borderRadius: 6 }}>
              <code style={{ color: c.primary, fontSize: 11, whiteSpace: 'nowrap' }}>{file}</code>
              <span style={{ color: c.light, fontSize: 10 }}>{lines}</span>
              <span style={{ color: c.muted, fontSize: 10, flex: 1 }}>{desc}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );

  // ============================================================================
  // TIER 1: API
  // ============================================================================
  const Tier1Page = () => (
    <div>
      <h2 style={{ color: c.dustyBlue, marginBottom: 8 }}>Tier 1: API Entry Layer</h2>
      <p style={{ color: c.muted, marginBottom: 24, fontFamily: 'monospace', fontSize: 12 }}>backend/main.py → backend/routers/*</p>
      
      <Explain title="📥 The Front Door">
        When you click a button or upload a file, your request enters here.
        This layer receives all incoming requests and sends them to the right place.
      </Explain>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        {[
          { endpoint: 'POST /upload', fn: 'smart_router.smart_upload()', desc: 'File uploads (Excel, PDF, etc.)' },
          { endpoint: 'POST /chat', fn: 'chat.send_message()', desc: 'Chat questions and analysis' },
          { endpoint: 'GET /status/*', fn: 'status.get_*_status()', desc: 'System and data status' },
          { endpoint: 'POST /bi/*', fn: 'bi_router.execute_query()', desc: 'BI Builder queries' },
          { endpoint: 'POST /intelligence', fn: 'intelligence.analyze()', desc: 'Direct intelligence calls' },
          { endpoint: 'GET /metrics/*', fn: 'metrics_router.get_*()', desc: 'Platform metrics' },
          { endpoint: 'POST /playbooks/*', fn: 'playbooks.execute()', desc: 'Playbook execution' },
          { endpoint: 'DELETE /*', fn: 'cleanup.delete_*()', desc: 'Data deletion' },
        ].map((api, i) => (
          <Card key={i} title={api.endpoint} color={c.dustyBlue}>
            <code style={{ display: 'block', color: c.text, fontSize: 10, marginBottom: 8 }}>{api.fn}</code>
            <div style={{ color: c.muted, fontSize: 11 }}>{api.desc}</div>
            <div style={{ color: c.light, fontSize: 10, marginTop: 8 }}>→ Tier 2</div>
          </Card>
        ))}
      </div>
    </div>
  );

  // ============================================================================
  // TIER 2: ROUTER + SECURITY
  // ============================================================================
  const Tier2Page = () => (
    <div>
      <h2 style={{ color: c.primary, marginBottom: 8 }}>Tier 2: Smart Router + Security</h2>
      <p style={{ color: c.muted, marginBottom: 24 }}>Traffic control, PII protection, and encryption</p>
      
      <Explain title="🚦 Traffic Control + Privacy Protection">
        The Smart Router looks at each file and decides how to process it (Excel? PDF? Pay register?).
        Meanwhile, PII Redaction strips out sensitive data like SSNs BEFORE anything goes to AI.
      </Explain>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 20 }}>
        {/* Smart Router */}
        <Card title="Smart Router" subtitle="smart_router.py (983 lines)" color={c.primary}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
            <FnBox name="smart_upload()" desc="Main entry" items={['• Validate size/type', '• SHA-256 hash', '• Check duplicates']} color={c.primary} />
            <FnBox name="_determine_proc_type()" desc="Content analysis" items={['• .xlsx → STRUCTURED', '• *register* → REGISTER', '• truth_type=ref → STD']} color={c.primary} />
            <FnBox name="_register_document()" desc="Registry entry" items={['• Insert registry', '• Create lineage edge', '• Link to project']} color={c.primary} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
            {['_route_to_register() → Register Extractor', '_route_to_standards() → Standards Processor', '_route_to_structured() → Structured Handler', '_route_to_semantic() → RAG Handler'].map((r, i) => (
              <div key={i} style={{ background: c.sageLight, border: `1px solid ${c.sage}`, borderRadius: 6, padding: 8, fontSize: 10, color: c.sage, textAlign: 'center' }}>{r}</div>
            ))}
          </div>
        </Card>

        {/* PII Redaction */}
        <Card title="🔒 PII Redaction" subtitle="unified_chat.py" color={c.error}>
          <FnBox name="ReversibleRedactor" desc="PII NEVER goes to LLMs" items={['• SSN, Salary, DOB', '• 30+ PII patterns', '• Reversible tokens']} color={c.error} />
          <div style={{ marginTop: 12 }}>
            <FnBox name="Vision PII Redaction" desc="Before Claude Vision API" items={['• Tesseract OCR detect', '• Black box overlay']} color={c.error} />
          </div>
          <div style={{ marginTop: 12, background: c.errorLight, borderRadius: 6, padding: 8, fontSize: 10, color: c.error, textAlign: 'center' }}>
            User Input → redact() → LLM → restore() → Response
          </div>
        </Card>

        {/* Encryption */}
        <Card title="🔐 Encryption" subtitle="structured_data_handler.py" color={c.error}>
          <FnBox name="Field Encryption" desc="AES-GCM per-field" items={['• DUCKDB_ENCRYPTION_KEY', '• Per-field encrypt', '• Audit logging']} color={c.error} />
          <div style={{ marginTop: 12 }}>
            <FnBox name="encryption_status()" desc="Verify & audit" items={['• Verify AESGCM', '• Return PII status']} color={c.error} />
          </div>
        </Card>
      </div>
    </div>
  );

  // ============================================================================
  // TIER 3: PROCESSORS
  // ============================================================================
  const Tier3Page = () => (
    <div>
      <h2 style={{ color: c.sage, marginBottom: 8 }}>Tier 3: Processors</h2>
      <p style={{ color: c.muted, marginBottom: 24 }}>Specialized file handlers - each an expert at one thing</p>
      
      <Explain title="⚙️ The Workers — Specialized File Processors">
        Each processor is an expert at one thing: Register Extractor reads pay stubs using AI.
        Standards Processor extracts rules from policy docs. Structured Handler loads Excel/CSV into the database.
        PDF Vision uses AI to "see" table columns in PDFs with 92% accuracy.
      </Explain>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 20 }}>
        {[
          {
            title: '3.1 Register Extractor',
            file: 'register_extractor.py (1,932 lines)',
            fns: [
              { name: 'extract()', desc: 'Orchestrate', items: ['• Chunk pages', '• Parallel LLM'] },
              { name: '_extract_parallel()', desc: 'ThreadPool(4)', items: ['• 68s→9.4s', '• Error isolation'] },
              { name: '_call_groq()', desc: 'llama-3.3-70b', items: ['• JSON mode', '• Rate limiting'] },
              { name: '_merge_results()', desc: 'Combine', items: ['• Dedupe by ID', '• Return DF'] },
            ]
          },
          {
            title: '3.2 Standards Processor',
            file: 'standards_processor.py',
            fns: [
              { name: 'process_document()', desc: 'Main entry', items: ['• PDF/DOCX/TXT', '• Detect type'] },
              { name: '_extract_rules()', desc: 'LLM extract', items: ['• JSON output', '• Fallback LLM'] },
              { name: '_chunk_document()', desc: 'Chunking', items: ['• 500 tokens', '• 50 overlap'] },
              { name: '_store_chromadb()', desc: 'Vector store', items: ['• __STANDARDS__', '• Metadata'] },
            ]
          },
          {
            title: '3.3 Structured Handler',
            file: 'structured_data_handler.py (4,800+ lines)',
            fns: [
              { name: 'load_file()', desc: 'Ingestion', items: ['• Auto-detect', '• Multi-sheet'] },
              { name: 'store_dataframe()', desc: 'DuckDB', items: ['• CREATE TABLE', '• _column_profiles'] },
              { name: '_profile_columns()', desc: '★ CRITICAL', items: ['• top_values_json', '• VALUE matching'] },
              { name: 'safe_fetchall()', desc: 'Thread-safe', items: ['• db_lock', '• Commit first'] },
            ]
          },
          {
            title: '3.4 PDF Vision Analyzer',
            file: 'pdf_vision_analyzer.py (1,161 lines)',
            fns: [
              { name: 'extract_tables_smart()', desc: 'Main entry', items: ['• Vision struct', '• Learning cache'] },
              { name: 'get_pdf_table_structure()', desc: 'Claude Vision', items: ['• Pages 1-2', '• ~$0.04 cost'] },
              { name: 'get_document_fingerprint()', desc: 'Caching', items: ['• Similar→cached', '• $0 repeat'] },
              { name: 'extract_columns_with_vision()', desc: 'API call', items: ['• PII redacted', '• 92%+ accuracy'] },
            ]
          },
        ].map((proc, pi) => (
          <Card key={pi} title={proc.title} subtitle={proc.file} color={c.sage}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
              {proc.fns.map((fn, fi) => (
                <FnBox key={fi} name={fn.name} desc={fn.desc} items={fn.items} color={c.sage} />
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );

  // ============================================================================
  // TIER 4: INTELLIGENCE
  // ============================================================================
  const Tier4Page = () => (
    <div>
      <h2 style={{ color: c.taupe, marginBottom: 8 }}>Tier 4: Intelligence Layer</h2>
      <p style={{ color: c.muted, marginBottom: 24 }}>Five Truths + Consultative Synthesis - the AI brain</p>
      
      <Explain title="🧠 The Brain — Where Questions Get Answered">
        When you ask "show me SUI rates", the Intelligence Engine searches FIVE sources of truth:
        Reality (actual data), Intent (what customer wanted), Configuration (how it's set up),
        Reference (best practices), and Regulatory (legal requirements).
        The Consultative Synthesizer then triangulates these truths, finds conflicts, and generates
        world-class answers — not just data dumps.
      </Explain>

      {/* Five Truths */}
      <Card title="4.1 Intelligence Engine v5.20.0 — Five Truths" subtitle="intelligence_engine.py (5,937 lines)" color={c.taupe} style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 20 }}>
          {[
            { truth: 'REALITY', source: 'DuckDB', fn: '_gather_reality()', question: 'What does the data actually show?', example: 'Current SUI rate is 2.7%', color: c.slate },
            { truth: 'INTENT', source: 'Customer SOWs', fn: '_gather_intent()', question: 'What was the customer trying to do?', example: '"Implement all state taxes"', color: c.taupe },
            { truth: 'CONFIGURATION', source: 'System Setup', fn: '_gather_configuration()', question: 'How is the system configured?', example: 'Tax code "SUI" maps to cat 4', color: c.primary },
            { truth: 'REFERENCE', source: 'Product Docs', fn: '_gather_reflib()', question: 'What should the config look like?', example: 'SUI rate range 0.1%-12%', color: c.warning },
            { truth: 'REGULATORY', source: 'Laws & Rules', fn: '_gather_regulatory()', question: 'What does the law require?', example: 'Texas SUI due quarterly', color: c.error },
          ].map((t, i) => (
            <div key={i} style={{ background: `${t.color}15`, border: `2px solid ${t.color}`, borderRadius: 10, padding: 12 }}>
              <div style={{ color: t.color, fontWeight: 700, fontSize: 12, marginBottom: 4 }}>TRUTH {i + 1}: {t.truth}</div>
              <div style={{ color: c.text, fontSize: 10, marginBottom: 8 }}>{t.source}</div>
              <code style={{ display: 'block', color: c.muted, fontSize: 9, marginBottom: 8 }}>{t.fn}</code>
              <div style={{ color: c.muted, fontSize: 10, marginBottom: 4 }}>"{t.question}"</div>
              <div style={{ color: c.light, fontSize: 9, fontStyle: 'italic' }}>Ex: {t.example}</div>
            </div>
          ))}
        </div>

        {/* Table Scoring */}
        <div style={{ background: c.bg, borderRadius: 8, padding: 16, marginBottom: 16 }}>
          <div style={{ fontWeight: 600, color: c.taupe, marginBottom: 12 }}>★ Table Scoring — How We Find the Right Data</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
            {['+120 Three-word name', '+100 Two-word match', '+80 ★ VALUE MATCH', '+50 Filter candidate', '+40 Location cols', '+30 Single word', '-30 Lookup penalty'].map((s, i) => (
              <code key={i} style={{ background: i === 2 ? c.primaryLight : c.card, border: `1px solid ${i === 2 ? c.primary : c.border}`, borderRadius: 4, padding: 6, fontSize: 10, color: i === 2 ? c.primary : c.muted, fontWeight: i === 2 ? 700 : 400 }}>{s}</code>
            ))}
          </div>
          <div style={{ marginTop: 12, fontSize: 11, color: c.muted }}>
            ★ <strong style={{ color: c.primary }}>VALUE match is key:</strong> "show me SUI rates" → We search column VALUES for "SUI", not just column names.
            Found in type_of_tax column? That table wins!
          </div>
        </div>

        {/* SQL Generation */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          <FnBox name="_generate_sql()" desc="DeepSeek SQLCoder" items={['• CREATE TABLE format', '• Column validation']} color={c.taupe} />
          <FnBox name="_build_create_table_schema()" desc="SQLCoder format" items={['• PRAGMA table_info', '• Sample data']} color={c.taupe} />
          <FnBox name="_try_fix_sql_from_error()" desc="Auto-repair" items={['• Parse DuckDB errors', '• Fuzzy column match']} color={c.taupe} />
        </div>
      </Card>

      {/* Consultative Synthesis */}
      <Card title="4.X Consultative Synthesis ★ NEW" subtitle="consultative_synthesis.py (650 lines)" color={c.synth} style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
          <FnBox name="synthesize()" desc="Main entry" items={['• Orchestrates all', '• ConsultativeAnswer']} color={c.synth} />
          <FnBox name="_triangulate()" desc="Compare truths" items={['• Find alignments', '• Find conflicts', '• Identify gaps']} color={c.synth} />
          <FnBox name="_synthesize_with_llm()" desc="LLM synthesis" items={['• Mistral (local)', '• Claude fallback', '• Template fallback']} color={c.synth} />
          <FnBox name="_calculate_confidence()" desc="Confidence score" items={['• Source coverage', '• Conflict penalty', '• Gap penalty']} color={c.synth} />
        </div>
        <div style={{ background: c.synthLight, borderRadius: 6, padding: 12, textAlign: 'center' }}>
          <div style={{ color: c.synth, fontWeight: 600, fontSize: 12 }}>This is what separates XLR8 from "fancy BI tool"</div>
          <div style={{ color: c.muted, fontSize: 11, marginTop: 4 }}>Triangulates → Finds conflicts → Provides "so-what" context → Signals confidence → Recommends actions</div>
        </div>
      </Card>

      {/* Project Intelligence + Learning */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 20 }}>
        <Card title="4.2 Project Intelligence" subtitle="project_intelligence.py (2,197 lines)" color={c.purple}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
            {['analyze()', '_detect_profile_based_lookups()', '_detect_relationships()', '_find_code_desc_pair()'].map((fn, i) => (
              <div key={i} style={{ background: c.purpleLight, border: `1px solid ${c.purple}`, borderRadius: 6, padding: 8, fontSize: 10, color: c.purple, textAlign: 'center' }}>{fn}</div>
            ))}
          </div>
          <div style={{ marginTop: 12, fontSize: 10, color: c.muted, textAlign: 'center' }}>Output: _intelligence_lookups • _intelligence_relationships • FK mappings</div>
        </Card>

        <Card title="4.3 Learning Module" subtitle="learning.py (596 lines)" color={c.purple}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
            {['find_similar_query()', 'learn_query()', 'record_feedback()', 'get_cached_analysis()'].map((fn, i) => (
              <div key={i} style={{ background: c.purpleLight, border: `1px solid ${c.purple}`, borderRadius: 6, padding: 8, fontSize: 10, color: c.purple, textAlign: 'center' }}>{fn}</div>
            ))}
          </div>
          <div style={{ marginTop: 12, fontSize: 10, color: c.muted, textAlign: 'center' }}>Self-improving: Pattern memory • Feedback loops • Skip learned clarifications</div>
        </Card>
      </div>
    </div>
  );

  // ============================================================================
  // TIER 5: STORAGE
  // ============================================================================
  const Tier5Page = () => (
    <div>
      <h2 style={{ color: c.slate, marginBottom: 8 }}>Tier 5: Storage Layer</h2>
      <p style={{ color: c.muted, marginBottom: 24 }}>Three specialized databases + LLM services</p>
      
      <Explain title="💾 Where Everything Lives — Three Specialized Databases">
        DuckDB stores spreadsheet data you can query. ChromaDB stores document text for AI search.
        Supabase tracks what files exist and who uploaded them. Each excels at its job.
      </Explain>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 20, marginBottom: 20 }}>
        {/* DuckDB */}
        <Card title="D1: DuckDB (Reality)" subtitle="/data/project_{id}.duckdb" color={c.slate}>
          <div style={{ marginBottom: 12, fontSize: 11, color: c.muted }}>Fast SQL queries on your Excel/CSV data</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
            <div>
              <div style={{ fontWeight: 600, color: c.slate, fontSize: 11, marginBottom: 8 }}>System Tables</div>
              {['• _schema_metadata — What tables exist', '★ _column_profiles — Values in columns', '• _intelligence_lookups — Code translations', '• _intelligence_relationships — Links', '• {project}_{file} — Your data'].map((t, i) => (
                <div key={i} style={{ fontSize: 10, color: i === 1 ? c.primary : c.muted, fontWeight: i === 1 ? 600 : 400, marginBottom: 4 }}>{t}</div>
              ))}
            </div>
            <div>
              <div style={{ fontWeight: 600, color: c.slate, fontSize: 11, marginBottom: 8 }}>Access Pattern</div>
              {['• threading.Lock for safety', '• safe_fetchall() with commit', '• Per-project isolation', '• AES-GCM field encryption'].map((t, i) => (
                <div key={i} style={{ fontSize: 10, color: c.muted, marginBottom: 4 }}>{t}</div>
              ))}
            </div>
          </div>
        </Card>

        {/* ChromaDB */}
        <Card title="D2: ChromaDB" subtitle="/chromadb" color={c.taupe}>
          <div style={{ marginBottom: 12, fontSize: 11, color: c.muted }}>Semantic search: "Find docs about tax compliance" actually works</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
            <div>
              <div style={{ fontWeight: 600, color: c.taupe, fontSize: 11, marginBottom: 8 }}>Collections by Truth</div>
              {['• project_{id}_documents', '  └ truth: intent | config', '• __STANDARDS__', '  └ truth: reference | regulatory', '• 768-dim vectors'].map((t, i) => (
                <div key={i} style={{ fontSize: 10, color: c.muted, marginBottom: 4 }}>{t}</div>
              ))}
            </div>
            <div>
              <div style={{ fontWeight: 600, color: c.taupe, fontSize: 11, marginBottom: 8 }}>Operations</div>
              {['• add() — Store chunks', '• query() — Find similar', '• Filter by project/type', '• nomic-embed-text (local)'].map((t, i) => (
                <div key={i} style={{ fontSize: 10, color: c.muted, marginBottom: 4 }}>{t}</div>
              ))}
            </div>
          </div>
        </Card>

        {/* Supabase */}
        <Card title="D3: Supabase" subtitle="PostgreSQL cloud" color={c.warning}>
          <div style={{ marginBottom: 12, fontSize: 11, color: c.muted }}>Tracks WHAT exists, not the data itself</div>
          <div style={{ fontWeight: 600, color: c.warning, fontSize: 11, marginBottom: 8 }}>Registry Tables</div>
          {['• projects — Your projects', '• documents — File metadata', '• document_registry — Classifications', '• lineage_edges — What came from what', '• platform_metrics — Usage stats'].map((t, i) => (
            <div key={i} style={{ fontSize: 10, color: c.muted, marginBottom: 4 }}>{t}</div>
          ))}
        </Card>

        {/* LLMs */}
        <Card title="E1: LLM Services" subtitle="Local First = Privacy + Speed + Cost" color={c.warning}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
            <div>
              <div style={{ fontWeight: 600, color: c.warning, fontSize: 11, marginBottom: 8 }}>Local (Primary)</div>
              {['• Ollama self-hosted', '• DeepSeek = SQL expert', '• Mistral = Synthesis', '• nomic = Embeddings'].map((t, i) => (
                <div key={i} style={{ fontSize: 10, color: c.muted, marginBottom: 4 }}>{t}</div>
              ))}
              <div style={{ fontSize: 9, color: c.light, marginTop: 8 }}>Your data never leaves</div>
            </div>
            <div>
              <div style={{ fontWeight: 600, color: c.warning, fontSize: 11, marginBottom: 8 }}>Cloud (Fallback)</div>
              {['• Claude API', '• Groq (registers)', '• Rate limiting', '• Cost tracking'].map((t, i) => (
                <div key={i} style={{ fontSize: 10, color: c.muted, marginBottom: 4 }}>{t}</div>
              ))}
              <div style={{ fontSize: 9, color: c.light, marginTop: 8 }}>Only when local can't handle</div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );

  // ============================================================================
  // DATA FLOWS
  // ============================================================================
  const FlowsPage = () => (
    <div>
      <h2 style={{ color: c.synth, marginBottom: 8 }}>Critical Data Flows</h2>
      <p style={{ color: c.muted, marginBottom: 24 }}>Five flows that connect everything — if any breaks, the system suffers</p>
      
      <Explain title="🔄 How Everything Connects">
        These five flows are the "magic" of XLR8. They're why you can ask natural questions
        and get accurate, consultative answers.
      </Explain>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {[
          {
            num: 1, title: 'Config Validation → Query Routing', tag: '★ MOST CRITICAL', color: c.primary,
            steps: ['Config upload', 'store_dataframe()', '_profile_columns()', 'top_values_json', '_select_tables()', 'VALUE +80'],
            why: 'When you upload a config file, we scan EVERY column and remember what values are in it. So when you ask "show me SUI rates", we know that "SUI" is a VALUE in the type_of_tax column — even though "SUI" isn\'t a column NAME.'
          },
          {
            num: 2, title: 'PDF Vision Learning (Cost Optimization)', color: c.sage,
            steps: ['PDF upload', 'get_fingerprint()', 'Cache check', 'Vision 1-2', 'store_learned()', 'Next: $0'],
            why: 'First time we see a PDF type, Claude Vision reads pages 1-2 to understand the columns (~$0.04). We remember by "fingerprint". Next similar PDF? Reuse cached columns. $0.00 Vision cost.'
          },
          {
            num: 3, title: 'Learning Loop (Self-Improvement)', color: c.purple,
            steps: ['User query', 'find_similar()', 'Cache hit?', 'learn_query()', 'record_feedback()', 'Next faster'],
            why: 'Every successful query gets remembered. Asked "show employees by department" and we figured out you meant org_level_2? Next time anyone asks similar, we skip clarification.'
          },
          {
            num: 4, title: 'Five Truths Query Resolution', color: c.taupe,
            steps: ['Question', 'Reality', 'Intent', 'Config', 'Reference', 'Regulatory'],
            why: '"Is our SUI rate correct?" → We check Reality (your current rate: 2.7%), Reference (valid range: 0.1%-12%), Regulatory (Texas rules). If Reality doesn\'t match Reference, we found a gap!'
          },
          {
            num: 5, title: 'Consultative Synthesis — Data to Wisdom', tag: '★ NEW', color: c.synth,
            steps: ['Five Truths', 'Summarize', 'Triangulate', 'Conflicts?', 'LLM Synthesis', 'Confidence', 'Answer'],
            why: 'Raw data isn\'t enough. The Synthesizer triangulates sources, notes conflicts, provides "so-what" context, and recommends next steps. Mistral (local) → Claude (fallback) → Template (graceful degradation).'
          },
        ].map((flow, i) => (
          <Card key={i} title={`Flow ${flow.num}: ${flow.title}`} subtitle={flow.tag} color={flow.color}>
            <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
              {flow.steps.map((step, si) => (
                <React.Fragment key={si}>
                  <div style={{ background: c.card, border: `1px solid ${flow.color}`, borderRadius: 6, padding: '8px 12px', fontSize: 11, color: flow.color, fontWeight: 600 }}>{step}</div>
                  {si < flow.steps.length - 1 && <span style={{ color: flow.color, alignSelf: 'center' }}>→</span>}
                </React.Fragment>
              ))}
            </div>
            <div style={{ fontSize: 11, color: c.muted, lineHeight: 1.6 }}>
              <strong style={{ color: c.text }}>Why this matters:</strong> {flow.why}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );

  // ============================================================================
  // WIP PAGE
  // ============================================================================
  const WipPage = () => (
    <div>
      <h2 style={{ color: c.wip, marginBottom: 8 }}>Work In Progress</h2>
      <p style={{ color: c.muted, marginBottom: 24 }}>Features being built • Exit blockers for product launch</p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 20 }}>
        {[
          { title: '🚧 Playbook Builder UI', status: 'Exit Blocker #5', hours: '12h', desc: 'Visual workflow editor for creating playbooks through configuration' },
          { title: '🚧 Export Engine', status: 'Parking Lot', hours: 'TBD', desc: 'PDF/Excel/PowerPoint report generation' },
          { title: '🚧 Unified SQL Gen', status: 'Parking Lot', hours: 'TBD', desc: 'One service for all SQL generation across the platform' },
          { title: '🚧 Enhancements', status: 'Future', hours: 'TBD', desc: 'Table display names, compliance features, GitHub CI/CD' },
        ].map((item, i) => (
          <div key={i} style={{
            background: c.wipLight,
            border: `2px dashed ${c.wip}`,
            borderRadius: 12,
            padding: 20
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ color: c.text, fontWeight: 700, fontSize: 14 }}>{item.title}</div>
              <code style={{ background: c.card, padding: '4px 8px', borderRadius: 4, fontSize: 10, color: c.wip }}>{item.hours}</code>
            </div>
            <div style={{ color: c.wip, fontSize: 12, fontWeight: 600, marginBottom: 8 }}>{item.status}</div>
            <div style={{ color: c.muted, fontSize: 11 }}>{item.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );

  // ============================================================================
  // RENDER
  // ============================================================================
  const pages = {
    overview: <OverviewPage />,
    tier1: <Tier1Page />,
    tier2: <Tier2Page />,
    tier3: <Tier3Page />,
    tier4: <Tier4Page />,
    tier5: <Tier5Page />,
    flows: <FlowsPage />,
    wip: <WipPage />,
  };

  return (
    <div style={{ minHeight: '100vh', background: c.bg }}>
      {/* Header */}
      <div style={{
        background: c.card,
        borderBottom: `1px solid ${c.border}`,
        padding: '12px 24px',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '8px 16px',
                background: activeTab === tab.id ? tab.color : c.card,
                color: activeTab === tab.id ? '#fff' : c.muted,
                border: `1px solid ${activeTab === tab.id ? tab.color : c.border}`,
                borderRadius: 8,
                cursor: 'pointer',
                fontWeight: activeTab === tab.id ? 600 : 400,
                fontSize: 13,
                transition: 'all 0.15s'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: 24, maxWidth: 1600, margin: '0 auto' }}>
        {pages[activeTab]}
      </div>

      {/* Footer */}
      <div style={{ padding: '16px 24px', borderTop: `1px solid ${c.border}`, textAlign: 'center' }}>
        <span style={{ color: c.light, fontSize: 11 }}>XLR8 Platform v3.0 | Level 5 DFD | December 27, 2025 | intelligence_engine.py v5.20.0</span>
      </div>
    </div>
  );
};

export default ArchitecturePage;
