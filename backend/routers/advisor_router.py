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

router = APIRouter(prefix="/api/advisor", tags=["advisor"])


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
        
        # Try Claude if Ollama failed
        if not response_text:
            try:
                import anthropic
                import os
                
                client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
                
                claude_messages = [{"role": m['role'], "content": m['content']} for m in messages]
                
                claude_response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=500,
                    system=full_system,
                    messages=claude_messages
                )
                
                response_text = claude_response.content[0].text
                logger.info("[ADVISOR] Got response from Claude")
                
            except Exception as claude_error:
                logger.warning(f"[ADVISOR] Claude failed: {claude_error}")
        
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
