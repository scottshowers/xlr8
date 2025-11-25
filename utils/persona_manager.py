"""
Persona Management System - Meet Bessie!
=========================================

Manages AI personas with different personalities, expertise, and styles.
Users can switch personas or create custom ones.

Author: XLR8 Team
"""

from typing import Dict, List, Optional
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Persona:
    """AI Persona with personality and expertise"""
    
    def __init__(
        self,
        name: str,
        icon: str,
        description: str,
        system_prompt: str,
        expertise: List[str],
        tone: str,
        custom: bool = False
    ):
        self.name = name
        self.icon = icon  # emoji or icon name
        self.description = description
        self.system_prompt = system_prompt
        self.expertise = expertise
        self.tone = tone
        self.custom = custom
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self):
        return {
            'name': self.name,
            'icon': self.icon,
            'description': self.description,
            'system_prompt': self.system_prompt,
            'expertise': self.expertise,
            'tone': self.tone,
            'custom': self.custom,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**{k: v for k, v in data.items() if k != 'created_at'})


class PersonaManager:
    """Manages all available personas"""
    
    def __init__(self, personas_file: str = "/data/personas.json"):
        self.personas_file = personas_file
        self.personas = {}
        self._load_default_personas()
        self._load_builtin_overrides()  # Load any edited built-in personas
        self._load_custom_personas()
    
    def _load_default_personas(self):
        """Load built-in personas"""
        
        # BESSIE - The UKG Payroll Expert
        bessie = Persona(
            name="Bessie",
            icon="🐮",  # Cow emoji - friendly, reliable, hardworking
            description="Your friendly UKG payroll expert. Bessie knows everything about earnings, deductions, and getting payroll right!",
            system_prompt="""You are Bessie, a friendly and knowledgeable UKG payroll expert with years of experience. 

Your personality:
- Warm and approachable, like a trusted colleague
- Patient and thorough - you never rush through explanations
- Practical and detail-oriented - accuracy matters in payroll!
- Encouraging and supportive - payroll can be complex, you're here to help
- You occasionally use farm/cow puns when appropriate (but not overdone)

Your expertise:
- UKG Pro/WFM configuration and best practices
- Earnings codes, deduction codes, benefit plans
- Payroll processing, tax setup, GL mapping
- Time and attendance, accruals, PTO
- Compliance and regulatory requirements

Your style:
- Start with a friendly greeting
- Break down complex topics into digestible pieces
- Use examples and analogies
- Highlight important details or gotchas
- End with "anything else I can help you wrangle?" or similar friendly closing

Remember: You're not just answering questions, you're helping people succeed with their payroll!""",
            expertise=["UKG Pro", "Payroll", "Configuration", "Time & Attendance", "Compliance"],
            tone="Friendly, Professional, Supportive"
        )
        
        # ANALYST - The Data Detective
        analyst = Persona(
            name="Analyst",
            icon="🔍",
            description="Data-driven and analytical. Perfect for deep dives, comparisons, and finding patterns.",
            system_prompt="""You are a data analyst focused on uncovering insights and patterns.

Your approach:
- Start with the data, always cite your sources
- Look for trends, anomalies, and patterns
- Compare and contrast different options
- Quantify everything when possible
- Highlight key metrics and KPIs

Your style:
- Structured and methodical
- Use bullet points and tables
- Show your reasoning process
- Data first, opinions second
- Professional and objective""",
            expertise=["Data Analysis", "Reporting", "Metrics", "Trends", "Comparisons"],
            tone="Analytical, Objective, Data-Driven"
        )
        
        # CONSULTANT - The Strategic Advisor
        consultant = Persona(
            name="Consultant",
            icon="💼",
            description="Strategic and advisory. Focuses on best practices, recommendations, and long-term thinking.",
            system_prompt="""You are an experienced consultant providing strategic guidance.

Your approach:
- Consider business context and goals
- Provide pros/cons for different approaches
- Think about scalability and future state
- Reference industry best practices
- Consider risks and mitigation strategies

Your style:
- Strategic and forward-thinking
- Provide clear recommendations
- Acknowledge trade-offs
- Professional and polished
- Executive-friendly summaries""",
            expertise=["Strategy", "Best Practices", "Change Management", "Risk Assessment", "Planning"],
            tone="Strategic, Advisory, Professional"
        )
        
        # TRAINER - The Educator
        trainer = Persona(
            name="Trainer",
            icon="👩‍🏫",
            description="Patient educator. Great for learning new concepts and step-by-step guidance.",
            system_prompt="""You are a patient trainer helping people learn and understand.

Your approach:
- Break complex topics into simple steps
- Use clear examples and analogies
- Check for understanding along the way
- Encourage questions
- Build confidence through learning

Your style:
- Clear and simple language
- Step-by-step instructions
- Visual descriptions when helpful
- Positive and encouraging
- "Let's learn together" attitude""",
            expertise=["Training", "Documentation", "Onboarding", "Tutorials", "Education"],
            tone="Patient, Clear, Encouraging"
        )
        
        # QUICK - The Efficient Assistant
        quick = Persona(
            name="Quick",
            icon="⚡",
            description="Fast and to-the-point. No fluff, just answers.",
            system_prompt="""You are a quick and efficient assistant. Get to the point fast.

Your approach:
- Answer directly, no preamble
- Bullet points over paragraphs
- Key facts only
- Skip the explanations unless asked
- Move fast

Your style:
- Concise and direct
- Minimal formatting
- Action-oriented
- No small talk
- Speed is the priority""",
            expertise=["Quick Answers", "Fast Lookups", "Efficiency", "Direct Response"],
            tone="Concise, Direct, Fast"
        )
        
        # Store default personas
        self.personas = {
            'bessie': bessie,
            'analyst': analyst,
            'consultant': consultant,
            'trainer': trainer,
            'quick': quick
        }
        
        logger.info(f"Loaded {len(self.personas)} default personas")
    
    def _load_custom_personas(self):
        """Load custom personas from file"""
        if not os.path.exists(self.personas_file):
            return
        
        try:
            with open(self.personas_file, 'r') as f:
                data = json.load(f)
                
            for persona_data in data.get('custom_personas', []):
                persona = Persona.from_dict(persona_data)
                persona_id = persona.name.lower().replace(' ', '_')
                self.personas[persona_id] = persona
            
            logger.info(f"Loaded {len(data.get('custom_personas', []))} custom personas")
        except Exception as e:
            logger.error(f"Error loading custom personas: {e}")
    
    def _save_custom_personas(self):
        """Save custom personas to file"""
        custom = [
            p.to_dict() 
            for p in self.personas.values() 
            if p.custom
        ]
        
        try:
            os.makedirs(os.path.dirname(self.personas_file), exist_ok=True)
            with open(self.personas_file, 'w') as f:
                json.dump({'custom_personas': custom}, f, indent=2)
            logger.info(f"Saved {len(custom)} custom personas")
        except Exception as e:
            logger.error(f"Error saving custom personas: {e}")
    
    def _save_builtin_overrides(self):
        """Save edited built-in personas as overrides"""
        overrides_file = self.personas_file.replace('personas.json', 'persona_overrides.json')
        builtin_ids = ['bessie', 'analyst', 'consultant', 'trainer', 'quick']
        
        overrides = {}
        for pid in builtin_ids:
            if pid in self.personas:
                # Save full persona data as override
                overrides[pid] = self.personas[pid].to_dict()
        
        try:
            os.makedirs(os.path.dirname(overrides_file), exist_ok=True)
            with open(overrides_file, 'w') as f:
                json.dump({'overrides': overrides}, f, indent=2)
            logger.info(f"Saved {len(overrides)} persona overrides")
        except Exception as e:
            logger.error(f"Error saving persona overrides: {e}")
    
    def _load_builtin_overrides(self):
        """Load edited built-in personas from overrides file"""
        overrides_file = self.personas_file.replace('personas.json', 'persona_overrides.json')
        
        if not os.path.exists(overrides_file):
            return
        
        try:
            with open(overrides_file, 'r') as f:
                data = json.load(f)
            
            for pid, persona_data in data.get('overrides', {}).items():
                if pid in self.personas:
                    # Update existing persona with override data
                    persona = Persona.from_dict(persona_data)
                    self.personas[pid] = persona
                    logger.info(f"Applied override for persona: {pid}")
            
            logger.info(f"Loaded {len(data.get('overrides', {}))} persona overrides")
        except Exception as e:
            logger.error(f"Error loading persona overrides: {e}")
    
    def get_persona(self, name: str = 'bessie') -> Persona:
        """Get persona by name"""
        persona_id = name.lower().replace(' ', '_')
        return self.personas.get(persona_id, self.personas['bessie'])
    
    def list_personas(self) -> List[Dict]:
        """List all available personas"""
        return [
            {
                'id': pid,
                'name': p.name,
                'icon': p.icon,
                'description': p.description,
                'expertise': p.expertise,
                'tone': p.tone,
                'custom': p.custom
            }
            for pid, p in self.personas.items()
        ]
    
    def create_persona(
        self,
        name: str,
        icon: str,
        description: str,
        system_prompt: str,
        expertise: List[str],
        tone: str
    ) -> Persona:
        """Create a new custom persona"""
        persona = Persona(
            name=name,
            icon=icon,
            description=description,
            system_prompt=system_prompt,
            expertise=expertise,
            tone=tone,
            custom=True
        )
        
        persona_id = name.lower().replace(' ', '_')
        self.personas[persona_id] = persona
        self._save_custom_personas()
        
        logger.info(f"Created custom persona: {name}")
        return persona
    
    def delete_persona(self, name: str) -> bool:
        """Delete a custom persona"""
        persona_id = name.lower().replace(' ', '_')
        
        if persona_id not in self.personas:
            return False
        
        if not self.personas[persona_id].custom:
            logger.warning(f"Cannot delete default persona: {name}")
            return False
        
        del self.personas[persona_id]
        self._save_custom_personas()
        
        logger.info(f"Deleted custom persona: {name}")
        return True
    
    def update_persona(self, name: str, **updates) -> Optional[Persona]:
        """Update any persona (built-in or custom)"""
        persona_id = name.lower().replace(' ', '_')
        
        if persona_id not in self.personas:
            return None
        
        persona = self.personas[persona_id]
        
        # Allow updating all personas (built-in and custom)
        # Built-in persona edits are saved as overrides
        
        # Update fields
        for key, value in updates.items():
            if hasattr(persona, key):
                setattr(persona, key, value)
        
        # Save changes (custom personas to personas.json, built-in overrides to persona_overrides.json)
        self._save_custom_personas()
        self._save_builtin_overrides()
        logger.info(f"Updated persona: {name}")
        
        return persona


# Global persona manager instance
_persona_manager = None

def get_persona_manager() -> PersonaManager:
    """Get or create persona manager singleton"""
    global _persona_manager
    if _persona_manager is None:
        _persona_manager = PersonaManager()
    return _persona_manager
