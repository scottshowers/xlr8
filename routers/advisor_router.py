"""
Work Advisor Router

A conversational AI that helps users figure out the best approach for their task.
Guides them to the right feature or helps them build a playbook.
"""

import logging
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import re
import json

logger = logging.getLogger(__name__)

# LLM orchestrator for consistent Claude calls
from utils.llm_orchestrator import LLMOrchestrator
_advisor_orchestrator = LLMOrchestrator()

router = APIRouter(tags=["advisor"])


class AdvisorMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class AdvisorChatRequest(BaseModel):
    messages: List[AdvisorMessage]
    system_prompt: Optional[str] = None


class AdvisorChatResponse(BaseModel):
    response: str
    recommendation: Optional[Any] = None  # Feature key or list of keys
    playbook_draft: Optional[Dict] = None
    confidence: float = 0.0


# Keywords and patterns that suggest specific features
FEATURE_SIGNALS = {
    'CHAT': {
        'keywords': ['explore', 'think through', 'help me understand', 'analyze', 'review', 'look at', 'what do you think'],
        'anti_keywords': ['compare', 'reconcile', 'steps', 'workflow', 'deliverable', 'report'],
        'patterns': [r'help me (think|figure|understand)', r'what (should|could) I', r'take a look']
    },
    'VACUUM': {
        'keywords': ['upload', 'load data', 'ingest', 'import', 'get data in'],
        'anti_keywords': [],
        'patterns': [r'(upload|load|import) (my|the|this) (data|file|spreadsheet)']
    },
    'BI_BUILDER': {
        'keywords': ['report', 'dashboard', 'chart', 'trend', 'metrics', 'kpi', 'visualization', 'how many', 'show me'],
        'anti_keywords': ['compare', 'reconcile'],
        'patterns': [r'(build|create|make) (a |the )?(report|dashboard|chart)', r'show me .* by']
    },
    'PLAYBOOK_EXISTING': {
        'keywords': ['year-end', 'yearend', 'year end', 'readiness'],
        'anti_keywords': [],
        'patterns': [r'year.?end', r'readiness (check|audit)']
    },
    'COMPARE': {
        'keywords': ['compare', 'reconcile', 'variance', 'difference', 'parallel', 'before and after', 'historical vs', 'legacy vs'],
        'anti_keywords': [],
        'patterns': [r'compare .* (to|with|against)', r'(find|show) (the )?(difference|variance)', r'parallel test']
    },
    'GL_MAPPER': {
        'keywords': ['gl', 'general ledger', 'chart of accounts', 'account mapping', 'gl unwrap', 'segment'],
        'anti_keywords': [],
        'patterns': [r'(gl|general ledger) (mapping|configuration|setup)', r'map .* accounts']
    }
}

# Questions to understand the user's needs better
CLARIFYING_QUESTIONS = [
    "What's the end goal here - is there a specific deliverable you need to produce?",
    "Will you need to do this again for other customers, or is it a one-time thing?",
    "Do you have files ready to upload, or are you still gathering what you need?",
    "Are you looking for structured steps to follow, or more of a thought partner to work through this?",
    "Is there a customer deadline driving this?",
    "Have you done something similar before, or is this new territory?",
    "What would 'done' look like for this task?"
]


