import React, { useState, useRef, useEffect } from 'react';

/**
 * XLR8 Platform Architecture - Level 5 DFD
 * Version: 2.2 | Updated: December 26, 2025
 * 
 * CHANGELOG:
 * - v2.2: Added Consultative Synthesis Layer (4.X) and Flow 5
 * - v2.1: Added layman-friendly explanations throughout
 * - v2.0: Five Truths, Learning Module, Project Intelligence, PDF Vision
 * - v1.0: Initial Level 5 DFD
 */

const ArchitecturePage = () => {
  const [scale, setScale] = useState(0.30);
  const [translate, setTranslate] = useState({ x: 50, y: 20 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  const handleWheel = (e) => { e.preventDefault(); setScale(s => Math.min(Math.max(s * (e.deltaY > 0 ? 0.9 : 1.1), 0.1), 3)); };
  const handleMouseDown = (e) => { setIsDragging(true); setDragStart({ x: e.clientX - translate.x, y: e.clientY - translate.y }); };
  const handleMouseMove = (e) => { if (isDragging) setTranslate({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y }); };
  const handleMouseUp = () => setIsDragging(false);
  const resetView = () => { setScale(0.30); setTranslate({ x: 50, y: 20 }); };

  useEffect(() => {
    const cont = containerRef.current;
    if (cont) { cont.addEventListener('wheel', handleWheel, { passive: false }); return () => cont.removeEventListener('wheel', handleWheel); }
  }, []);

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
    explain: '#f0f4f8', explainBorder: '#c5d1de',
    // New color for synthesis
    synth: '#5d8aa8', synthLight: 'rgba(93,138,168,0.12)',
  };

  const W = 4200;
  const PAD = 100;

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: c.bg }}>
      <div style={{ background: c.card, borderBottom: `1px solid ${c.border}`, padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: c.text, margin: 0 }}>Platform Architecture</h1>
          <p style={{ fontSize: 14, color: c.muted, margin: '4px 0 0' }}>Level 5 DFD • Function-Level Detail • v2.2 Dec 2025</p>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          {['+ Zoom', '- Zoom', 'Reset'].map((label, i) => (
            <button key={i} onClick={[() => setScale(s => Math.min(s*1.2,3)), () => setScale(s => Math.max(s/1.2,0.1)), resetView][i]}
              style={{ padding: '8px 16px', background: c.card, border: `1px solid ${c.border}`, borderRadius: 8, cursor: 'pointer' }}>{label}</button>
          ))}
          <span style={{ padding: '8px 12px', background: c.bg, borderRadius: 8, fontFamily: 'monospace', color: c.muted }}>{Math.round(scale*100)}%</span>
        </div>
      </div>

      <div style={{ position: 'absolute', bottom: 24, left: 24, background: c.card, borderRadius: 12, padding: 16, zIndex: 10, border: `1px solid ${c.border}`, boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}>
        <h4 style={{ fontWeight: 600, color: c.text, marginBottom: 12, fontSize: 13 }}>Legend</h4>
        {[[c.dustyBlue,'API'],[c.primary,'Router'],[c.sage,'Processor'],[c.taupe,'Intelligence'],[c.synth,'Synthesis'],[c.purple,'Learning'],[c.slate,'Storage'],[c.warning,'External'],[c.error,'PII/Security']].map(([col,lbl],i)=>(
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 11 }}>
            <div style={{ width: 14, height: 14, borderRadius: 3, background: col }}/><span style={{ color: c.muted }}>{lbl}</span>
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 11 }}>
          <div style={{ width: 14, height: 14, borderRadius: 3, background: c.explain, border: `1px solid ${c.explainBorder}` }}/><span style={{ color: c.muted }}>Explanation</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
          <div style={{ width: 14, height: 14, borderRadius: 3, background: c.wipLight, border: `2px dashed ${c.wip}` }}/><span style={{ color: c.muted }}>WIP</span>
        </div>
      </div>

      <div ref={containerRef} style={{ flex: 1, overflow: 'hidden', cursor: isDragging ? 'grabbing' : 'grab' }}
        onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}>
        <svg viewBox="0 0 4200 4000" style={{ transform: `translate(${translate.x}px,${translate.y}px) scale(${scale})`, transformOrigin: '0 0', width: 4200, height: 4000 }}>
          <defs><pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse"><path d="M50 0L0 0 0 50" fill="none" stroke={c.border} strokeWidth="0.5"/></pattern></defs>
          <rect width="4200" height="4000" fill={c.bg}/><rect width="4200" height="4000" fill="url(#grid)"/>

          {/* ========== TIER 1: API (y=50) ========== */}
          {/* Explanation box */}
          <rect x={PAD} y={50} width={W-2*PAD} height={65} rx="8" fill={c.explain} stroke={c.explainBorder} strokeWidth="1"/>
          <text x={PAD+20} y={75} fill={c.text} fontSize="13" fontWeight="bold">📥 TIER 1: The Front Door</text>
          <text x={PAD+20} y={95} fill={c.muted} fontSize="11">When you click a button or upload a file, your request enters here. This layer receives all incoming requests and sends them to the right place.</text>

          <rect x={PAD} y={125} width={W-2*PAD} height={200} rx="12" fill={c.dustyBlueLight} stroke={c.dustyBlue} strokeWidth="2"/>
          <rect x={PAD} y={125} width={W-2*PAD} height={42} rx="12" fill={c.dustyBlue}/>
          <text x={W/2} y={153} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="18">TIER 1: API ENTRY LAYER</text>
          <text x={PAD+20} y={187} fill={c.muted} fontSize="10" fontFamily="monospace">backend/main.py → backend/routers/*</text>
          
          {[['POST /upload','smart_router.smart_upload()'],['POST /chat','chat.send_message()'],['GET /status/*','status.get_*_status()'],['POST /bi/*','bi_router.execute_query()'],['POST /intelligence','intelligence.analyze()'],['GET /metrics/*','metrics_router.get_*()'],['POST /playbooks/*','playbooks.execute()'],['DELETE /*','cleanup.delete_*()']].map(([ep,fn],i)=>(
            <g key={i}>
              <rect x={PAD+20+i*495} y={200} width={480} height={110} rx="8" fill={c.card} stroke={c.dustyBlue}/>
              <text x={PAD+20+i*495+240} y={230} textAnchor="middle" fill={c.dustyBlue} fontWeight="bold" fontSize="12">{ep}</text>
              <text x={PAD+20+i*495+240} y={253} textAnchor="middle" fill={c.text} fontSize="9" fontFamily="monospace">{fn}</text>
              <text x={PAD+20+i*495+240} y={280} textAnchor="middle" fill={c.light} fontSize="9">→ Tier 2</text>
            </g>
          ))}

          {/* ========== TIER 2: ROUTER + PII (y=385) ========== */}
          {/* Explanation box */}
          <rect x={PAD} y={385} width={W-2*PAD} height={65} rx="8" fill={c.explain} stroke={c.explainBorder} strokeWidth="1"/>
          <text x={PAD+20} y={410} fill={c.text} fontSize="13" fontWeight="bold">🚦 TIER 2: Traffic Control + Privacy Protection</text>
          <text x={PAD+20} y={430} fill={c.muted} fontSize="11">The Smart Router looks at each file and decides how to process it (Excel? PDF? Pay register?). Meanwhile, PII Redaction strips out sensitive data like SSNs BEFORE anything goes to AI.</text>

          <rect x={PAD} y={460} width={1900} height={340} rx="12" fill={c.primaryLight} stroke={c.primary} strokeWidth="2"/>
          <rect x={PAD} y={460} width={1900} height={42} rx="12" fill={c.primary}/>
          <text x={PAD+950} y={488} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="18">TIER 2: SMART ROUTER</text>
          <text x={PAD+20} y={522} fill={c.muted} fontSize="10" fontFamily="monospace">backend/routers/smart_router.py (983 lines)</text>

          {[['smart_upload()','Main entry',['• Validate size/type','• SHA-256 hash','• Check duplicates']],['_determine_proc_type()','Content analysis',['• .xlsx → STRUCTURED','• *register* → REGISTER','• truth_type=ref → STD']],['_register_document()','Registry entry',['• Insert registry','• Create lineage edge','• Link to project']]].map(([nm,desc,items],i)=>(
            <g key={i}>
              <rect x={PAD+20+i*620} y={540} width={600} height={120} rx="8" fill={c.card} stroke={c.primary}/>
              <text x={PAD+20+i*620+300} y={568} textAnchor="middle" fill={c.primary} fontWeight="bold" fontSize="12">{nm}</text>
              <text x={PAD+20+i*620+300} y={588} textAnchor="middle" fill={c.text} fontSize="10">{desc}</text>
              {items.map((it,j)=><text key={j} x={PAD+35+i*620} y={608+j*18} fill={c.muted} fontSize="10">{it}</text>)}
            </g>
          ))}

          {[['_route_to_register()','→ Register Extractor'],['_route_to_standards()','→ Standards Processor'],['_route_to_structured()','→ Structured Handler'],['_route_to_semantic()','→ RAG Handler']].map(([nm,tgt],i)=>(
            <g key={i}>
              <rect x={PAD+20+i*465} y={675} width={450} height={45} rx="6" fill={c.card} stroke={c.sage}/>
              <text x={PAD+20+i*465+225} y={695} textAnchor="middle" fill={c.sage} fontWeight="bold" fontSize="11">{nm}</text>
              <text x={PAD+20+i*465+225} y={712} textAnchor="middle" fill={c.muted} fontSize="9">{tgt}</text>
            </g>
          ))}

          <polygon points="1050,750 1090,775 1050,800 1010,775" fill={c.card} stroke={c.primary} strokeWidth="2"/>
          <text x="1050" y="780" textAnchor="middle" fill={c.primary} fontSize="10" fontWeight="bold">route?</text>

          {/* PII Redaction */}
          <rect x={2050} y={460} width={1000} height={340} rx="12" fill={c.errorLight} stroke={c.error} strokeWidth="2"/>
          <rect x={2050} y={460} width={1000} height={42} rx="12" fill={c.error}/>
          <text x={2550} y={488} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="18">🔒 PII REDACTION</text>
          <text x={2070} y={522} fill={c.muted} fontSize="10" fontFamily="monospace">unified_chat.py + pdf_vision_analyzer.py</text>

          <rect x={2070} y={540} width={470} height={120} rx="8" fill={c.card} stroke={c.error}/>
          <text x={2305} y={565} textAnchor="middle" fill={c.error} fontWeight="bold" fontSize="12">ReversibleRedactor</text>
          <text x={2305} y={585} textAnchor="middle" fill={c.text} fontSize="10">PII NEVER goes to LLMs</text>
          {['• SSN, Salary, DOB','• 30+ PII patterns'].map((t,i)=><text key={i} x={2085} y={605+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          <rect x={2560} y={540} width={470} height={120} rx="8" fill={c.card} stroke={c.error}/>
          <text x={2795} y={565} textAnchor="middle" fill={c.error} fontWeight="bold" fontSize="12">Vision PII Redaction</text>
          <text x={2795} y={585} textAnchor="middle" fill={c.text} fontSize="10">Before Claude Vision API</text>
          {['• Tesseract OCR detect','• Black box overlay'].map((t,i)=><text key={i} x={2575} y={605+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          <rect x={2070} y={675} width={960} height={45} rx="6" fill={c.card} stroke={c.error}/>
          <text x={2550} y={695} textAnchor="middle" fill={c.error} fontWeight="bold" fontSize="11">User Input → redact() → LLM → restore() → Response</text>
          <text x={2550} y={712} textAnchor="middle" fill={c.muted} fontSize="9">PII isolated from ALL external services</text>

          {/* Encryption */}
          <rect x={3100} y={460} width={1000} height={340} rx="12" fill={c.errorLight} stroke={c.error} strokeWidth="2"/>
          <rect x={3100} y={460} width={1000} height={42} rx="12" fill={c.error}/>
          <text x={3600} y={488} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="18">🔐 ENCRYPTION</text>
          <text x={3120} y={522} fill={c.muted} fontSize="10" fontFamily="monospace">structured_data_handler.py</text>

          <rect x={3120} y={540} width={470} height={120} rx="8" fill={c.card} stroke={c.error}/>
          <text x={3355} y={565} textAnchor="middle" fill={c.error} fontWeight="bold" fontSize="12">Field Encryption</text>
          {['• AES-GCM','• Per-field encrypt','• DUCKDB_ENCRYPTION_KEY'].map((t,i)=><text key={i} x={3135} y={588+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          <rect x={3610} y={540} width={470} height={120} rx="8" fill={c.card} stroke={c.error}/>
          <text x={3845} y={565} textAnchor="middle" fill={c.error} fontWeight="bold" fontSize="12">encryption_status()</text>
          {['• Verify AESGCM','• Return PII status','• Audit logging'].map((t,i)=><text key={i} x={3625} y={588+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          {/* ========== TIER 3: PROCESSORS (y=860) ========== */}
          {/* Explanation box */}
          <rect x={PAD} y={860} width={W-2*PAD} height={80} rx="8" fill={c.explain} stroke={c.explainBorder} strokeWidth="1"/>
          <text x={PAD+20} y={885} fill={c.text} fontSize="13" fontWeight="bold">⚙️ TIER 3: The Workers — Specialized File Processors</text>
          <text x={PAD+20} y={905} fill={c.muted} fontSize="11">Each processor is an expert at one thing: Register Extractor reads pay stubs using AI. Standards Processor extracts rules from policy docs.</text>
          <text x={PAD+20} y={923} fill={c.muted} fontSize="11">Structured Handler loads Excel/CSV into the database. PDF Vision uses AI to "see" table columns in PDFs with 92% accuracy.</text>

          <text x={W/2} y={975} textAnchor="middle" fill={c.text} fontWeight="bold" fontSize="20">TIER 3: PROCESSORS</text>

          {[
            {x:100,title:'3.1 REGISTER EXTRACTOR',file:'register_extractor.py (1,932 lines)',fns:[['extract()','Orchestrate',['• Chunk pages','• Parallel LLM']],['_extract_parallel()','ThreadPool(4)',['• 68s→9.4s','• Error isolation']],['_call_groq()','llama-3.3-70b',['• JSON mode','• Rate limiting']],['_merge_results()','Combine',['• Dedupe by ID','• Return DF']]]},
            {x:1100,title:'3.2 STANDARDS PROCESSOR',file:'standards_processor.py',fns:[['process_document()','Main entry',['• PDF/DOCX/TXT','• Detect type']],['_extract_rules()','LLM extract',['• JSON output','• Fallback LLM']],['_chunk_document()','Chunking',['• 500 tokens','• 50 overlap']],['_store_chromadb()','Vector store',['• __STANDARDS__','• Metadata']]]},
            {x:2100,title:'3.3 STRUCTURED HANDLER',file:'structured_data_handler.py (4,800+ lines)',fns:[['load_file()','Ingestion',['• Auto-detect','• Multi-sheet']],['store_dataframe()','DuckDB',['• CREATE TABLE','• _column_profiles']],['_profile_columns()','★ CRITICAL',['• top_values_json','• VALUE matching']],['safe_fetchall()','Thread-safe',['• db_lock','• Commit first']]]},
            {x:3100,title:'3.4 PDF VISION ANALYZER',file:'pdf_vision_analyzer.py (1,161 lines)',fns:[['extract_tables_smart()','Main entry',['• Vision struct','• Learning cache']],['get_pdf_table_structure()','Claude Vision',['• Pages 1-2','• ~$0.04 cost']],['get_document_fingerprint()','Caching',['• Similar→cached','• $0 repeat']],['extract_columns_with_vision()','API call',['• PII redacted','• 92%+ accuracy']]]}
          ].map((sec,si)=>(
            <g key={si}>
              <rect x={sec.x} y={1000} width={980} height={320} rx="12" fill={c.sageLight} stroke={c.sage} strokeWidth="2"/>
              <rect x={sec.x} y={1000} width={980} height={38} rx="12" fill={c.sage}/>
              <text x={sec.x+490} y={1025} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="14">{sec.title}</text>
              <text x={sec.x+20} y={1055} fill={c.muted} fontSize="9" fontFamily="monospace">{sec.file}</text>
              {sec.fns.map(([nm,desc,items],fi)=>{
                const rowOffset = Math.floor(fi/2)*130;
                const boxX = sec.x+20+(fi%2)*480;
                return (
                <g key={fi}>
                  <rect x={boxX} y={1070+rowOffset} width={460} height={115} rx="6" fill={c.card} stroke={c.sage}/>
                  <text x={boxX+230} y={1092+rowOffset} textAnchor="middle" fill={c.sage} fontWeight="bold" fontSize="11">{nm}</text>
                  <text x={boxX+230} y={1110+rowOffset} textAnchor="middle" fill={c.text} fontSize="10">{desc}</text>
                  {items.map((it,ii)=><text key={ii} x={boxX+15} y={1130+rowOffset+ii*16} fill={c.muted} fontSize="9">{it}</text>)}
                </g>
              )})}
            </g>
          ))}

          {/* ========== TIER 4: INTELLIGENCE (y=1380) ========== */}
          {/* Explanation box */}
          <rect x={PAD} y={1380} width={W-2*PAD} height={95} rx="8" fill={c.explain} stroke={c.explainBorder} strokeWidth="1"/>
          <text x={PAD+20} y={1405} fill={c.text} fontSize="13" fontWeight="bold">🧠 TIER 4: The Brain — Where Questions Get Answered</text>
          <text x={PAD+20} y={1425} fill={c.muted} fontSize="11">This is the AI brain of XLR8. When you ask "show me SUI rates", the Intelligence Engine searches FIVE different sources of truth:</text>
          <text x={PAD+20} y={1443} fill={c.muted} fontSize="11">Reality (actual data), Intent (what customer wanted), Configuration (how it's set up), Reference (best practices), and Regulatory (legal requirements).</text>
          <text x={PAD+20} y={1461} fill={c.muted} fontSize="11">The Consultative Synthesizer then triangulates these truths, finds conflicts, and generates world-class answers — not just data dumps.</text>

          <text x={W/2} y={1510} textAnchor="middle" fill={c.text} fontWeight="bold" fontSize="20">TIER 4: INTELLIGENCE LAYER</text>

          {/* Intelligence Engine - Five Truths */}
          <rect x={PAD} y={1540} width={2500} height={520} rx="12" fill={c.taupeLight} stroke={c.taupe} strokeWidth="2"/>
          <rect x={PAD} y={1540} width={2500} height={42} rx="12" fill={c.taupe}/>
          <text x={PAD+1250} y={1568} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="18">4.1 INTELLIGENCE ENGINE v5.20.0 — "Five Truths"</text>
          <text x={PAD+20} y={1602} fill={c.muted} fontSize="10" fontFamily="monospace">intelligence_engine.py (5,937 lines) — The core AI orchestrator that answers all your questions</text>

          {/* Five Truths boxes - Row 1 */}
          <rect x={PAD+20} y={1620} width={480} height={140} rx="10" fill={c.slateLight} stroke={c.slate} strokeWidth="2"/>
          <text x={PAD+260} y={1645} textAnchor="middle" fill={c.slate} fontWeight="bold" fontSize="12">TRUTH 1: REALITY</text>
          <text x={PAD+260} y={1665} textAnchor="middle" fill={c.text} fontSize="10">DuckDB Structured Data</text>
          <text x={PAD+40} y={1690} fill={c.muted} fontSize="9">_gather_reality() → SQL</text>
          <text x={PAD+40} y={1708} fill={c.muted} fontSize="9">"What does the data actually show?"</text>
          <text x={PAD+40} y={1726} fill={c.light} fontSize="8">Your Excel files, registers, PDFs</text>
          <text x={PAD+40} y={1744} fill={c.light} fontSize="8" fontStyle="italic">Example: Current SUI rate is 2.7%</text>

          <rect x={PAD+520} y={1620} width={480} height={140} rx="10" fill={c.taupeLight} stroke={c.taupe} strokeWidth="2"/>
          <text x={PAD+760} y={1645} textAnchor="middle" fill={c.taupe} fontWeight="bold" fontSize="12">TRUTH 2: INTENT</text>
          <text x={PAD+760} y={1665} textAnchor="middle" fill={c.text} fontSize="10">Customer Goals & SOWs</text>
          <text x={PAD+540} y={1690} fill={c.muted} fontSize="9">_gather_intent() → Semantic</text>
          <text x={PAD+540} y={1708} fill={c.muted} fontSize="9">"What was the customer trying to do?"</text>
          <text x={PAD+540} y={1726} fill={c.light} fontSize="8">SOWs, requirements, policies</text>
          <text x={PAD+540} y={1744} fill={c.light} fontSize="8" fontStyle="italic">Example: "Implement all state taxes"</text>

          <rect x={PAD+1020} y={1620} width={480} height={140} rx="10" fill={c.primaryLight} stroke={c.primary} strokeWidth="2"/>
          <text x={PAD+1260} y={1645} textAnchor="middle" fill={c.primary} fontWeight="bold" fontSize="12">TRUTH 3: CONFIGURATION</text>
          <text x={PAD+1260} y={1665} textAnchor="middle" fill={c.text} fontSize="10">System Setup & Mappings</text>
          <text x={PAD+1040} y={1690} fill={c.muted} fontSize="9">_gather_configuration()</text>
          <text x={PAD+1040} y={1708} fill={c.muted} fontSize="9">"How is the system configured?"</text>
          <text x={PAD+1040} y={1726} fill={c.light} fontSize="8">Config validation, code tables</text>
          <text x={PAD+1040} y={1744} fill={c.light} fontSize="8" fontStyle="italic">Example: Tax code "SUI" maps to category 4</text>

          {/* Five Truths boxes - Row 2 */}
          <rect x={PAD+270} y={1775} width={480} height={140} rx="10" fill={c.warningLight} stroke={c.warning} strokeWidth="2"/>
          <text x={PAD+510} y={1800} textAnchor="middle" fill={c.warning} fontWeight="bold" fontSize="12">TRUTH 4: REFERENCE</text>
          <text x={PAD+510} y={1820} textAnchor="middle" fill={c.text} fontSize="10">Product Docs & How-To</text>
          <text x={PAD+290} y={1845} fill={c.muted} fontSize="9">_gather_reflib() → Standards</text>
          <text x={PAD+290} y={1863} fill={c.muted} fontSize="9">"What should the config look like?"</text>
          <text x={PAD+290} y={1881} fill={c.light} fontSize="8">Implementation guides, manuals</text>
          <text x={PAD+290} y={1899} fill={c.light} fontSize="8" fontStyle="italic">Example: SUI rate range 0.1%-12%</text>

          <rect x={PAD+770} y={1775} width={480} height={140} rx="10" fill={c.errorLight} stroke={c.error} strokeWidth="2"/>
          <text x={PAD+1010} y={1800} textAnchor="middle" fill={c.error} fontWeight="bold" fontSize="12">TRUTH 5: REGULATORY</text>
          <text x={PAD+1010} y={1820} textAnchor="middle" fill={c.text} fontSize="10">Laws, IRS Rules, Mandates</text>
          <text x={PAD+790} y={1845} fill={c.muted} fontSize="9">_gather_regulatory()</text>
          <text x={PAD+790} y={1863} fill={c.muted} fontSize="9">"What does the law require?"</text>
          <text x={PAD+790} y={1881} fill={c.light} fontSize="8">IRS pubs, state regs, SOC 2</text>
          <text x={PAD+790} y={1899} fill={c.light} fontSize="8" fontStyle="italic">Example: Texas SUI due quarterly</text>

          {/* Table Scoring */}
          <rect x={PAD+1520} y={1620} width={960} height={295} rx="10" fill={c.card} stroke={c.taupe} strokeWidth="2"/>
          <text x={PAD+2000} y={1645} textAnchor="middle" fill={c.taupe} fontWeight="bold" fontSize="12">★ TABLE SCORING — How We Find the Right Data</text>
          <text x={PAD+2000} y={1665} textAnchor="middle" fill={c.text} fontSize="10">When you ask a question, we score every table to find the best match</text>
          {[
            '+120  Three-word name match',
            '+100  Two-word name match',
            '+80   ★ COLUMN VALUE MATCH',
            '+50   Filter candidate table',
            '+40   Location columns',
            '+30   Single word match',
            '-30   Lookup table penalty',
          ].map((t,i)=><text key={i} x={PAD+1540} y={1695+i*20} fill={i===2 ? c.primary : c.muted} fontSize="10" fontFamily="monospace" fontWeight={i===2 ? 'bold' : 'normal'}>{t}</text>)}
          <text x={PAD+1540} y={1850} fill={c.text} fontSize="10" fontWeight="bold">Why VALUE match matters:</text>
          <text x={PAD+1540} y={1870} fill={c.muted} fontSize="9">"show me SUI rates" → We look inside columns for "SUI"</text>
          <text x={PAD+1540} y={1888} fill={c.muted} fontSize="9">Found in type_of_tax column → That table wins!</text>

          {/* SQL Generation functions */}
          {[['_generate_sql()','DeepSeek SQLCoder',['• CREATE TABLE format','• Column validation']],['_build_create_table_schema()','SQLCoder format',['• PRAGMA table_info','• Sample data']],['_try_fix_sql_from_error()','Auto-repair',['• Parse DuckDB errors','• Fuzzy column match']]].map(([nm,desc,items],i)=>(
            <g key={i}>
              <rect x={PAD+20+i*820} y={1935} width={800} height={85} rx="6" fill={c.card} stroke={c.taupe}/>
              <text x={PAD+20+i*820+400} y={1958} textAnchor="middle" fill={c.taupe} fontWeight="bold" fontSize="10">{nm}</text>
              <text x={PAD+20+i*820+400} y={1976} textAnchor="middle" fill={c.text} fontSize="9">{desc}</text>
              {items.map((it,ii)=><text key={ii} x={PAD+35+i*820} y={1995+ii*15} fill={c.muted} fontSize="9">{it}</text>)}
            </g>
          ))}

          {/* ========== NEW: CONSULTATIVE SYNTHESIS (4.X) ========== */}
          <rect x={2650} y={1540} width={1450} height={250} rx="12" fill={c.synthLight} stroke={c.synth} strokeWidth="2"/>
          <rect x={2650} y={1540} width={1450} height={42} rx="12" fill={c.synth}/>
          <text x={3375} y={1568} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="16">4.X CONSULTATIVE SYNTHESIS ★ NEW</text>
          <text x={2670} y={1602} fill={c.muted} fontSize="10" fontFamily="monospace">consultative_synthesis.py (650 lines) — The "Consultant Brain"</text>

          {[['synthesize()','Main entry',['• Orchestrates all steps','• Returns ConsultativeAnswer']],['_triangulate()','Compare truths',['• Find alignments','• Find conflicts','• Identify gaps']],['_synthesize_with_llm()','LLM synthesis',['• Mistral (local) first','• Claude fallback','• Template fallback']],['_calculate_confidence()','Confidence',['• Source coverage','• Conflict penalty','• Gap penalty']]].map(([nm,desc,items],i)=>(
            <g key={i}>
              <rect x={2670+i*355} y={1620} width={340} height={95} rx="6" fill={c.card} stroke={c.synth}/>
              <text x={2670+i*355+170} y={1643} textAnchor="middle" fill={c.synth} fontWeight="bold" fontSize="10">{nm}</text>
              <text x={2670+i*355+170} y={1661} textAnchor="middle" fill={c.muted} fontSize="9">{desc}</text>
              {items.map((it,ii)=><text key={ii} x={2685+i*355} y={1680+ii*14} fill={c.muted} fontSize="8">{it}</text>)}
            </g>
          ))}

          <rect x={2670} y={1730} width={1410} height={45} rx="6" fill={c.card} stroke={c.synth}/>
          <text x={3375} y={1750} textAnchor="middle" fill={c.synth} fontWeight="bold" fontSize="10">This is what separates XLR8 from "fancy BI tool" — consultative answers, not data dumps</text>
          <text x={3375} y={1768} textAnchor="middle" fill={c.muted} fontSize="9">Triangulates → Finds conflicts → Provides "so-what" context → Signals confidence → Recommends actions</text>

          {/* Project Intelligence + Learning - y=2150 to clear Intelligence Engine (ends 2060) */}
          <rect x={PAD} y={2150} width={2000} height={170} rx="12" fill={c.purpleLight} stroke={c.purple} strokeWidth="2"/>
          <rect x={PAD} y={2150} width={2000} height={40} rx="12" fill={c.purple}/>
          <text x={PAD+1000} y={2176} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="14">4.2 PROJECT INTELLIGENCE — Auto-Discovery</text>
          <text x={PAD+20} y={2208} fill={c.muted} fontSize="10" fontFamily="monospace">project_intelligence.py (2,197 lines)</text>

          {[['analyze()','Tiered analysis'],['_detect_profile_based_lookups()','Uses top_values_json'],['_detect_relationships()','FK detection'],['_find_code_desc_pair()','Code→Description']].map(([nm,desc],i)=>(
            <g key={i}>
              <rect x={PAD+20+i*490} y={2225} width={470} height={40} rx="6" fill={c.card} stroke={c.purple}/>
              <text x={PAD+20+i*490+235} y={2250} textAnchor="middle" fill={c.purple} fontWeight="bold" fontSize="10">{nm}</text>
            </g>
          ))}

          <rect x={PAD+20} y={2275} width={1960} height={30} rx="6" fill={c.card} stroke={c.purple}/>
          <text x={PAD+1000} y={2295} textAnchor="middle" fill={c.muted} fontSize="9">Output: _intelligence_lookups • _intelligence_relationships • FK mappings</text>

          {/* Learning Module */}
          <rect x={2050} y={2150} width={2050} height={170} rx="12" fill={c.purpleLight} stroke={c.purple} strokeWidth="2"/>
          <rect x={2050} y={2150} width={2050} height={40} rx="12" fill={c.purple}/>
          <text x={3075} y={2176} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="14">4.3 LEARNING MODULE — Gets Smarter Over Time</text>
          <text x={2070} y={2208} fill={c.muted} fontSize="10" fontFamily="monospace">learning.py (596 lines)</text>

          {[['find_similar_query()','Pattern reuse'],['learn_query()','Store patterns'],['record_feedback()','Feedback'],['get_cached_analysis()','Cache']].map(([nm,desc],i)=>(
            <g key={i}>
              <rect x={2070+i*500} y={2225} width={480} height={40} rx="6" fill={c.card} stroke={c.purple}/>
              <text x={2070+i*500+240} y={2250} textAnchor="middle" fill={c.purple} fontWeight="bold" fontSize="10">{nm}</text>
            </g>
          ))}

          <rect x={2070} y={2275} width={2010} height={30} rx="6" fill={c.card} stroke={c.purple}/>
          <text x={3075} y={2295} textAnchor="middle" fill={c.muted} fontSize="9">Self-improving: Pattern memory • Feedback loops • Skip learned clarifications</text>

          {/* ========== TIER 5: STORAGE (y=2400) ========== */}
          {/* Explanation box */}
          <rect x={PAD} y={2400} width={W-2*PAD} height={65} rx="8" fill={c.explain} stroke={c.explainBorder} strokeWidth="1"/>
          <text x={PAD+20} y={2425} fill={c.text} fontSize="13" fontWeight="bold">💾 TIER 5: Where Everything Lives — Three Specialized Databases</text>
          <text x={PAD+20} y={2445} fill={c.muted} fontSize="11">DuckDB stores spreadsheet data you can query. ChromaDB stores document text for AI search. Supabase tracks what files exist and who uploaded them. Each excels at its job.</text>

          <text x={W/2} y={2500} textAnchor="middle" fill={c.text} fontWeight="bold" fontSize="20">TIER 5: STORAGE LAYER</text>

          {/* DuckDB */}
          <rect x={PAD} y={2540} width={1100} height={300} rx="12" fill={c.slateLight} stroke={c.slate} strokeWidth="2"/>
          <rect x={PAD} y={2540} width={1100} height={42} rx="12" fill={c.slate}/>
          <text x={PAD+550} y={2568} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="16">D1: DuckDB (Reality) — Your Structured Data</text>
          <text x={PAD+20} y={2602} fill={c.muted} fontSize="10" fontFamily="monospace">/data/project_{'{id}'}.duckdb — Fast SQL queries on your Excel/CSV data</text>

          <rect x={PAD+20} y={2620} width={520} height={200} rx="6" fill={c.card} stroke={c.slate}/>
          <text x={PAD+280} y={2645} textAnchor="middle" fill={c.slate} fontWeight="bold" fontSize="11">System Tables (★ = Critical)</text>
          {[
            '• _schema_metadata — What tables exist',
            '★ _column_profiles — Values in each column',
            '• _intelligence_lookups — Code translations',
            '• _intelligence_relationships — Table links',
            '• {project}_{filename} — Your actual data',
          ].map((t,i)=><text key={i} x={PAD+35} y={2670+i*22} fill={i===1 ? c.primary : c.muted} fontSize="10" fontWeight={i===1 ? 'bold' : 'normal'}>{t}</text>)}
          <text x={PAD+35} y={2790} fill={c.light} fontSize="9">★ _column_profiles.top_values_json is HOW we find the right table</text>

          <rect x={PAD+560} y={2620} width={520} height={200} rx="6" fill={c.card} stroke={c.slate}/>
          <text x={PAD+820} y={2645} textAnchor="middle" fill={c.slate} fontWeight="bold" fontSize="11">Access Pattern</text>
          {['• threading.Lock for safety','• safe_fetchall() with commit','• Per-project isolation','• AES-GCM field encryption','• DUCKDB_ENCRYPTION_KEY env'].map((t,i)=><text key={i} x={PAD+575} y={2670+i*22} fill={c.muted} fontSize="10">{t}</text>)}

          {/* ChromaDB */}
          <rect x={1250} y={2540} width={1100} height={300} rx="12" fill={c.taupeLight} stroke={c.taupe} strokeWidth="2"/>
          <rect x={1250} y={2540} width={1100} height={42} rx="12" fill={c.taupe}/>
          <text x={1800} y={2568} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="16">D2: ChromaDB — AI-Searchable Documents</text>
          <text x={1270} y={2602} fill={c.muted} fontSize="10" fontFamily="monospace">/chromadb — Semantic search: "Find docs about tax compliance" actually works</text>

          <rect x={1270} y={2620} width={520} height={200} rx="6" fill={c.card} stroke={c.taupe}/>
          <text x={1530} y={2645} textAnchor="middle" fill={c.taupe} fontWeight="bold" fontSize="11">Collections by Truth Type</text>
          {['• project_{id}_documents','  └ truth_type: intent | config','• __STANDARDS__','  └ truth_type: reference | regulatory','• 768-dim vectors for similarity'].map((t,i)=><text key={i} x={1285} y={2670+i*22} fill={c.muted} fontSize="10">{t}</text>)}

          <rect x={1810} y={2620} width={520} height={200} rx="6" fill={c.card} stroke={c.taupe}/>
          <text x={2070} y={2645} textAnchor="middle" fill={c.taupe} fontWeight="bold" fontSize="11">Operations</text>
          {['• add() — Store doc chunks','• query() — Find similar text','• Filter by project/type','• nomic-embed-text (local)'].map((t,i)=><text key={i} x={1825} y={2670+i*22} fill={c.muted} fontSize="10">{t}</text>)}

          {/* Supabase */}
          <rect x={2400} y={2540} width={900} height={300} rx="12" fill={c.warningLight} stroke={c.warning} strokeWidth="2"/>
          <rect x={2400} y={2540} width={900} height={42} rx="12" fill={c.warning}/>
          <text x={2850} y={2568} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="16">D3: Supabase — The Registry</text>
          <text x={2420} y={2602} fill={c.muted} fontSize="10" fontFamily="monospace">PostgreSQL cloud — Tracks WHAT exists, not the data itself</text>

          <rect x={2420} y={2620} width={860} height={200} rx="6" fill={c.card} stroke={c.warning}/>
          <text x={2850} y={2645} textAnchor="middle" fill={c.warning} fontWeight="bold" fontSize="11">Registry Tables</text>
          {['• projects — Your projects','• documents — File metadata','• document_registry — Classifications','• lineage_edges — What came from what','• platform_metrics — Usage stats'].map((t,i)=><text key={i} x={2435} y={2670+i*22} fill={c.muted} fontSize="10">{t}</text>)}
          <text x={2435} y={2790} fill={c.light} fontSize="9">Note: Actual DATA lives in DuckDB/ChromaDB</text>

          {/* LLM Services */}
          <rect x={3350} y={2540} width={750} height={300} rx="12" fill={c.warningLight} stroke={c.warning} strokeWidth="2"/>
          <rect x={3350} y={2540} width={750} height={42} rx="12" fill={c.warning}/>
          <text x={3725} y={2568} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="16">E1: LLM Services — AI Brains</text>
          <text x={3370} y={2602} fill={c.muted} fontSize="10">Local First = Privacy + Speed + Cost savings</text>

          <rect x={3370} y={2620} width={350} height={200} rx="6" fill={c.card} stroke={c.warning}/>
          <text x={3545} y={2645} textAnchor="middle" fill={c.warning} fontWeight="bold" fontSize="11">Local (Primary)</text>
          {['• Ollama self-hosted','• DeepSeek = SQL expert','• Mistral = Synthesis','• nomic = Embeddings'].map((t,i)=><text key={i} x={3385} y={2670+i*22} fill={c.muted} fontSize="10">{t}</text>)}
          <text x={3385} y={2770} fill={c.light} fontSize="9">Your data never leaves</text>

          <rect x={3740} y={2620} width={340} height={200} rx="6" fill={c.card} stroke={c.warning}/>
          <text x={3910} y={2645} textAnchor="middle" fill={c.warning} fontWeight="bold" fontSize="11">Cloud (Fallback)</text>
          {['• Claude API','• Groq (registers)','• Rate limiting','• Cost tracking'].map((t,i)=><text key={i} x={3755} y={2670+i*22} fill={c.muted} fontSize="10">{t}</text>)}
          <text x={3755} y={2770} fill={c.light} fontSize="9">Only when local can't handle it</text>

          {/* ========== CRITICAL DATA FLOWS (y=2900) ========== */}
          {/* Explanation box */}
          <rect x={PAD} y={2900} width={W-2*PAD} height={65} rx="8" fill={c.explain} stroke={c.explainBorder} strokeWidth="1"/>
          <text x={PAD+20} y={2925} fill={c.text} fontSize="13" fontWeight="bold">🔄 CRITICAL DATA FLOWS — How Everything Connects</text>
          <text x={PAD+20} y={2945} fill={c.muted} fontSize="11">These five flows are the "magic" of XLR8. They're why you can ask natural questions and get accurate, consultative answers. If any flow breaks, the whole system suffers.</text>

          <text x={W/2} y={3000} textAnchor="middle" fill={c.text} fontWeight="bold" fontSize="20">CRITICAL DATA FLOWS</text>

          {/* Flow 1 */}
          <rect x={PAD} y={3040} width={2000} height={160} rx="12" fill={c.primaryLight} stroke={c.primary} strokeWidth="2"/>
          <rect x={PAD} y={3040} width={2000} height={30} rx="12" fill={c.primary}/>
          <text x={PAD+1000} y={3060} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="12">FLOW 1: Config Validation → Query Routing (★ MOST CRITICAL)</text>
          
          {['Config upload','store_dataframe()','_profile_columns()','top_values_json','_select_tables()','VALUE +80'].map((step,i)=>(
            <g key={i}>
              <rect x={PAD+20+i*325} y={3085} width={305} height={40} rx="6" fill={c.card} stroke={c.primary}/>
              <text x={PAD+20+i*325+152} y={3110} textAnchor="middle" fill={c.primary} fontWeight="bold" fontSize="10">{step}</text>
              {i < 5 && <text x={PAD+335+i*325} y={3105} fill={c.primary} fontSize="14">→</text>}
            </g>
          ))}
          <text x={PAD+40} y={3150} fill={c.text} fontSize="10" fontWeight="bold">Why this matters:</text>
          <text x={PAD+40} y={3168} fill={c.muted} fontSize="9">When you upload a config file, we scan EVERY column and remember what values are in it. So when you ask "show me SUI rates",</text>
          <text x={PAD+40} y={3184} fill={c.muted} fontSize="9">we know that "SUI" is a VALUE in the type_of_tax column — even though "SUI" isn't a column NAME. This is how we find the right table.</text>

          {/* Flow 2 */}
          <rect x={2100} y={3040} width={2000} height={160} rx="12" fill={c.sageLight} stroke={c.sage} strokeWidth="2"/>
          <rect x={2100} y={3040} width={2000} height={30} rx="12" fill={c.sage}/>
          <text x={3100} y={3060} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="12">FLOW 2: PDF Vision Learning (Cost Optimization)</text>
          
          {['PDF upload','get_fingerprint()','Cache check','Vision 1-2','store_learned()','Next: $0'].map((step,i)=>(
            <g key={i}>
              <rect x={2120+i*325} y={3085} width={305} height={40} rx="6" fill={c.card} stroke={c.sage}/>
              <text x={2120+i*325+152} y={3110} textAnchor="middle" fill={c.sage} fontWeight="bold" fontSize="10">{step}</text>
              {i < 5 && <text x={2435+i*325} y={3105} fill={c.sage} fontSize="14">→</text>}
            </g>
          ))}
          <text x={2120} y={3150} fill={c.text} fontSize="10" fontWeight="bold">Why this matters:</text>
          <text x={2120} y={3168} fill={c.muted} fontSize="9">First time we see a PDF type, Claude Vision reads pages 1-2 to understand the columns (~$0.04). We remember this by "fingerprint".</text>
          <text x={2120} y={3184} fill={c.muted} fontSize="9">Next time a similar PDF comes in? We recognize it and reuse the learned columns. $0.00 Vision cost. Scales beautifully.</text>

          {/* Flow 3 */}
          <rect x={PAD} y={3220} width={2000} height={160} rx="12" fill={c.purpleLight} stroke={c.purple} strokeWidth="2"/>
          <rect x={PAD} y={3220} width={2000} height={30} rx="12" fill={c.purple}/>
          <text x={PAD+1000} y={3240} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="12">FLOW 3: Learning Loop (Self-Improvement)</text>
          
          {['User query','find_similar()','Cache hit?','learn_query()','record_feedback()','Next faster'].map((step,i)=>(
            <g key={i}>
              <rect x={PAD+20+i*325} y={3265} width={305} height={40} rx="6" fill={c.card} stroke={c.purple}/>
              <text x={PAD+20+i*325+152} y={3290} textAnchor="middle" fill={c.purple} fontWeight="bold" fontSize="10">{step}</text>
              {i < 5 && <text x={PAD+335+i*325} y={3285} fill={c.purple} fontSize="14">→</text>}
            </g>
          ))}
          <text x={PAD+40} y={3330} fill={c.text} fontSize="10" fontWeight="bold">Why this matters:</text>
          <text x={PAD+40} y={3348} fill={c.muted} fontSize="9">Every successful query gets remembered. Asked "show employees by department" and we figured out you meant org_level_2?</text>
          <text x={PAD+40} y={3364} fill={c.muted} fontSize="9">Next time anyone asks a similar question, we skip the clarification. The system literally gets smarter with use.</text>

          {/* Flow 4 */}
          <rect x={2100} y={3220} width={2000} height={160} rx="12" fill={c.taupeLight} stroke={c.taupe} strokeWidth="2"/>
          <rect x={2100} y={3220} width={2000} height={30} rx="12" fill={c.taupe}/>
          <text x={3100} y={3240} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="12">FLOW 4: Five Truths Query Resolution</text>
          
          {['Question','Reality','Intent','Config','Reference','Regulatory'].map((step,i)=>(
            <g key={i}>
              <rect x={2120+i*325} y={3265} width={305} height={40} rx="6" fill={c.card} stroke={c.taupe}/>
              <text x={2120+i*325+152} y={3290} textAnchor="middle" fill={c.taupe} fontWeight="bold" fontSize="10">{step}</text>
              {i < 5 && <text x={2435+i*325} y={3285} fill={c.taupe} fontSize="14">→</text>}
            </g>
          ))}
          <text x={2120} y={3330} fill={c.text} fontSize="10" fontWeight="bold">Why this matters:</text>
          <text x={2120} y={3348} fill={c.muted} fontSize="9">"Is our SUI rate correct?" → We check Reality (your current rate: 2.7%), Reference (valid range: 0.1%-12%), Regulatory (Texas rules).</text>
          <text x={2120} y={3364} fill={c.muted} fontSize="9">If Reality doesn't match Reference, we found a gap. This is how XLR8 catches configuration errors automatically.</text>

          {/* Flow 5 - NEW: Consultative Synthesis */}
          <rect x={PAD} y={3400} width={W-2*PAD} height={160} rx="12" fill={c.synthLight} stroke={c.synth} strokeWidth="2"/>
          <rect x={PAD} y={3400} width={W-2*PAD} height={30} rx="12" fill={c.synth}/>
          <text x={W/2} y={3420} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="12">FLOW 5: Consultative Synthesis — From Data to Wisdom (★ NEW)</text>
          
          {['Five Truths','Summarize','Triangulate','Conflicts?','LLM Synthesis','Confidence','Answer'].map((step,i)=>(
            <g key={i}>
              <rect x={PAD+20+i*570} y={3445} width={550} height={40} rx="6" fill={c.card} stroke={c.synth}/>
              <text x={PAD+20+i*570+275} y={3470} textAnchor="middle" fill={c.synth} fontWeight="bold" fontSize="10">{step}</text>
              {i < 6 && <text x={PAD+580+i*570} y={3465} fill={c.synth} fontSize="14">→</text>}
            </g>
          ))}
          <text x={PAD+40} y={3510} fill={c.text} fontSize="10" fontWeight="bold">Why this matters:</text>
          <text x={PAD+40} y={3528} fill={c.muted} fontSize="9">Raw data isn't enough. A world-class consultant triangulates sources, notes conflicts, provides "so-what" context, and recommends next steps.</text>
          <text x={PAD+40} y={3544} fill={c.muted} fontSize="9">That's exactly what the Consultative Synthesizer does: Mistral (local) → Claude (fallback) → Template (graceful degradation). Always delivers.</text>

          {/* ========== WIP (y=3620) ========== */}
          <text x={W/2} y={3640} textAnchor="middle" fill={c.text} fontWeight="bold" fontSize="20">WORK IN PROGRESS</text>
          <text x={W/2} y={3665} textAnchor="middle" fill={c.muted} fontSize="11">Features being built • Exit blockers for product launch</text>

          {[
            {x:100,title:'🚧 PLAYBOOK BUILDER UI (12h)',status:'Exit Blocker #5 — Visual workflow editor'},
            {x:1100,title:'🚧 EXPORT ENGINE',status:'Parking Lot — PDF/Excel/PowerPoint reports'},
            {x:2100,title:'🚧 UNIFIED SQL GEN',status:'Parking Lot — One service for all SQL generation'},
            {x:3100,title:'🚧 ENHANCEMENTS',status:'Future — Table names, compliance, GitHub CI/CD'}
          ].map((sec,si)=>(
            <g key={si}>
              <rect x={sec.x} y={3690} width={980} height={90} rx="12" fill={c.wipLight} stroke={c.wip} strokeWidth="2" strokeDasharray="8 4"/>
              <rect x={sec.x} y={3690} width={980} height={35} rx="12" fill={c.wip}/>
              <text x={sec.x+490} y={3712} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="11">{sec.title}</text>
              <text x={sec.x+490} y={3755} textAnchor="middle" fill={c.muted} fontSize="10">{sec.status}</text>
            </g>
          ))}

          {/* Version footer */}
          <text x={W-100} y={3860} textAnchor="end" fill={c.light} fontSize="10">XLR8 Platform v2.2 | Level 5 DFD | December 26, 2025</text>
          <text x={W-100} y={3880} textAnchor="end" fill={c.light} fontSize="10">intelligence_engine.py v5.20.0 | Five Truths + Consultative Synthesis</text>
        </svg>
      </div>
    </div>
  );
};

export default ArchitecturePage;
