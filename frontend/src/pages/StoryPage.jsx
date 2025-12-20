<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>XLR8 - The Story</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #f5f6f8;
      --bg-alt: #eef0f4;
      --card: #ffffff;
      --card-border: #e4e7ec;
      --text: #2d3643;
      --text-muted: #6b7a8f;
      --text-light: #9aa5b5;
      --primary: #83b16d;
      --primary-light: rgba(131, 177, 109, 0.12);
      --primary-dark: #6a9b5a;
      --dusty-blue: #7889a0;
      --dusty-blue-light: rgba(120, 137, 160, 0.12);
      --taupe: #9b8f82;
      --taupe-light: rgba(155, 143, 130, 0.12);
      --slate: #6b7a8f;
      --slate-light: rgba(107, 122, 143, 0.12);
    }
    
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    
    body {
      font-family: 'Inter', system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
    }
    
    .mono { font-family: 'JetBrains Mono', monospace; }
    
    /* Progress bar */
    .progress-bar {
      position: fixed;
      top: 0;
      left: 0;
      height: 3px;
      background: var(--primary);
      z-index: 1000;
      transition: width 0.1s ease;
    }
    
    /* Nav */
    .nav {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(245, 246, 248, 0.95);
      backdrop-filter: blur(10px);
      z-index: 100;
      border-bottom: 1px solid var(--card-border);
    }
    
    .logo {
      font-family: 'Sora', sans-serif;
      font-size: 1.4rem;
      font-weight: 800;
      color: var(--primary);
    }
    
    .skip-btn {
      padding: 0.5rem 1rem;
      background: var(--card);
      border: 1px solid var(--card-border);
      color: var(--text);
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    
    .skip-btn:hover {
      border-color: var(--primary);
      color: var(--primary);
    }
    
    /* Chapter structure */
    .chapter {
      min-height: 100vh;
      padding: 8rem 2rem 6rem;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .chapter-inner {
      max-width: 1100px;
      width: 100%;
    }
    
    .chapter-label {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.7rem;
      font-weight: 500;
      color: var(--primary);
      letter-spacing: 2px;
      text-transform: uppercase;
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    
    .chapter-label::before {
      content: '';
      width: 24px;
      height: 2px;
      background: var(--primary);
    }
    
    h1 {
      font-family: 'Sora', sans-serif;
      font-size: 3.5rem;
      font-weight: 800;
      line-height: 1.1;
      letter-spacing: -0.03em;
      margin-bottom: 1.5rem;
    }
    
    h2 {
      font-family: 'Sora', sans-serif;
      font-size: 2.25rem;
      font-weight: 800;
      line-height: 1.2;
      letter-spacing: -0.02em;
      margin-bottom: 1rem;
    }
    
    .lead {
      font-size: 1.15rem;
      color: var(--text-muted);
      max-width: 600px;
      line-height: 1.7;
    }
    
    /* ============ CHAPTER 1: THE BEGINNING ============ */
    .ch-beginning {
      background: var(--bg);
      position: relative;
      overflow: hidden;
    }
    
    .ch-beginning::before {
      content: '';
      position: absolute;
      top: -50%;
      right: -20%;
      width: 800px;
      height: 800px;
      background: radial-gradient(circle, var(--primary-light) 0%, transparent 70%);
      pointer-events: none;
    }
    
    .origin-story {
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 4rem;
      align-items: center;
    }
    
    .typewriter {
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.5rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
    }
    
    .typewriter-header {
      display: flex;
      gap: 6px;
      margin-bottom: 1rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--card-border);
    }
    
    .typewriter-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--card-border);
    }
    
    .typewriter-line {
      color: var(--text-muted);
      margin-bottom: 0.5rem;
      display: flex;
    }
    
    .typewriter-line .num {
      color: var(--text-light);
      width: 24px;
      text-align: right;
      margin-right: 1rem;
      user-select: none;
    }
    
    .typewriter-line .comment { color: var(--slate); }
    .typewriter-line .keyword { color: var(--primary); }
    .typewriter-line .string { color: var(--dusty-blue); }
    .typewriter-line .func { color: var(--taupe); }
    
    /* ============ CHAPTER 2: THE PROBLEM ============ */
    .ch-problem {
      background: var(--bg-alt);
    }
    
    .problem-visual {
      margin-top: 3rem;
      display: flex;
      gap: 2rem;
      align-items: stretch;
    }
    
    .old-way {
      flex: 1;
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 2rem;
      position: relative;
    }
    
    .old-way::before {
      content: 'THE OLD WAY';
      position: absolute;
      top: -10px;
      left: 1.5rem;
      background: var(--bg-alt);
      padding: 0 0.5rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.65rem;
      font-weight: 600;
      color: var(--text-light);
      letter-spacing: 1px;
    }
    
    .pain-item {
      display: flex;
      align-items: flex-start;
      gap: 1rem;
      padding: 1rem 0;
      border-bottom: 1px dashed var(--card-border);
    }
    
    .pain-item:last-child { border-bottom: none; }
    
    .pain-icon {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: rgba(160, 112, 112, 0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1rem;
      flex-shrink: 0;
    }
    
    .pain-text strong {
      display: block;
      font-size: 0.9rem;
      margin-bottom: 0.25rem;
    }
    
    .pain-text span {
      font-size: 0.8rem;
      color: var(--text-muted);
    }
    
    .transform-arrow {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 0 1rem;
    }
    
    .arrow-line {
      width: 60px;
      height: 2px;
      background: linear-gradient(90deg, var(--card-border), var(--primary));
    }
    
    .arrow-label {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.65rem;
      color: var(--primary);
      margin-top: 0.5rem;
      letter-spacing: 1px;
    }
    
    .new-way {
      flex: 1;
      background: var(--card);
      border: 2px solid var(--primary);
      border-radius: 16px;
      padding: 2rem;
      position: relative;
    }
    
    .new-way::before {
      content: 'THE XLR8 WAY';
      position: absolute;
      top: -10px;
      left: 1.5rem;
      background: var(--bg-alt);
      padding: 0 0.5rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.65rem;
      font-weight: 600;
      color: var(--primary);
      letter-spacing: 1px;
    }
    
    .win-item {
      display: flex;
      align-items: flex-start;
      gap: 1rem;
      padding: 1rem 0;
      border-bottom: 1px dashed var(--primary-light);
    }
    
    .win-item:last-child { border-bottom: none; }
    
    .win-icon {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: var(--primary-light);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1rem;
      flex-shrink: 0;
      color: var(--primary);
    }
    
    .win-text strong {
      display: block;
      font-size: 0.9rem;
      margin-bottom: 0.25rem;
      color: var(--primary-dark);
    }
    
    .win-text span {
      font-size: 0.8rem;
      color: var(--text-muted);
    }
    
    /* ============ CHAPTER 3: THE INSIGHT ============ */
    .ch-insight {
      background: var(--bg);
    }
    
    .insight-block {
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 3rem;
      margin-top: 2rem;
      text-align: center;
    }
    
    .insight-formula {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 1.5rem;
      margin: 2rem 0;
      flex-wrap: wrap;
    }
    
    .formula-box {
      padding: 1.5rem 2rem;
      border-radius: 12px;
      text-align: center;
      min-width: 160px;
    }
    
    .formula-box.reality {
      background: var(--primary-light);
      border: 2px solid var(--primary);
    }
    
    .formula-box.intent {
      background: var(--dusty-blue-light);
      border: 2px solid var(--dusty-blue);
    }
    
    .formula-box.reference {
      background: var(--taupe-light);
      border: 2px solid var(--taupe);
    }
    
    .formula-box .icon {
      font-size: 2rem;
      margin-bottom: 0.5rem;
    }
    
    .formula-box .label {
      font-family: 'Sora', sans-serif;
      font-weight: 700;
      font-size: 1rem;
      margin-bottom: 0.25rem;
    }
    
    .formula-box.reality .label { color: var(--primary-dark); }
    .formula-box.intent .label { color: var(--dusty-blue); }
    .formula-box.reference .label { color: var(--taupe); }
    
    .formula-box .desc {
      font-size: 0.75rem;
      color: var(--text-muted);
    }
    
    .formula-operator {
      font-family: 'Sora', sans-serif;
      font-size: 2rem;
      font-weight: 800;
      color: var(--text-light);
    }
    
    .formula-equals {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
    }
    
    .formula-result {
      background: linear-gradient(135deg, var(--primary), var(--dusty-blue));
      color: white;
      padding: 1rem 2rem;
      border-radius: 12px;
      font-family: 'Sora', sans-serif;
      font-weight: 700;
      font-size: 1.1rem;
    }
    
    /* ============ CHAPTER 4: THE ARCHITECTURE ============ */
    .ch-architecture {
      background: var(--bg-alt);
    }
    
    .arch-diagram {
      margin-top: 3rem;
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 2.5rem;
    }
    
    .arch-layer {
      display: grid;
      grid-template-columns: 140px 1fr;
      gap: 1.5rem;
      align-items: center;
      padding: 1.5rem 0;
      border-bottom: 1px solid var(--card-border);
    }
    
    .arch-layer:last-child { border-bottom: none; }
    
    .layer-label {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 1px;
      color: var(--text-light);
      text-transform: uppercase;
    }
    
    .layer-content {
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
    }
    
    .layer-block {
      padding: 0.75rem 1.25rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    
    .layer-block.input { background: var(--slate-light); color: var(--slate); }
    .layer-block.process { background: var(--primary-light); color: var(--primary-dark); }
    .layer-block.store { background: var(--dusty-blue-light); color: var(--dusty-blue); }
    .layer-block.output { background: var(--taupe-light); color: var(--taupe); }
    
    .arch-flow {
      display: flex;
      justify-content: center;
      margin: 1.5rem 0;
    }
    
    .flow-arrow {
      display: flex;
      flex-direction: column;
      align-items: center;
      color: var(--text-light);
    }
    
    .flow-arrow span {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.65rem;
      letter-spacing: 1px;
    }
    
    /* ============ CHAPTER 5: THE INTELLIGENCE ============ */
    .ch-intelligence {
      background: var(--bg);
    }
    
    .intel-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1.25rem;
      margin-top: 3rem;
    }
    
    .intel-card {
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.5rem;
      transition: all 0.2s ease;
    }
    
    .intel-card:hover {
      border-color: var(--primary);
      transform: translateY(-2px);
    }
    
    .intel-card .icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: var(--primary-light);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
      margin-bottom: 1rem;
    }
    
    .intel-card h3 {
      font-size: 0.95rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
    }
    
    .intel-card p {
      font-size: 0.8rem;
      color: var(--text-muted);
      line-height: 1.5;
    }
    
    .intel-card .tag {
      display: inline-block;
      margin-top: 0.75rem;
      padding: 0.25rem 0.5rem;
      background: var(--bg);
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.65rem;
      color: var(--text-muted);
    }
    
    /* ============ CHAPTER 6: THE WORKFLOW ============ */
    .ch-workflow {
      background: var(--bg-alt);
    }
    
    .workflow-timeline {
      margin-top: 3rem;
      position: relative;
    }
    
    .workflow-timeline::before {
      content: '';
      position: absolute;
      left: 24px;
      top: 0;
      bottom: 0;
      width: 2px;
      background: linear-gradient(180deg, var(--primary), var(--dusty-blue), var(--taupe));
    }
    
    .workflow-step {
      display: flex;
      gap: 2rem;
      margin-bottom: 2rem;
      position: relative;
    }
    
    .step-marker {
      width: 50px;
      height: 50px;
      border-radius: 50%;
      background: var(--card);
      border: 3px solid var(--primary);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: 'Sora', sans-serif;
      font-weight: 800;
      font-size: 1.1rem;
      color: var(--primary);
      flex-shrink: 0;
      z-index: 1;
    }
    
    .step-content {
      flex: 1;
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.5rem;
    }
    
    .step-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.75rem;
    }
    
    .step-title {
      font-weight: 700;
      font-size: 1rem;
    }
    
    .step-time {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.7rem;
      color: var(--primary);
      background: var(--primary-light);
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
    }
    
    .step-desc {
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-bottom: 0.75rem;
    }
    
    .step-details {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }
    
    .step-detail {
      font-size: 0.7rem;
      padding: 0.35rem 0.6rem;
      background: var(--bg-alt);
      border-radius: 4px;
      color: var(--text-muted);
    }
    
    /* ============ CHAPTER 7: THE VALUE ============ */
    .ch-value {
      background: var(--bg);
    }
    
    .value-split {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 2rem;
      margin-top: 3rem;
    }
    
    .value-panel {
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 2rem;
    }
    
    .value-panel h3 {
      font-family: 'Sora', sans-serif;
      font-size: 1.25rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    
    .value-panel h3 .badge {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.6rem;
      padding: 0.25rem 0.5rem;
      background: var(--primary-light);
      color: var(--primary);
      border-radius: 4px;
      letter-spacing: 0.5px;
    }
    
    .value-panel .subtitle {
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-bottom: 1.5rem;
    }
    
    .value-list {
      list-style: none;
    }
    
    .value-list li {
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      padding: 0.75rem 0;
      border-bottom: 1px solid var(--card-border);
      font-size: 0.9rem;
    }
    
    .value-list li:last-child { border-bottom: none; }
    
    .value-list .check {
      color: var(--primary);
      font-weight: bold;
    }
    
    /* ============ CHAPTER 8: THE INVITATION ============ */
    .ch-cta {
      background: var(--bg-alt);
      text-align: center;
    }
    
    .cta-box {
      background: var(--card);
      border: 2px solid var(--primary);
      border-radius: 20px;
      padding: 4rem;
      max-width: 700px;
      margin: 0 auto;
    }
    
    .cta-box h2 {
      margin-bottom: 1rem;
    }
    
    .cta-box p {
      color: var(--text-muted);
      font-size: 1.1rem;
      margin-bottom: 2rem;
    }
    
    .cta-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem 2rem;
      background: var(--primary);
      color: white;
      border: none;
      border-radius: 12px;
      font-size: 1rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s ease;
      font-family: 'Sora', sans-serif;
    }
    
    .cta-btn:hover {
      background: var(--primary-dark);
      transform: translateY(-2px);
    }
    
    .cta-btn .arrow {
      transition: transform 0.2s ease;
    }
    
    .cta-btn:hover .arrow {
      transform: translateX(4px);
    }
    
    /* Footer */
    footer {
      padding: 2rem;
      text-align: center;
      color: var(--text-light);
      font-size: 0.8rem;
      background: var(--bg);
      border-top: 1px solid var(--card-border);
    }
    
    footer span {
      color: var(--primary);
    }
  </style>