def analyze_conversation(messages: List[Dict]) -> Dict:
    """
    Analyze the conversation to understand user intent and determine
    if we have enough information to make a recommendation.
    """
    # Combine all user messages
    user_text = ' '.join([
        m['content'].lower() 
        for m in messages 
        if m['role'] == 'user'
    ])
    
    # Count conversation turns
    user_turns = sum(1 for m in messages if m['role'] == 'user')
    
    # Score each feature based on signals
    scores = {}
    for feature, signals in FEATURE_SIGNALS.items():
        score = 0
        
        # Check keywords
        for keyword in signals['keywords']:
            if keyword in user_text:
                score += 2
        
        # Check anti-keywords (reduce score)
        for anti in signals['anti_keywords']:
            if anti in user_text:
                score -= 1
        
        # Check patterns
        for pattern in signals['patterns']:
            if re.search(pattern, user_text):
                score += 3
        
        scores[feature] = max(0, score)
    
    # Determine if we should recommend yet
    max_score = max(scores.values()) if scores else 0
    total_score = sum(scores.values())
    
    # Check for playbook indicators FIRST
    playbook_indicators = [
        'repeatable', 'every time', 'standard process', 'workflow',
        'steps', 'checklist', 'deliverable', 'for other customers',
        'do this again', 'reusable', 'other customers', 'template',
        'xlsx', 'excel', 'output'
    ]
    wants_playbook = any(ind in user_text for ind in playbook_indicators)
    
    # Strong playbook signals - user clearly said yes to repeatable
    strong_playbook = any(phrase in user_text for phrase in [
        'other customers', 'yes', 'both', 'every time', 'template'
    ])
    
    # One-off indicators
    oneoff_indicators = [
        'just this once', 'one time', 'this particular', 'quick',
        'just need to', 'real quick'
    ]
    wants_oneoff = any(ind in user_text for ind in oneoff_indicators)
    
    # Need enough conversation AND clear signal
    # OR if user has given clear playbook signals after 2+ turns
    ready_to_recommend = (
        (user_turns >= 2 and max_score >= 4 and (max_score / max(total_score, 1)) > 0.4) or
        (user_turns >= 3 and wants_playbook) or
        (user_turns >= 2 and strong_playbook)  # User clearly said yes to repeatable
    )
    
    # Get top features
    sorted_features = sorted(scores.items(), key=lambda x: -x[1])
    top_feature = sorted_features[0][0] if sorted_features and sorted_features[0][1] > 0 else None
    
    return {
        'scores': scores,
        'max_score': max_score,
        'user_turns': user_turns,
        'ready_to_recommend': ready_to_recommend,
        'top_feature': top_feature,
        'wants_playbook': wants_playbook,
        'wants_oneoff': wants_oneoff,
        'user_text': user_text
    }


def extract_playbook_draft(messages: List[Dict], analysis: Dict) -> Optional[Dict]:
    """
    If the user wants a playbook, try to extract a draft from the conversation.
    """
    user_text = analysis['user_text']
    
    # Try to identify inputs mentioned
    inputs = []
    input_patterns = [
        r'upload (?:my |the |a )?([^,\.]+)',
        r'have (?:a |the )?([^,\.]+) (?:file|report|data)',
        r'([^,\.]+) (?:from|file|report|spreadsheet)'
    ]
    for pattern in input_patterns:
        matches = re.findall(pattern, user_text)
        inputs.extend(matches[:3])  # Limit
    
    # Try to identify outputs mentioned
    outputs = []
    output_patterns = [
        r'(?:produce|create|generate|need) (?:a |the )?([^,\.]+)',
        r'deliverable[s]? (?:like |is |are )?([^,\.]+)',
        r'(?:end up with|result in) (?:a |the )?([^,\.]+)'
    ]
    for pattern in output_patterns:
        matches = re.findall(pattern, user_text)
        outputs.extend(matches[:3])
    
    if not inputs and not outputs:
        return None
    
    return {
        'name': '',
        'description': '',
        'inputs': [{'name': inp.strip(), 'type': 'file', 'description': ''} for inp in inputs if inp.strip()],
        'steps': [],
        'outputs': [{'name': out.strip(), 'format': 'report', 'description': ''} for out in outputs if out.strip()]
    }


