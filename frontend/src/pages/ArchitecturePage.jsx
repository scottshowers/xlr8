import React, { useState, useRef, useEffect } from 'react';

const ArchitecturePage = () => {
  const [scale, setScale] = useState(0.35);
  const [translate, setTranslate] = useState({ x: 50, y: 20 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  const handleWheel = (e) => { e.preventDefault(); setScale(s => Math.min(Math.max(s * (e.deltaY > 0 ? 0.9 : 1.1), 0.1), 3)); };
  const handleMouseDown = (e) => { setIsDragging(true); setDragStart({ x: e.clientX - translate.x, y: e.clientY - translate.y }); };
  const handleMouseMove = (e) => { if (isDragging) setTranslate({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y }); };
  const handleMouseUp = () => setIsDragging(false);
  const resetView = () => { setScale(0.35); setTranslate({ x: 50, y: 20 }); };

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
  };

  // Layout constants
  const W = 4200;  // Canvas width
  const PAD = 100; // Padding
  const SEC_GAP = 60; // Gap between tier sections
  const BOX_GAP = 20; // Gap between boxes

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: c.bg }}>
      <div style={{ background: c.card, borderBottom: `1px solid ${c.border}`, padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: c.text, margin: 0 }}>Platform Architecture</h1>
          <p style={{ fontSize: 14, color: c.muted, margin: '4px 0 0' }}>Level 5 DFD • Function-Level Detail</p>
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
        {[[c.dustyBlue,'API'],[c.primary,'Router'],[c.sage,'Processor'],[c.taupe,'Intelligence'],[c.slate,'Storage'],[c.warning,'External'],[c.error,'PII/Security']].map(([col,lbl],i)=>(
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 11 }}>
            <div style={{ width: 14, height: 14, borderRadius: 3, background: col }}/><span style={{ color: c.muted }}>{lbl}</span>
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
          <div style={{ width: 14, height: 14, borderRadius: 3, background: c.wipLight, border: `2px dashed ${c.wip}` }}/><span style={{ color: c.muted }}>WIP</span>
        </div>
      </div>

      <div ref={containerRef} style={{ flex: 1, overflow: 'hidden', cursor: isDragging ? 'grabbing' : 'grab' }}
        onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}>
        <svg viewBox="0 0 4200 4400" style={{ transform: `translate(${translate.x}px,${translate.y}px) scale(${scale})`, transformOrigin: '0 0', width: 4200, height: 4400 }}>
          <defs><pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse"><path d="M50 0L0 0 0 50" fill="none" stroke={c.border} strokeWidth="0.5"/></pattern></defs>
          <rect width="4200" height="4400" fill={c.bg}/><rect width="4200" height="4400" fill="url(#grid)"/>

          {/* ========== TIER 1: API (y=50) ========== */}
          <rect x={PAD} y={50} width={W-2*PAD} height={200} rx="12" fill={c.dustyBlueLight} stroke={c.dustyBlue} strokeWidth="2"/>
          <rect x={PAD} y={50} width={W-2*PAD} height={42} rx="12" fill={c.dustyBlue}/>
          <text x={W/2} y={78} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="18">TIER 1: API ENTRY LAYER</text>
          <text x={PAD+20} y={112} fill={c.muted} fontSize="10" fontFamily="monospace">backend/main.py → backend/routers/*</text>
          
          {[['POST /upload','smart_router.smart_upload()'],['POST /chat','chat.send_message()'],['GET /status/*','status.get_*_status()'],['POST /bi/*','bi_router.execute_query()'],['POST /intelligence','intelligence.analyze()'],['GET /metrics/*','metrics_router.get_*()'],['POST /playbooks/*','playbooks.execute()'],['DELETE /*','cleanup.delete_*()']].map(([ep,fn],i)=>(
            <g key={i}>
              <rect x={PAD+20+i*495} y={125} width={480} height={110} rx="8" fill={c.card} stroke={c.dustyBlue}/>
              <text x={PAD+20+i*495+240} y={155} textAnchor="middle" fill={c.dustyBlue} fontWeight="bold" fontSize="12">{ep}</text>
              <text x={PAD+20+i*495+240} y={178} textAnchor="middle" fill={c.text} fontSize="9" fontFamily="monospace">{fn}</text>
              <text x={PAD+20+i*495+240} y={205} textAnchor="middle" fill={c.light} fontSize="9">→ Tier 2</text>
            </g>
          ))}

          {/* ========== TIER 2: ROUTER + PII (y=310) ========== */}
          <rect x={PAD} y={310} width={1900} height={380} rx="12" fill={c.primaryLight} stroke={c.primary} strokeWidth="2"/>
          <rect x={PAD} y={310} width={1900} height={42} rx="12" fill={c.primary}/>
          <text x={PAD+950} y={338} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="18">TIER 2: SMART ROUTER</text>
          <text x={PAD+20} y={372} fill={c.muted} fontSize="10" fontFamily="monospace">backend/routers/smart_router.py (983 lines)</text>

          {[['smart_upload()','Main entry',['• Validate size/type','• SHA-256 hash','• Check duplicates','• Route to processor']],['_determine_proc_type()','Content analysis',['• .xlsx → STRUCTURED','• *register* → REGISTER','• truth_type=ref → STD','• Default → SEMANTIC']],['_register_document()','Registry entry',['• Insert registry','• Create lineage edge','• Return document_id','• Link to project']]].map(([nm,desc,items],i)=>(
            <g key={i}>
              <rect x={PAD+20+i*620} y={390} width={600} height={145} rx="8" fill={c.card} stroke={c.primary}/>
              <text x={PAD+20+i*620+300} y={418} textAnchor="middle" fill={c.primary} fontWeight="bold" fontSize="12">{nm}</text>
              <text x={PAD+20+i*620+300} y={438} textAnchor="middle" fill={c.text} fontSize="10">{desc}</text>
              {items.map((it,j)=><text key={j} x={PAD+35+i*620} y={460+j*18} fill={c.muted} fontSize="10">{it}</text>)}
            </g>
          ))}

          {[['_route_to_register()','→ Register Extractor'],['_route_to_standards()','→ Standards Processor'],['_route_to_structured()','→ Structured Handler'],['_route_to_semantic()','→ RAG Handler']].map(([nm,tgt],i)=>(
            <g key={i}>
              <rect x={PAD+20+i*465} y={555} width={450} height={50} rx="6" fill={c.card} stroke={c.sage}/>
              <text x={PAD+20+i*465+225} y={578} textAnchor="middle" fill={c.sage} fontWeight="bold" fontSize="11">{nm}</text>
              <text x={PAD+20+i*465+225} y={596} textAnchor="middle" fill={c.muted} fontSize="9">{tgt}</text>
            </g>
          ))}

          <polygon points="1050,640 1095,670 1050,700 1005,670" fill={c.card} stroke={c.primary} strokeWidth="2"/>
          <text x="1050" y="675" textAnchor="middle" fill={c.primary} fontSize="10" fontWeight="bold">route?</text>

          {/* PII Redaction */}
          <rect x={2050} y={310} width={1000} height={380} rx="12" fill={c.errorLight} stroke={c.error} strokeWidth="2"/>
          <rect x={2050} y={310} width={1000} height={42} rx="12" fill={c.error}/>
          <text x={2550} y={338} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="18">🔒 PII REDACTION</text>
          <text x={2070} y={372} fill={c.muted} fontSize="10" fontFamily="monospace">unified_chat.py - ReversibleRedactor</text>

          <rect x={2070} y={390} width={470} height={145} rx="8" fill={c.card} stroke={c.error}/>
          <text x={2305} y={418} textAnchor="middle" fill={c.error} fontWeight="bold" fontSize="12">ReversibleRedactor</text>
          <text x={2305} y={438} textAnchor="middle" fill={c.text} fontSize="10">PII NEVER goes to LLMs</text>
          {['• SSN → [SSN_001]','• Salary → [SALARY_001]','• Phone, Email, DOB','• Account numbers'].map((t,i)=><text key={i} x={2085} y={460+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          <rect x={2560} y={390} width={470} height={145} rx="8" fill={c.card} stroke={c.error}/>
          <text x={2795} y={418} textAnchor="middle" fill={c.error} fontWeight="bold" fontSize="12">redact() / restore()</text>
          <text x={2795} y={438} textAnchor="middle" fill={c.text} fontSize="10">Reversible placeholders</text>
          {['• Regex pattern match','• Unique placeholder/value','• Mappings dict','• has_pii() / get_stats()'].map((t,i)=><text key={i} x={2575} y={460+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          <rect x={2070} y={555} width={960} height={50} rx="6" fill={c.card} stroke={c.error}/>
          <text x={2550} y={578} textAnchor="middle" fill={c.error} fontWeight="bold" fontSize="11">User Input → redact() → LLM → restore() → Response</text>
          <text x={2550} y={596} textAnchor="middle" fill={c.muted} fontSize="9">PII isolated from ALL external services</text>

          {/* Encryption */}
          <rect x={3100} y={310} width={1000} height={380} rx="12" fill={c.errorLight} stroke={c.error} strokeWidth="2"/>
          <rect x={3100} y={310} width={1000} height={42} rx="12" fill={c.error}/>
          <text x={3600} y={338} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="18">🔐 ENCRYPTION</text>
          <text x={3120} y={372} fill={c.muted} fontSize="10" fontFamily="monospace">structured_data_handler.py + threat_assessor.py</text>

          <rect x={3120} y={390} width={470} height={145} rx="8" fill={c.card} stroke={c.error}/>
          <text x={3355} y={418} textAnchor="middle" fill={c.error} fontWeight="bold" fontSize="12">Field Encryption</text>
          <text x={3355} y={438} textAnchor="middle" fill={c.text} fontSize="10">Sensitive columns</text>
          {['• AES-GCM encryption','• Per-field encrypt','• Key from env var','• Decrypt on display'].map((t,i)=><text key={i} x={3135} y={460+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          <rect x={3610} y={390} width={470} height={145} rx="8" fill={c.card} stroke={c.error}/>
          <text x={3845} y={418} textAnchor="middle" fill={c.error} fontWeight="bold" fontSize="12">encryption_status()</text>
          <text x={3845} y={438} textAnchor="middle" fill={c.text} fontSize="10">/api/chat/data/encryption-status</text>
          {['• Check encryptor','• Verify AESGCM','• Return PII status','• Audit logging'].map((t,i)=><text key={i} x={3625} y={460+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          <rect x={3120} y={555} width={960} height={50} rx="6" fill={c.card} stroke={c.error}/>
          <text x={3600} y={578} textAnchor="middle" fill={c.error} fontWeight="bold" fontSize="11">DUCKDB_ENCRYPTION_KEY env required</text>
          <text x={3600} y={596} textAnchor="middle" fill={c.muted} fontSize="9">threat_assessor.py validates on startup</text>

          {/* ========== TIER 3: PROCESSORS (y=750) ========== */}
          <text x={W/2} y={770} textAnchor="middle" fill={c.text} fontWeight="bold" fontSize="20">TIER 3: PROCESSORS</text>

          {/* Processor boxes - 4 columns */}
          {[
            {x:100,title:'3.1 REGISTER EXTRACTOR',file:'register_extractor.py',fns:[['extract()','Orchestrator',['• Chunk pages','• Parallel LLM','• Merge results']],['_extract_parallel()','Concurrent',['• ThreadPool(4)','• 68s→9.4s','• Error isolation']],['_call_groq()','Primary LLM',['• llama-3.3-70b','• JSON mode','• Rate limiting']],['_merge_results()','Combine',['• Dedupe by ID','• Validate types','• Return DF']]]},
            {x:1100,title:'3.2 STANDARDS PROCESSOR',file:'standards_processor.py',fns:[['process_document()','Main entry',['• PDF/DOCX/TXT','• Detect type','• Extract+store']],['_extract_rules()','LLM extract',['• Groq primary','• Claude fallback','• JSON output']],['_chunk_document()','Chunking',['• 500 tokens','• 50 overlap','• Paragraphs']],['_store_chromadb()','Vector store',['• __STANDARDS__','• Metadata tags','• Return count']]]},
            {x:2100,title:'3.3 STRUCTURED HANDLER',file:'structured_data_handler.py',fns:[['load_file()','Ingestion',['• Auto-detect','• Multi-sheet','• Return DFs']],['_detect_horiz()','Multi-table',['• Find gaps','• Boundaries','• Merged cells']],['store_dataframe()','DuckDB',['• CREATE TABLE','• Batch INSERT','• Metadata']],['safe_fetchall()','Thread-safe',['• db_lock','• Commit first','• Release finally']]]},
            {x:3100,title:'3.4 RAG HANDLER',file:'rag_handler.py',fns:[['add_document()','Ingestion',['• Text/PDF','• Chunk+embed','• Return IDs']],['_gen_embeddings()','Vectorize',['• nomic-embed','• 768 dims','• Batch 100']],['search()','Semantic',['• Embed query','• k-NN search','• Filter proj']],['get_context()','Build ctx',['• Top chunks','• Citations','• Token limit']]]}
          ].map((sec,si)=>(
            <g key={si}>
              <rect x={sec.x} y={800} width={980} height={400} rx="12" fill={c.sageLight} stroke={c.sage} strokeWidth="2"/>
              <rect x={sec.x} y={800} width={980} height={42} rx="12" fill={c.sage}/>
              <text x={sec.x+490} y={828} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="16">{sec.title}</text>
              <text x={sec.x+20} y={862} fill={c.muted} fontSize="10" fontFamily="monospace">{sec.file}</text>
              {sec.fns.map(([nm,desc,items],fi)=>(
                <g key={fi}>
                  <rect x={sec.x+20+(fi%2)*480} y={880+Math.floor(fi/2)*160} width={460} height={145} rx="6" fill={c.card} stroke={c.sage}/>
                  <text x={sec.x+20+(fi%2)*480+230} y={905} textAnchor="middle" fill={c.sage} fontWeight="bold" fontSize="11">{nm}</text>
                  <text x={sec.x+20+(fi%2)*480+230} y={925} textAnchor="middle" fill={c.text} fontSize="10">{desc}</text>
                  {items.map((it,ii)=><text key={ii} x={sec.x+35+(fi%2)*480} y={948+ii*18} fill={c.muted} fontSize="10">{it}</text>)}
                </g>
              ))}
            </g>
          ))}

          {/* ========== TIER 4: INTELLIGENCE (y=1260) ========== */}
          <text x={W/2} y={1280} textAnchor="middle" fill={c.text} fontWeight="bold" fontSize="20">TIER 4: INTELLIGENCE LAYER</text>

          {/* Intelligence Engine */}
          <rect x={PAD} y={1310} width={2100} height={480} rx="12" fill={c.taupeLight} stroke={c.taupe} strokeWidth="2"/>
          <rect x={PAD} y={1310} width={2100} height={42} rx="12" fill={c.taupe}/>
          <text x={PAD+1050} y={1338} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="18">4.1 INTELLIGENCE ENGINE — "Three Truths"</text>
          <text x={PAD+20} y={1372} fill={c.muted} fontSize="10" fontFamily="monospace">intelligence_engine.py (243,280 lines)</text>

          {/* Three Truths boxes */}
          <rect x={PAD+20} y={1390} width={660} height={170} rx="10" fill={c.slateLight} stroke={c.slate} strokeWidth="2"/>
          <text x={PAD+350} y={1420} textAnchor="middle" fill={c.slate} fontWeight="bold" fontSize="14">TRUTH 1: REALITY</text>
          <text x={PAD+350} y={1445} textAnchor="middle" fill={c.text} fontSize="11">DuckDB Structured Data</text>
          <text x={PAD+40} y={1475} fill={c.muted} fontSize="10">_get_reality() → SQL execution</text>
          <text x={PAD+40} y={1495} fill={c.muted} fontSize="10">"What does the data show?"</text>
          <text x={PAD+40} y={1520} fill={c.light} fontSize="9">Source: Excel/CSV, registers</text>

          <rect x={PAD+700} y={1390} width={660} height={170} rx="10" fill={c.taupeLight} stroke={c.taupe} strokeWidth="2"/>
          <text x={PAD+1030} y={1420} textAnchor="middle" fill={c.taupe} fontWeight="bold" fontSize="14">TRUTH 2: INTENT</text>
          <text x={PAD+1030} y={1445} textAnchor="middle" fill={c.text} fontSize="11">Customer Docs (ChromaDB)</text>
          <text x={PAD+720} y={1475} fill={c.muted} fontSize="10">_get_intent() → Semantic search</text>
          <text x={PAD+720} y={1495} fill={c.muted} fontSize="10">"What was customer trying to do?"</text>
          <text x={PAD+720} y={1520} fill={c.light} fontSize="9">Source: SOWs, configs, policies</text>

          <rect x={PAD+1380} y={1390} width={660} height={170} rx="10" fill={c.primaryLight} stroke={c.primary} strokeWidth="2"/>
          <text x={PAD+1710} y={1420} textAnchor="middle" fill={c.primary} fontWeight="bold" fontSize="14">TRUTH 3: BEST PRACTICE</text>
          <text x={PAD+1710} y={1445} textAnchor="middle" fill={c.text} fontSize="11">Standards Documents</text>
          <text x={PAD+1400} y={1475} fill={c.muted} fontSize="10">_get_best_practice() → Standards</text>
          <text x={PAD+1400} y={1495} fill={c.muted} fontSize="10">"What should config be?"</text>
          <text x={PAD+1400} y={1520} fill={c.light} fontSize="9">Source: Reference library</text>

          {/* Intelligence functions */}
          {[['analyze()','Universal entry',['• Question+project','• Call 3 truths','• Synthesize']],['_generate_sql()','NL to SQL',['• Schema-aware','• DeepSeek coder','• Validate syntax']],['_synthesize()','LLM combine',['• Three truths','• Mistral/Claude','• Recommendations']]].map(([nm,desc,items],i)=>(
            <g key={i}>
              <rect x={PAD+20+i*680} y={1580} width={660} height={110} rx="6" fill={c.card} stroke={c.taupe}/>
              <text x={PAD+20+i*680+330} y={1608} textAnchor="middle" fill={c.taupe} fontWeight="bold" fontSize="11">{nm}</text>
              <text x={PAD+20+i*680+330} y={1628} textAnchor="middle" fill={c.text} fontSize="10">{desc}</text>
              {items.map((it,ii)=><text key={ii} x={PAD+35+i*680} y={1650+ii*16} fill={c.muted} fontSize="10">{it}</text>)}
            </g>
          ))}

          {/* Playbook Framework */}
          <rect x={PAD+20} y={1710} width={2020} height={55} rx="6" fill={c.primaryLight} stroke={c.primary}/>
          <text x={PAD+1030} y={1735} textAnchor="middle" fill={c.primary} fontWeight="bold" fontSize="12">PLAYBOOK FRAMEWORK — execute_playbook() • get_applicable_playbooks() • _run_step()</text>
          <text x={PAD+1030} y={1755} textAnchor="middle" fill={c.muted} fontSize="9">Earnings Codes, Tax Verification, Deduction Analysis, Pay Policy Review</text>

          {/* Chat System */}
          <rect x={2250} y={1310} width={900} height={260} rx="12" fill={c.dustyBlueLight} stroke={c.dustyBlue} strokeWidth="2"/>
          <rect x={2250} y={1310} width={900} height={42} rx="12" fill={c.dustyBlue}/>
          <text x={2700} y={1338} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="16">4.2 CHAT</text>
          <text x={2270} y={1372} fill={c.muted} fontSize="10" fontFamily="monospace">unified_chat.py (3,297 lines)</text>
          {[['send_message()','Main entry'],['_route_query()','Classify'],['_detect_clarify()','Need info?'],['_handle_data()','SQL path'],['_inject_filters()','Context'],['_handle_semantic()','RAG path']].map(([nm,desc],i)=>(
            <g key={i}>
              <rect x={2270+(i%3)*290} y={1390+Math.floor(i/3)*80} width={270} height={65} rx="6" fill={c.card} stroke={c.dustyBlue}/>
              <text x={2270+(i%3)*290+135} y={1418+Math.floor(i/3)*80} textAnchor="middle" fill={c.dustyBlue} fontWeight="bold" fontSize="10">{nm}</text>
              <text x={2270+(i%3)*290+135} y={1438+Math.floor(i/3)*80} textAnchor="middle" fill={c.muted} fontSize="9">{desc}</text>
            </g>
          ))}

          {/* BI Builder */}
          <rect x={3200} y={1310} width={900} height={260} rx="12" fill={c.taupeLight} stroke={c.taupe} strokeWidth="2"/>
          <rect x={3200} y={1310} width={900} height={42} rx="12" fill={c.taupe}/>
          <text x={3650} y={1338} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="16">4.3 BI BUILDER</text>
          <text x={3220} y={1372} fill={c.muted} fontSize="10" fontFamily="monospace">bi_router.py (44,757 lines)</text>
          {[['create_query()','NL→SQL'],['execute_query()','Run'],['save_query()','Persist'],['get_suggestions()','Recommend'],['export_results()','Export'],['_recommend_chart()','Visualize']].map(([nm,desc],i)=>(
            <g key={i}>
              <rect x={3220+(i%3)*290} y={1390+Math.floor(i/3)*80} width={270} height={65} rx="6" fill={c.card} stroke={c.taupe}/>
              <text x={3220+(i%3)*290+135} y={1418+Math.floor(i/3)*80} textAnchor="middle" fill={c.taupe} fontWeight="bold" fontSize="10">{nm}</text>
              <text x={3220+(i%3)*290+135} y={1438+Math.floor(i/3)*80} textAnchor="middle" fill={c.muted} fontSize="9">{desc}</text>
            </g>
          ))}

          {/* ========== TIER 5: STORAGE (y=1850) ========== */}
          <text x={W/2} y={1870} textAnchor="middle" fill={c.text} fontWeight="bold" fontSize="20">TIER 5: STORAGE LAYER</text>

          {/* DuckDB */}
          <rect x={PAD} y={1910} width={980} height={280} rx="12" fill={c.slateLight} stroke={c.slate} strokeWidth="2"/>
          <rect x={PAD} y={1910} width={980} height={42} rx="12" fill={c.slate}/>
          <text x={PAD+490} y={1938} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="16">D1: DuckDB</text>
          <text x={PAD+20} y={1972} fill={c.muted} fontSize="10" fontFamily="monospace">/data/project_{'{id}'}.duckdb</text>

          <rect x={PAD+20} y={1990} width={460} height={180} rx="6" fill={c.card} stroke={c.slate}/>
          <text x={PAD+250} y={2015} textAnchor="middle" fill={c.slate} fontWeight="bold" fontSize="11">Tables</text>
          {['• Uploaded Excel/CSV','• Extracted registers','• PDF tabular data','• _schema_metadata'].map((t,i)=><text key={i} x={PAD+35} y={2040+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          <rect x={PAD+500} y={1990} width={460} height={180} rx="6" fill={c.card} stroke={c.slate}/>
          <text x={PAD+730} y={2015} textAnchor="middle" fill={c.slate} fontWeight="bold" fontSize="11">Access Pattern</text>
          {['• threading.Lock','• safe_fetchall()','• Commit before read','• Per-project isolation'].map((t,i)=><text key={i} x={PAD+515} y={2040+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          {/* ChromaDB */}
          <rect x={1130} y={1910} width={980} height={280} rx="12" fill={c.taupeLight} stroke={c.taupe} strokeWidth="2"/>
          <rect x={1130} y={1910} width={980} height={42} rx="12" fill={c.taupe}/>
          <text x={1620} y={1938} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="16">D2: ChromaDB</text>
          <text x={1150} y={1972} fill={c.muted} fontSize="10" fontFamily="monospace">/chromadb (persistent)</text>

          <rect x={1150} y={1990} width={460} height={180} rx="6" fill={c.card} stroke={c.taupe}/>
          <text x={1380} y={2015} textAnchor="middle" fill={c.taupe} fontWeight="bold" fontSize="11">Collections</text>
          {['• project_{id}_documents','• __STANDARDS__','• 768-dim embeddings','• Metadata per chunk'].map((t,i)=><text key={i} x={1165} y={2040+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          <rect x={1630} y={1990} width={460} height={180} rx="6" fill={c.card} stroke={c.taupe}/>
          <text x={1860} y={2015} textAnchor="middle" fill={c.taupe} fontWeight="bold" fontSize="11">Operations</text>
          {['• add() - upsert','• query() - k-NN','• delete() - remove','• Filter by metadata'].map((t,i)=><text key={i} x={1645} y={2040+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          {/* Supabase */}
          <rect x={2160} y={1910} width={980} height={280} rx="12" fill={c.warningLight} stroke={c.warning} strokeWidth="2"/>
          <rect x={2160} y={1910} width={980} height={42} rx="12" fill={c.warning}/>
          <text x={2650} y={1938} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="16">D3: Supabase</text>
          <text x={2180} y={1972} fill={c.muted} fontSize="10" fontFamily="monospace">PostgreSQL (cloud)</text>

          <rect x={2180} y={1990} width={460} height={180} rx="6" fill={c.card} stroke={c.warning}/>
          <text x={2410} y={2015} textAnchor="middle" fill={c.warning} fontWeight="bold" fontSize="11">Core Tables</text>
          {['• projects, documents','• document_registry','• lineage_edges','• platform_metrics'].map((t,i)=><text key={i} x={2195} y={2040+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          <rect x={2660} y={1990} width={460} height={180} rx="6" fill={c.card} stroke={c.warning}/>
          <text x={2890} y={2015} textAnchor="middle" fill={c.warning} fontWeight="bold" fontSize="11">Standards+BI</text>
          {['• standards_documents','• standards_rules','• playbook_definitions','• saved_queries'].map((t,i)=><text key={i} x={2675} y={2040+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          {/* LLM Services */}
          <rect x={3190} y={1910} width={910} height={280} rx="12" fill={c.warningLight} stroke={c.warning} strokeWidth="2"/>
          <rect x={3190} y={1910} width={910} height={42} rx="12" fill={c.warning}/>
          <text x={3645} y={1938} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="16">E1: LLM Services</text>
          <text x={3210} y={1972} fill={c.muted} fontSize="10">External APIs</text>

          <rect x={3210} y={1990} width={430} height={180} rx="6" fill={c.card} stroke={c.warning}/>
          <text x={3425} y={2015} textAnchor="middle" fill={c.warning} fontWeight="bold" fontSize="11">Ollama (Self-hosted)</text>
          {['• nomic-embed-text','• mistral:7b','• deepseek-coder','213.173.109.76:10077'].map((t,i)=><text key={i} x={3225} y={2040+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          <rect x={3660} y={1990} width={420} height={180} rx="6" fill={c.card} stroke={c.warning}/>
          <text x={3870} y={2015} textAnchor="middle" fill={c.warning} fontWeight="bold" fontSize="11">Cloud LLMs</text>
          {['• Groq llama-3.3-70b','• Claude Haiku','• Rate limiting','• Cost tracking'].map((t,i)=><text key={i} x={3675} y={2040+i*18} fill={c.muted} fontSize="10">{t}</text>)}

          {/* ========== TIER 6: SERVICES (y=2250) ========== */}
          <text x={W/2} y={2270} textAnchor="middle" fill={c.text} fontWeight="bold" fontSize="20">TIER 6: CROSS-CUTTING SERVICES</text>

          {/* Registration */}
          <rect x={PAD} y={2310} width={1300} height={130} rx="12" fill={c.primaryLight} stroke={c.primary} strokeWidth="2"/>
          <rect x={PAD} y={2310} width={1300} height={42} rx="12" fill={c.primary}/>
          <text x={PAD+650} y={2338} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="14">REGISTRATION SERVICE</text>
          {['register_document()','add_lineage()','update_storage_ref()','get_document_chain()'].map((fn,i)=>(
            <g key={i}><rect x={PAD+20+i*315} y={2365} width={300} height={55} rx="6" fill={c.card} stroke={c.primary}/>
            <text x={PAD+20+i*315+150} y={2398} textAnchor="middle" fill={c.primary} fontWeight="bold" fontSize="10">{fn}</text></g>
          ))}

          {/* Metrics */}
          <rect x={1450} y={2310} width={1300} height={130} rx="12" fill={c.warningLight} stroke={c.warning} strokeWidth="2"/>
          <rect x={1450} y={2310} width={1300} height={42} rx="12" fill={c.warning}/>
          <text x={2100} y={2338} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="14">METRICS SERVICE</text>
          {['record_upload()','record_llm_call()','get_summary()','get_trends()'].map((fn,i)=>(
            <g key={i}><rect x={1470+i*315} y={2365} width={300} height={55} rx="6" fill={c.card} stroke={c.warning}/>
            <text x={1470+i*315+150} y={2398} textAnchor="middle" fill={c.warning} fontWeight="bold" fontSize="10">{fn}</text></g>
          ))}

          {/* Cleanup */}
          <rect x={2800} y={2310} width={1300} height={130} rx="12" fill={c.slateLight} stroke={c.slate} strokeWidth="2"/>
          <rect x={2800} y={2310} width={1300} height={42} rx="12" fill={c.slate}/>
          <text x={3450} y={2338} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="14">CLEANUP SERVICE</text>
          {['delete_document()','delete_table()','deep_clean()','clear_project()'].map((fn,i)=>(
            <g key={i}><rect x={2820+i*315} y={2365} width={300} height={55} rx="6" fill={c.card} stroke={c.slate}/>
            <text x={2820+i*315+150} y={2398} textAnchor="middle" fill={c.slate} fontWeight="bold" fontSize="10">{fn}</text></g>
          ))}

          {/* ========== WORK IN PROGRESS (y=2500) ========== */}
          <text x={W/2} y={2520} textAnchor="middle" fill={c.text} fontWeight="bold" fontSize="20">WORK IN PROGRESS</text>
          <text x={W/2} y={2545} textAnchor="middle" fill={c.muted} fontSize="11">Planned features not yet implemented</text>

          {/* WIP boxes */}
          {[
            {x:100,title:'🚧 EXPORT ENGINE',fns:[['export_to_pdf()','PDF reports'],['export_to_excel()','Advanced Excel'],['export_to_pptx()','PowerPoint'],['schedule_export()','Scheduled']]},
            {x:1100,title:'🚧 SECURITY LAYER',fns:[['role_based_access()','RBAC'],['data_encryption()','At-rest'],['audit_trail()','Logging'],['sso_integration()','SSO']]},
            {x:2100,title:'🚧 ENHANCEMENTS',fns:[['multi_tenant()','Multi-tenancy'],['api_gateway()','External API'],['workflow_builder()','Automation'],['notification_svc()','Alerts']]},
            {x:3100,title:'🚧 QUALITY (P5)',fns:[['chat_quality()','Better responses'],['playbook_ui()','Visual editor'],['performance()','Speed'],['ui_polish()','Frontend']]}
          ].map((sec,si)=>(
            <g key={si}>
              <rect x={sec.x} y={2580} width={980} height={220} rx="12" fill={c.wipLight} stroke={c.wip} strokeWidth="2" strokeDasharray="8 4"/>
              <rect x={sec.x} y={2580} width={980} height={42} rx="12" fill={c.wip}/>
              <text x={sec.x+490} y={2608} textAnchor="middle" fill={c.card} fontWeight="bold" fontSize="14">{sec.title}</text>
              {sec.fns.map(([nm,desc],fi)=>(
                <g key={fi}>
                  <rect x={sec.x+20+(fi%2)*480} y={2640+Math.floor(fi/2)*75} width={460} height={60} rx="6" fill={c.card} stroke={c.wip} strokeDasharray="4 2"/>
                  <text x={sec.x+20+(fi%2)*480+230} y={2668+Math.floor(fi/2)*75} textAnchor="middle" fill={c.wip} fontWeight="bold" fontSize="10">{nm}</text>
                  <text x={sec.x+20+(fi%2)*480+230} y={2688+Math.floor(fi/2)*75} textAnchor="middle" fill={c.muted} fontSize="9">{desc}</text>
                </g>
              ))}
            </g>
          ))}

          <text x={W-100} y={2880} textAnchor="end" fill={c.light} fontSize="10">XLR8 Platform v2.0 | Level 5 DFD | December 2025</text>
        </svg>
      </div>
    </div>
  );
};

export default ArchitecturePage;