</head>
<body>
  <div class="progress-bar" id="progress"></div>
  
  <!-- Nav -->
  <nav class="nav">
    <div class="logo">XLR8</div>
    <button class="skip-btn" onclick="window.location.href='/dashboard'">Skip to Dashboard →</button>
  </nav>

  <!-- Chapter 1: The Beginning -->
  <section class="chapter ch-beginning">
    <div class="chapter-inner">
      <div class="origin-story">
        <div>
          <div class="chapter-label">Chapter 01</div>
          <h1>We Built This<br/>For Ourselves</h1>
          <p class="lead">We're implementation consultants. We spent years drowning in spreadsheets, validating data manually, and starting from scratch on every project.</p>
          <p class="lead" style="margin-top: 1rem;">Then we built something better.</p>
        </div>
        
        <div class="typewriter">
          <div class="typewriter-header">
            <div class="typewriter-dot"></div>
            <div class="typewriter-dot"></div>
            <div class="typewriter-dot"></div>
          </div>
          <div class="typewriter-line"><span class="num">1</span><span class="comment">// The question we asked ourselves</span></div>
          <div class="typewriter-line"><span class="num">2</span></div>
          <div class="typewriter-line"><span class="num">3</span><span class="keyword">const</span> problem = {</div>
          <div class="typewriter-line"><span class="num">4</span>&nbsp;&nbsp;hours: <span class="string">"too many"</span>,</div>
          <div class="typewriter-line"><span class="num">5</span>&nbsp;&nbsp;spreadsheets: <span class="string">"endless"</span>,</div>
          <div class="typewriter-line"><span class="num">6</span>&nbsp;&nbsp;mistakes: <span class="string">"inevitable"</span>,</div>
          <div class="typewriter-line"><span class="num">7</span>&nbsp;&nbsp;knowledge: <span class="string">"trapped in heads"</span></div>
          <div class="typewriter-line"><span class="num">8</span>};</div>
          <div class="typewriter-line"><span class="num">9</span></div>
          <div class="typewriter-line"><span class="num">10</span><span class="func">whatIf</span>(<span class="string">"there's a better way?"</span>);</div>
        </div>
      </div>
    </div>
  </section>

  <!-- Chapter 2: The Problem -->
  <section class="chapter ch-problem">
    <div class="chapter-inner">
      <div class="chapter-label">Chapter 02</div>
      <h2>The Transformation</h2>
      <p class="lead">Here's what changed when we stopped accepting "that's just how it's done."</p>
      
      <div class="problem-visual">
        <div class="old-way">
          <div class="pain-item">
            <div class="pain-icon">📊</div>
            <div class="pain-text">
              <strong>Weeks in Spreadsheets</strong>
              <span>Every project starts from zero. Build formulas, cross-reference, repeat.</span>
            </div>
          </div>
          <div class="pain-item">
            <div class="pain-icon">🔍</div>
            <div class="pain-text">
              <strong>Manual Validation</strong>
              <span>Hope you didn't miss anything. Hope the formula didn't break.</span>
            </div>
          </div>
          <div class="pain-item">
            <div class="pain-icon">🧠</div>
            <div class="pain-text">
              <strong>Knowledge Silos</strong>
              <span>Expertise lives in people's heads. When they leave, it leaves.</span>
            </div>
          </div>
          <div class="pain-item">
            <div class="pain-icon">❓</div>
            <div class="pain-text">
              <strong>Incomplete Coverage</strong>
              <span>Can't check everything. Prioritize and pray.</span>
            </div>
          </div>
        </div>
        
        <div class="transform-arrow">
          <div class="arrow-line"></div>
          <div class="arrow-label">XLR8</div>
        </div>
        
        <div class="new-way">
          <div class="win-item">
            <div class="win-icon">⚡</div>
            <div class="win-text">
              <strong>Minutes, Not Weeks</strong>
              <span>Upload data. Get instant analysis. Ask questions in English.</span>
            </div>
          </div>
          <div class="win-item">
            <div class="win-icon">🤖</div>
            <div class="win-text">
              <strong>Automatic Validation</strong>
              <span>Every check runs every time. Nothing slips through.</span>
            </div>
          </div>
          <div class="win-item">
            <div class="win-icon">📚</div>
            <div class="win-text">
              <strong>Captured Knowledge</strong>
              <span>Standards and playbooks live in the system. Forever.</span>
            </div>
          </div>
          <div class="win-item">
            <div class="win-icon">✅</div>
            <div class="win-text">
              <strong>Complete Coverage</strong>
              <span>Check everything. Surface all issues. Miss nothing.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Chapter 3: The Insight -->
  <section class="chapter ch-insight">
    <div class="chapter-inner">
      <div class="chapter-label">Chapter 03</div>
      <h2>The Core Insight</h2>
      <p class="lead">Every engagement has three sources of truth. The magic happens when you connect them—especially when compliance is on the line.</p>
      
      <div class="insight-block">
        <div class="insight-formula">
          <div class="formula-box reality">
            <div class="icon">🗄️</div>
            <div class="label">Reality</div>
            <div class="desc">What actually exists</div>
          </div>
          
          <div class="formula-operator">×</div>
          
          <div class="formula-box intent">
            <div class="icon">📋</div>
            <div class="label">Intent</div>
            <div class="desc">What was requested</div>
          </div>
          
          <div class="formula-operator">×</div>
          
          <div class="formula-box reference">
            <div class="icon">⚖️</div>
            <div class="label">Reference</div>
            <div class="desc">Laws & compliance</div>
          </div>
          
          <div class="formula-equals">
            <div class="formula-operator">=</div>
          </div>
          
          <div class="formula-result">Complete Picture</div>
        </div>
        
        <p style="color: var(--text-muted); max-width: 600px; margin: 2rem auto 0; font-size: 0.95rem;">
          Most tools only see one piece. XLR8 connects all three—automatically finding gaps between what exists, what was asked for, and what the law requires.
        </p>
        
        <!-- Compliance callout -->
        <div style="margin-top: 2rem; padding: 1.25rem; background: var(--taupe-light); border: 2px solid var(--taupe); border-radius: 12px; text-align: left; display: flex; align-items: flex-start; gap: 1rem;">
          <span style="font-size: 1.5rem;">⚖️</span>
          <div>
            <div style="font-weight: 700; color: var(--text); margin-bottom: 0.4rem;">Reference = The "Oh Shit" Layer</div>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin: 0; line-height: 1.6;">
              Legislation. Regulations. FLSA, ACA, state labor laws, data privacy requirements. This isn't just best practice—it's legal exposure. XLR8 validates your data against the laws that matter, catching compliance gaps before they become audit findings or lawsuits.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Chapter 4: The Architecture -->
  <section class="chapter ch-architecture">
    <div class="chapter-inner">
      <div class="chapter-label">Chapter 04</div>
      <h2>How It Works</h2>
      <p class="lead">Under the hood: a purpose-built intelligence engine that learns and improves with every project.</p>
      
      <div class="arch-diagram">
        <div class="arch-layer">
          <div class="layer-label">Input</div>
          <div class="layer-content">
            <div class="layer-block input">📊 Excel / CSV</div>
            <div class="layer-block input">📄 PDFs</div>
            <div class="layer-block input">📝 Word Docs</div>
            <div class="layer-block input">📋 Requirements</div>
          </div>
        </div>
        
        <div class="arch-flow">
          <div class="flow-arrow">
            <span>↓ CLASSIFY</span>
          </div>
        </div>
        
        <div class="arch-layer">
          <div class="layer-label">Process</div>
          <div class="layer-content">
            <div class="layer-block process">🧠 Auto-Classification</div>
            <div class="layer-block process">🔗 Relationship Detection</div>
            <div class="layer-block process">📊 Data Profiling</div>
            <div class="layer-block process">✅ Quality Scoring</div>
          </div>
        </div>
        
        <div class="arch-flow">
          <div class="flow-arrow">
            <span>↓ STORE</span>
          </div>
        </div>
        
        <div class="arch-layer">
          <div class="layer-label">Three Truths</div>
          <div class="layer-content">
            <div class="layer-block store" style="background: var(--primary-light); color: var(--primary-dark);">🗄️ Reality Layer</div>
            <div class="layer-block store">📋 Intent Layer</div>
            <div class="layer-block store" style="background: var(--taupe-light); color: var(--taupe);">📖 Reference Layer</div>
          </div>
        </div>
        
        <div class="arch-flow">
          <div class="flow-arrow">
            <span>↓ ANALYZE</span>
          </div>
        </div>
        
        <div class="arch-layer">
          <div class="layer-label">Output</div>
          <div class="layer-content">
            <div class="layer-block output">💬 Natural Language Answers</div>
            <div class="layer-block output">📋 Playbook Results</div>
            <div class="layer-block output">🎯 Findings & Tasks</div>
            <div class="layer-block output">📈 Reports</div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Chapter 5: The Intelligence -->
  <section class="chapter ch-intelligence">
    <div class="chapter-inner">
      <div class="chapter-label">Chapter 05</div>
      <h2>Built-In Intelligence</h2>
      <p class="lead">Not just storage. Not just search. Actual understanding.</p>
      
      <div class="intel-grid">
        <div class="intel-card">
          <div class="icon">🎯</div>
          <h3>Auto-Classification</h3>
          <p>Documents analyzed and routed to the right Truth layer. No manual tagging.</p>
          <span class="tag">ON UPLOAD</span>
        </div>
        <div class="intel-card">
          <div class="icon">🔗</div>
          <h3>Relationship Discovery</h3>
          <p>Foreign keys and connections found automatically. Smart JOINs without config.</p>
          <span class="tag">AUTOMATIC</span>
        </div>
        <div class="intel-card">
          <div class="icon">📊</div>
          <h3>Data Quality Scoring</h3>
          <p>Every file gets a health score. Issues flagged before they become problems.</p>
          <span class="tag">REAL-TIME</span>
        </div>
        <div class="intel-card">
          <div class="icon">🧠</div>
          <h3>Pattern Learning</h3>
          <p>Common queries cached. The system gets faster the more you use it.</p>
          <span class="tag">CONTINUOUS</span>
        </div>
        <div class="intel-card">
          <div class="icon">💬</div>
          <h3>Natural Language</h3>
          <p>Ask questions in plain English. "How many employees in CA?" Just works.</p>
          <span class="tag">NO SQL NEEDED</span>
        </div>
        <div class="intel-card">
          <div class="icon">✅</div>
          <h3>Standards Validation</h3>
          <p>Upload compliance rules once. Validate against them forever.</p>
          <span class="tag">AUTOMATED</span>
        </div>
      </div>
    </div>
  </section>

  <!-- Chapter 6: The Workflow -->
  <section class="chapter ch-workflow">
    <div class="chapter-inner">
      <div class="chapter-label">Chapter 06</div>
      <h2>The Workflow</h2>
      <p class="lead">From raw data to actionable findings in minutes, not weeks.</p>
      
      <div class="workflow-timeline">
        <div class="workflow-step">
          <div class="step-marker">1</div>
          <div class="step-content">
            <div class="step-header">
              <div class="step-title">Upload Your Data</div>
              <div class="step-time">INSTANT</div>
            </div>
            <div class="step-desc">Drop employee exports, configuration tables, requirements docs. Any format.</div>
            <div class="step-details">
              <span class="step-detail">Excel</span>
              <span class="step-detail">CSV</span>
              <span class="step-detail">PDF</span>
              <span class="step-detail">Word</span>
            </div>
          </div>
        </div>
        
        <div class="workflow-step">
          <div class="step-marker">2</div>
          <div class="step-content">
            <div class="step-header">
              <div class="step-title">Automatic Analysis</div>
              <div class="step-time">~30 SECONDS</div>
            </div>
            <div class="step-desc">Classification, profiling, relationship detection—all happens automatically.</div>
            <div class="step-details">
              <span class="step-detail">Classify to Truth layer</span>
              <span class="step-detail">Profile columns</span>
              <span class="step-detail">Detect lookups</span>
              <span class="step-detail">Score quality</span>
            </div>
          </div>
        </div>
        
        <div class="workflow-step">
          <div class="step-marker">3</div>
          <div class="step-content">
            <div class="step-header">
              <div class="step-title">Ask Questions</div>
              <div class="step-time">~2 SECONDS</div>
            </div>
            <div class="step-desc">Natural language queries across all your data. Get answers, not just results.</div>
            <div class="step-details">
              <span class="step-detail">"How many employees are missing SSNs?"</span>
              <span class="step-detail">"What ALE groups are configured?"</span>
            </div>
          </div>
        </div>
        
        <div class="workflow-step">
          <div class="step-marker">4</div>
          <div class="step-content">
            <div class="step-header">
              <div class="step-title">Run Playbooks</div>
              <div class="step-time">~1 MINUTE</div>
            </div>
            <div class="step-desc">Execute standard validation workflows. Same checks, every project, every time.</div>
            <div class="step-details">
              <span class="step-detail">Data Quality Audit</span>
              <span class="step-detail">Compliance Check</span>
              <span class="step-detail">Configuration Review</span>
            </div>
          </div>
        </div>
        
        <div class="workflow-step">
          <div class="step-marker">5</div>
          <div class="step-content">
            <div class="step-header">
              <div class="step-title">Get Findings</div>
              <div class="step-time">AUTOMATIC</div>
            </div>
            <div class="step-desc">Issues surfaced with context, severity, and recommendations. Ready to act on.</div>
            <div class="step-details">
              <span class="step-detail">Prioritized by severity</span>
              <span class="step-detail">Actionable recommendations</span>
              <span class="step-detail">Track to resolution</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Chapter 7: The Value -->
  <section class="chapter ch-value">
    <div class="chapter-inner">
      <div class="chapter-label">Chapter 07</div>
      <h2>Who This Is For</h2>
      <p class="lead">Built by consultants for consultants—and the customers who trust them.</p>
      
      <div class="value-split">
        <div class="value-panel">
          <h3>For Consultants <span class="badge">YOU</span></h3>
          <p class="subtitle">Deliver better work in less time. Scale your expertise.</p>
          <ul class="value-list">
            <li><span class="check">✓</span> Cut analysis time by 80%</li>
            <li><span class="check">✓</span> Systematic validation—nothing missed</li>
            <li><span class="check">✓</span> Playbooks capture your methodology</li>
            <li><span class="check">✓</span> Ask questions in plain English</li>
            <li><span class="check">✓</span> Standards validate automatically</li>
            <li><span class="check">✓</span> Onboard new team members faster</li>
          </ul>
        </div>
        
        <div class="value-panel">
          <h3>For Customers <span class="badge">THEM</span></h3>
          <p class="subtitle">Visibility, quality, and confidence in their implementation.</p>
          <ul class="value-list">
            <li><span class="check">✓</span> See exactly where the project stands</li>
            <li><span class="check">✓</span> Higher quality implementations</li>
            <li><span class="check">✓</span> Issues caught early, not at go-live</li>
            <li><span class="check">✓</span> Evidence-based readiness decisions</li>
            <li><span class="check">✓</span> Faster time to value</li>
            <li><span class="check">✓</span> Audit-ready documentation</li>
          </ul>
        </div>
      </div>
    </div>
  </section>

  <!-- Chapter 8: The Invitation -->
  <section class="chapter ch-cta">
    <div class="chapter-inner">
      <div class="cta-box">
        <div class="chapter-label" style="justify-content: center;">Chapter 08</div>
        <h2>Ready to See It?</h2>
        <p>This isn't a pitch deck. This is the product. Let's go.</p>
        <button class="cta-btn" onclick="window.location.href='/dashboard'">
          Enter XLR8 <span class="arrow">→</span>
        </button>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer>
    <p>Built with 💚 by <span>XLR8</span> · The platform that replaced our spreadsheets</p>
  </footer>

  <script>
    // Progress bar
    window.addEventListener('scroll', () => {
      const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
      const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const scrolled = (winScroll / height) * 100;
      document.getElementById('progress').style.width = scrolled + '%';
    });
  </script>
</body>
</html>