@router.post("/chat", response_model=AdvisorChatResponse)
async def advisor_chat(request: AdvisorChatRequest):
    """
    Process a conversation turn with the Work Advisor.
    Returns a response and potentially a recommendation.
    
    Under the hood, this just calls unified chat with the advisor persona.
    """
    try:
        messages = [m.dict() for m in request.messages]
        
        # Analyze what we know so far
        analysis = analyze_conversation(messages)
        
        logger.info(f"[ADVISOR] Analysis: turns={analysis['user_turns']}, "
                   f"max_score={analysis['max_score']}, "
                   f"top={analysis['top_feature']}, "
                   f"ready={analysis['ready_to_recommend']}")
        
        # Build system prompt with analysis context
        system_prompt = request.system_prompt or ADVISOR_PERSONA
        
        context_addition = f"""

ANALYSIS OF CONVERSATION SO FAR:
- User turns: {analysis['user_turns']}
- Top feature match: {analysis['top_feature']} (score: {analysis['max_score']})
- Feature scores: {json.dumps(analysis['scores'])}
- Wants playbook (repeatable): {analysis['wants_playbook']}
- Wants one-off: {analysis['wants_oneoff']}
- Ready to recommend: {analysis['ready_to_recommend']}

{"INSTRUCTION: Based on the analysis, you have enough information. Make a clear recommendation and explain WHY. End your message with the recommendation." if analysis['ready_to_recommend'] else "INSTRUCTION: You need more information. Ask ONE focused follow-up question to better understand their needs. Pick from these angles: deliverable/output, repeatable vs one-time, file types, structured steps vs exploration, timeline."}

If recommending, use one of these exact phrases at the END of your response:
- "I recommend using **Chat**" 
- "I recommend using **Vacuum** to upload your data first"
- "I recommend the **BI Builder**"
- "I recommend running the **Year-End Readiness** playbook"
- "I recommend we **build a playbook** for this"
- "I recommend the **Compare** feature" (note: coming soon)
- "I recommend the **GL Mapper**" (note: coming soon)
"""
        
        full_system = system_prompt + context_addition
        
        # Get the last user message
        last_user_message = ""
        for msg in reversed(messages):
            if msg['role'] == 'user':
                last_user_message = msg['content']
                break
        
        # Call LLM (try Ollama first, then Claude, then fallback)
        response_text = None
        
        # Try Ollama/Mistral first
        try:
            import os
            import httpx
            
            ollama_url = os.environ.get('OLLAMA_API_URL', 'http://ollama:11434')
            
            # Build prompt
            prompt_parts = [full_system, "\n"]
            for msg in messages:
                if msg['role'] == 'user':
                    prompt_parts.append(f"Human: {msg['content']}\n")
                elif msg['role'] == 'assistant':
                    prompt_parts.append(f"Assistant: {msg['content']}\n")
            prompt_parts.append("Assistant:")
            
            full_prompt = "".join(prompt_parts)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                ollama_response = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": "mistral",
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 500}
                    }
                )
                
                if ollama_response.status_code == 200:
                    data = ollama_response.json()
                    response_text = data.get('response', '').strip()
                    logger.info("[ADVISOR] Got response from Ollama/Mistral")
                    
        except Exception as ollama_error:
            logger.warning(f"[ADVISOR] Ollama failed: {ollama_error}")
        
        # Try Claude if Ollama failed - use orchestrator for consistency
        if not response_text:
            try:
                global _advisor_orchestrator
                if _advisor_orchestrator:
                    # Build conversation for orchestrator
                    conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
                    
                    # Use synthesize_answer which handles local->Claude fallback
                    result = _advisor_orchestrator.synthesize_answer(
                        question=conversation_text,
                        context="",  # Context is in the conversation
                        expert_prompt=full_system,
                        use_claude_fallback=True
                    )
                    
                    if result.get('success') and result.get('response'):
                        response_text = result['response']
                        logger.info(f"[ADVISOR] Got response from {result.get('model_used', 'unknown')}")
                else:
                    logger.warning("[ADVISOR] LLMOrchestrator not available")
                
            except Exception as claude_error:
                logger.warning(f"[ADVISOR] LLM synthesis failed: {claude_error}")
        
        # Final fallback
        if not response_text:
            logger.warning("[ADVISOR] All LLMs failed, using fallback response")
            response_text = _get_fallback_response(analysis, messages)
        
        # Parse recommendation from response
        recommendation = None
        playbook_draft = None
        
        rec_patterns = {
            'CHAT': r'recommend.*\*\*Chat\*\*',
            'VACUUM': r'recommend.*\*\*Vacuum\*\*',
            'BI_BUILDER': r'recommend.*\*\*BI Builder\*\*',
            'PLAYBOOK_EXISTING': r'recommend.*\*\*Year-End',
            'PLAYBOOK_NEW': r'recommend.*\*\*build a playbook\*\*',
            'COMPARE': r'recommend.*\*\*Compare\*\*',
            'GL_MAPPER': r'recommend.*\*\*GL Mapper\*\*'
        }
        
        for feature, pattern in rec_patterns.items():
            if re.search(pattern, response_text, re.IGNORECASE):
                recommendation = feature
                break
        
        # If recommending new playbook, try to extract draft
        if recommendation == 'PLAYBOOK_NEW':
            playbook_draft = extract_playbook_draft(messages, analysis)
        
        return AdvisorChatResponse(
            response=response_text,
            recommendation=recommendation,
            playbook_draft=playbook_draft,
            confidence=analysis['max_score'] / 10.0 if analysis['max_score'] else 0.0
        )
        
    except Exception as e:
        logger.error(f"[ADVISOR] Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Advisor error: {str(e)}")


def _get_fallback_response(analysis: Dict, messages: List[Dict] = None) -> str:
    """Generate fallback response when LLM unavailable."""
    messages = messages or []
    
    # If we have enough info, make a recommendation
    if analysis['ready_to_recommend'] or analysis['user_turns'] >= 3:
        feature = analysis['top_feature']
        
        # Check for playbook signals
        if analysis['wants_playbook'] or any(
            word in analysis.get('user_text', '').lower() 
            for word in ['other customers', 'repeatable', 'every time', 'again']
        ):
            return "Based on what you've described - this is something you'll do repeatedly with a clear output format - I recommend we **build a playbook** for this. That way your whole team can follow the same process and produce consistent deliverables."
        
        if feature == 'COMPARE':
            return "This sounds like a comparison/reconciliation task. I recommend the **Compare** feature - though I should mention it's still being built. In the meantime, you could use **Chat** to upload both files and work through the comparison manually."
        elif feature == 'GL_MAPPER':
            return "This sounds like a GL configuration task. I recommend the **GL Mapper** - though it's still being built. For now, you could use **Chat** to upload your files and I can help you work through the mapping."
        elif feature == 'BI_BUILDER':
            return "This sounds like you want to analyze and visualize your data. I recommend the **BI Builder** - you can ask questions in plain English and build charts and reports."
        elif feature == 'VACUUM':
            return "First things first - let's get your data into the system. I recommend using **Vacuum** to upload and profile your files."
        elif feature == 'CHAT':
            return "This sounds like an exploratory task where you want to think through something. I recommend using **Chat** - upload your files and have a conversation with AI to work through it."
        else:
            # Default to playbook if they mentioned outputs/templates/repeatable
            user_text = analysis.get('user_text', '').lower()
            if any(word in user_text for word in ['template', 'output', 'deliverable', 'xlsx', 'excel']):
                return "Since you have a defined output template and this is repeatable, I recommend we **build a playbook** for this. It will ensure consistent results every time."
            return "Based on what you've shared, I recommend we **build a playbook** for this workflow."
    
    # Not enough info yet - ask a NEW question based on what we DON'T know
    user_text = analysis.get('user_text', '').lower()
    assistant_text = ' '.join([m['content'].lower() for m in messages if m.get('role') == 'assistant'])
    
    # Track what we've learned
    knows_repeatable = any(word in user_text for word in ['other customers', 'every time', 'again', 'repeatable', 'yes'])
    knows_output = any(word in user_text for word in ['template', 'xlsx', 'excel', 'output', 'deliverable', 'report'])
    knows_structured = any(word in user_text for word in ['steps', 'structured', 'workflow', 'both'])
    
    # Ask about what we DON'T know yet
    if not knows_output and 'output' not in assistant_text and 'deliverable' not in assistant_text:
        return "What's the end deliverable? Is there a specific output format you need to produce?"
    
    if not knows_repeatable and 'repeat' not in assistant_text and 'other customers' not in assistant_text:
        return "Is this something you'll do for multiple customers, or just this one?"
    
    if not knows_structured and 'structured' not in assistant_text and 'steps' not in assistant_text:
        return "Do you want a defined workflow with clear steps, or more flexibility to explore?"
    
    # If we've asked the main questions, make a recommendation
    return "Got it! Based on what you've shared - repeatable process with defined outputs - I recommend we **build a playbook** for this. Ready to set it up?"


@router.get("/features")
async def get_features():
    """
    Get list of available features for quick access.
    """
    return {
        "features": [
            {
                "key": "CHAT",
                "title": "Chat",
                "description": "Upload files and have a conversation",
                "route": "/chat",
                "available": True
            },
            {
                "key": "VACUUM",
                "title": "Upload Data (Vacuum)",
                "description": "Ingest and profile data files",
                "route": "/data/vacuum",
                "available": True
            },
            {
                "key": "BI_BUILDER",
                "title": "BI Builder",
                "description": "Build reports and dashboards",
                "route": "/bi-builder",
                "available": True
            },
            {
                "key": "PLAYBOOK_EXISTING",
                "title": "Run Playbook",
                "description": "Execute a structured workflow",
                "route": "/playbooks",
                "available": True
            },
            {
                "key": "PLAYBOOK_NEW",
                "title": "Build Playbook",
                "description": "Create a new reusable workflow",
                "route": None,
                "available": True
            },
            {
                "key": "COMPARE",
                "title": "Compare & Reconcile",
                "description": "Compare datasets and find variances",
                "route": "/compare",
                "available": False
            },
            {
                "key": "GL_MAPPER",
                "title": "GL Configuration",
                "description": "Map legacy GL to new system",
                "route": "/gl-mapper",
                "available": False
            }
        ]
    }


class GeneratePlaybookRequest(BaseModel):
    description: str


PLAYBOOK_GENERATION_PROMPT = """You are an expert implementation consultant. Based on the user's description, design a structured playbook with clear inputs, steps, and outputs.

USER'S DESCRIPTION:
{description}

Generate a JSON response with this exact structure:
{{
  "name": "Short descriptive name for the playbook",
  "description": "1-2 sentence summary of what this playbook accomplishes",
  "inputs": [
    {{"name": "Input name", "type": "file", "description": "What this input is and what format"}}
  ],
  "steps": [
    {{"title": "Step title", "description": "What happens in this step and what AI does", "ai_assisted": true}}
  ],
  "outputs": [
    {{"name": "Output name", "format": "spreadsheet or report or data", "description": "What this deliverable contains"}}
  ]
}}

Guidelines:
- Steps should be logical and sequential
- Each step should have a clear purpose
- Mark steps as ai_assisted: true if AI does analysis/comparison/generation
- Mark steps as ai_assisted: false if it's human review/approval
- Include data profiling/validation as early steps
- Include a final review/QA step
- Outputs should be concrete deliverables the customer receives
- Be specific about what each step does, not vague

Return ONLY valid JSON, no explanation or markdown."""


@router.post("/generate-playbook")
async def generate_playbook(request: GeneratePlaybookRequest):
    """
    Use AI to generate a playbook structure based on user's description.
    """
    try:
        description = request.description
        logger.info(f"[ADVISOR] Generating playbook for: {description[:100]}...")
        
        prompt = PLAYBOOK_GENERATION_PROMPT.format(description=description)
        response_text = None
        
        # Try Ollama/Mistral first
        try:
            import os
            import httpx
            
            ollama_url = os.environ.get('OLLAMA_API_URL', 'http://ollama:11434')
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                ollama_response = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": "mistral",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 2000}
                    }
                )
                
                if ollama_response.status_code == 200:
                    data = ollama_response.json()
                    response_text = data.get('response', '').strip()
                    logger.info("[ADVISOR] Got playbook structure from Ollama")
                    
        except Exception as ollama_error:
            logger.warning(f"[ADVISOR] Ollama failed for playbook gen: {ollama_error}")
        
        # Try Claude if Ollama failed - use orchestrator for consistency
        if not response_text:
            try:
                global _advisor_orchestrator
                if _advisor_orchestrator:
                    system_prompt = "You are a playbook architect. Generate well-structured playbook definitions. Return valid JSON only."
                    
                    # Use generate_json for structured output
                    result = _advisor_orchestrator.generate_json(
                        prompt=f"{system_prompt}\n\n{prompt}"
                    )
                    
                    if result.get('success') and result.get('json'):
                        # Already parsed JSON
                        logger.info(f"[ADVISOR] Got playbook structure from {result.get('model_used', 'unknown')}")
                        return result['json']
                    elif result.get('response'):
                        # Raw response, try to parse
                        response_text = result['response']
                        logger.info(f"[ADVISOR] Got playbook text from {result.get('model_used', 'unknown')}")
                else:
                    logger.warning("[ADVISOR] LLMOrchestrator not available for playbook gen")
                
            except Exception as claude_error:
                logger.warning(f"[ADVISOR] LLM failed for playbook gen: {claude_error}")
        
        # Parse JSON from response
        if response_text:
            # Clean up response - remove markdown if present
            response_text = response_text.strip()
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            response_text = response_text.strip()
            
            try:
                playbook = json.loads(response_text)
                return playbook
            except json.JSONDecodeError as e:
                logger.error(f"[ADVISOR] Failed to parse playbook JSON: {e}")
        
        # Fallback: Generate a basic structure based on keywords
        return _generate_fallback_playbook(description)
        
    except Exception as e:
        logger.error(f"[ADVISOR] Playbook generation error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return _generate_fallback_playbook(request.description)


def _generate_fallback_playbook(description: str) -> Dict:
    """Generate a basic playbook structure when AI is unavailable."""
    desc_lower = description.lower()
    
    # Detect common patterns
    is_comparison = any(w in desc_lower for w in ['compare', 'reconcile', 'variance', 'difference', 'match'])
    is_irs = any(w in desc_lower for w in ['irs', 'w-2', 'w2', '941', 'tax'])
    is_gl = any(w in desc_lower for w in ['gl', 'general ledger', 'account', 'mapping'])
    has_multiple_files = any(w in desc_lower for w in ['files', 'both', 'two', '2 '])
    
    # IRS/Tax comparison
    if is_irs and (is_comparison or has_multiple_files):
        return {
            "name": "IRS Reconciliation Analysis",
            "description": "Compare IRS tax files against customer payroll data to identify and categorize variances.",
            "inputs": [
                {"name": "IRS Tax File(s)", "type": "file", "description": "941, W-2 totals, or other IRS reports"},
                {"name": "Customer Payroll Data", "type": "file", "description": "Pay register, YTD totals, or employee data"}
            ],
            "steps": [
                {"title": "Profile & Validate Files", "description": "AI examines each uploaded file to understand structure, identify key columns, and flag data quality issues.", "ai_assisted": True},
                {"title": "Identify Join Keys", "description": "Find common fields between IRS and customer data (EIN, SSN, Employee ID). Validate keys exist in both sources.", "ai_assisted": True},
                {"title": "Map Comparison Fields", "description": "Match IRS fields to customer equivalents (e.g., Box 1 Wages → Gross Pay YTD). Define tolerance thresholds.", "ai_assisted": True},
                {"title": "Execute Comparison", "description": "Run matching analysis between datasets. Calculate variances and flag discrepancies by severity.", "ai_assisted": True},
                {"title": "Categorize Findings", "description": "Group variances into: Expected differences (timing, rounding), Errors requiring correction, Items needing investigation.", "ai_assisted": True},
                {"title": "Review & Approve", "description": "Human review of AI findings. Approve categorizations and add notes for customer discussion.", "ai_assisted": False},
                {"title": "Generate Deliverables", "description": "Create final reports: Executive summary, variance detail by category, and recommended actions.", "ai_assisted": True}
            ],
            "outputs": [
                {"name": "IRS Reconciliation Report", "format": "spreadsheet", "description": "Detailed variance analysis with all records compared"},
                {"name": "Executive Summary", "format": "report", "description": "High-level findings and recommendations for customer"},
                {"name": "Action Items Checklist", "format": "data", "description": "List of items requiring correction or follow-up"}
            ]
        }
    
    # GL Mapping
    elif is_gl:
        return {
            "name": "GL Configuration Mapping",
            "description": "Map legacy general ledger structure to new system configuration rules.",
            "inputs": [
                {"name": "Legacy GL Structure", "type": "file", "description": "Current chart of accounts or GL configuration"},
                {"name": "Target GL Template", "type": "file", "description": "New system GL structure or mapping template"}
            ],
            "steps": [
                {"title": "Profile GL Structures", "description": "Analyze both source and target GL configurations to understand segments, hierarchies, and rules.", "ai_assisted": True},
                {"title": "Auto-Map Common Accounts", "description": "AI identifies obvious mappings based on account names, numbers, and patterns.", "ai_assisted": True},
                {"title": "Flag Ambiguous Mappings", "description": "Highlight accounts that need human decision - multiple possible targets or no clear match.", "ai_assisted": True},
                {"title": "Human Resolution", "description": "Review and resolve flagged mappings. Make decisions on ambiguous accounts.", "ai_assisted": False},
                {"title": "Validate Mapping Rules", "description": "Check mapping completeness - ensure all source accounts have targets and no orphans exist.", "ai_assisted": True},
                {"title": "Generate Configuration", "description": "Create import-ready configuration files for the new system.", "ai_assisted": True}
            ],
            "outputs": [
                {"name": "GL Mapping Document", "format": "spreadsheet", "description": "Complete source-to-target mapping with all accounts"},
                {"name": "Configuration Import File", "format": "data", "description": "Ready-to-load file for new system"},
                {"name": "Mapping Exceptions Report", "format": "report", "description": "Documentation of decisions made on ambiguous mappings"}
            ]
        }
    
    # Generic comparison
    elif is_comparison or has_multiple_files:
        return {
            "name": "Data Comparison Analysis",
            "description": "Compare two datasets to identify matches, variances, and discrepancies.",
            "inputs": [
                {"name": "Source File 1", "type": "file", "description": "First dataset for comparison"},
                {"name": "Source File 2", "type": "file", "description": "Second dataset for comparison"}
            ],
            "steps": [
                {"title": "Profile Both Files", "description": "Analyze structure, columns, data types, and row counts for each file.", "ai_assisted": True},
                {"title": "Identify Join Keys", "description": "Determine which fields can be used to match records between files.", "ai_assisted": True},
                {"title": "Execute Comparison", "description": "Match records and calculate differences for comparable fields.", "ai_assisted": True},
                {"title": "Categorize Results", "description": "Group findings: Exact matches, Within tolerance, Significant variances, Orphan records.", "ai_assisted": True},
                {"title": "Review Findings", "description": "Human review of significant variances and orphan records.", "ai_assisted": False},
                {"title": "Generate Report", "description": "Create comparison summary and detailed variance report.", "ai_assisted": True}
            ],
            "outputs": [
                {"name": "Comparison Summary", "format": "report", "description": "Executive summary of comparison results"},
                {"name": "Variance Detail", "format": "spreadsheet", "description": "All records with variance details"}
            ]
        }
    
    # Generic analysis
    else:
        return {
            "name": "Data Analysis Playbook",
            "description": "Structured analysis of uploaded data with findings and recommendations.",
            "inputs": [
                {"name": "Source Data", "type": "file", "description": "Data file(s) to analyze"}
            ],
            "steps": [
                {"title": "Profile Data", "description": "Analyze file structure, data quality, and key statistics.", "ai_assisted": True},
                {"title": "Identify Patterns", "description": "Find trends, anomalies, and notable patterns in the data.", "ai_assisted": True},
                {"title": "Generate Insights", "description": "Create findings and recommendations based on analysis.", "ai_assisted": True},
                {"title": "Review & Refine", "description": "Human review of AI findings. Add context and refine recommendations.", "ai_assisted": False},
                {"title": "Create Deliverable", "description": "Generate final analysis report.", "ai_assisted": True}
            ],
            "outputs": [
                {"name": "Analysis Report", "format": "report", "description": "Complete analysis with findings and recommendations"}
            ]
        }
