"""
XLR8 LEARNING MODULE
====================

Makes the AI smarter with every interaction:
- Learns successful query patterns
- Remembers user preferences from clarifications
- Uses feedback to improve responses
- Skips unnecessary clarifications

Deploy to: backend/utils/learning.py
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class LearningModule:
    """
    Self-learning system for XLR8.
    
    Connects to Supabase to:
    - Store successful query patterns
    - Learn from user feedback
    - Remember clarification preferences
    - Skip questions when we know the answer
    """
    
    def __init__(self):
        self.supabase = None
        self._init_supabase()
    
    def _init_supabase(self):
        """Initialize Supabase connection."""
        try:
            from utils.supabase_client import get_supabase_client
            self.supabase = get_supabase_client()
            logger.info("[LEARNING] Connected to Supabase")
        except Exception as e:
            try:
                from backend.utils.supabase_client import get_supabase_client
                self.supabase = get_supabase_client()
                logger.info("[LEARNING] Connected to Supabase (alt path)")
            except Exception as e2:
                logger.warning(f"[LEARNING] Supabase not available: {e2}")
                self.supabase = None
    
    # =========================================================================
    # QUERY LEARNING
    # =========================================================================
    
    def find_similar_query(
        self, 
        question: str, 
        intent: str = None,
        domain: str = None,
        project: str = None
    ) -> Optional[Dict]:
        """
        Find a similar previously successful query.
        
        Returns the best match if found, None otherwise.
        """
        if not self.supabase:
            return None
        
        try:
            keywords = self._extract_keywords(question)
            
            result = self.supabase.rpc('find_similar_queries', {
                'p_keywords': keywords,
                'p_intent': intent,
                'p_domain': domain,
                'p_project': project,
                'p_limit': 3
            }).execute()
            
            if result.data and len(result.data) > 0:
                best_match = result.data[0]
                
                # Only use if good match score and positive feedback
                if best_match.get('match_score', 0) > 0.5 and best_match.get('avg_feedback', 0) >= 0:
                    logger.info(f"[LEARNING] Found similar query with score {best_match['match_score']:.2f}")
                    return best_match
            
            return None
            
        except Exception as e:
            logger.warning(f"[LEARNING] Error finding similar query: {e}")
            return None
    
    def record_successful_query(
        self,
        question: str,
        sql: str = None,
        response: str = None,
        intent: str = None,
        domain: str = None,
        project: str = None,
        sources: List[str] = None
    ):
        """Record a successful query pattern for future reuse."""
        if not self.supabase:
            return
        
        try:
            keywords = self._extract_keywords(question)
            
            self.supabase.rpc('record_successful_query', {
                'p_question': question,
                'p_keywords': keywords,
                'p_intent': intent or 'search',
                'p_sql': sql,
                'p_response': response[:500] if response else None,
                'p_sources': sources or [],
                'p_project': project,
                'p_domain': domain
            }).execute()
            
            logger.info(f"[LEARNING] Recorded successful query pattern")
            
        except Exception as e:
            logger.warning(f"[LEARNING] Error recording query: {e}")
    
    # =========================================================================
    # FEEDBACK LEARNING
    # =========================================================================
    
    def record_feedback(
        self,
        question: str,
        feedback: str,  # 'positive' or 'negative'
        project: str = None,
        user_id: str = None,
        job_id: str = None,
        intent: str = None,
        was_intelligent: bool = False
    ):
        """Record user feedback to improve future responses."""
        if not self.supabase:
            return
        
        try:
            keywords = self._extract_keywords(question)
            
            self.supabase.rpc('record_feedback', {
                'p_question': question,
                'p_feedback': feedback,
                'p_project': project,
                'p_user_id': user_id,
                'p_job_id': job_id,
                'p_intent': intent,
                'p_keywords': keywords,
                'p_was_intelligent': was_intelligent
            }).execute()
            
            logger.info(f"[LEARNING] Recorded {feedback} feedback")
            
        except Exception as e:
            logger.warning(f"[LEARNING] Error recording feedback: {e}")
    
    # =========================================================================
    # CLARIFICATION LEARNING
    # =========================================================================
    
    def record_clarification_choice(
        self,
        question_id: str,
        chosen_option: str,
        domain: str = None,
        intent: str = None,
        project: str = None,
        user_id: str = None
    ):
        """Record a user's clarification choice to learn preferences."""
        if not self.supabase:
            return
        
        try:
            self.supabase.rpc('record_clarification_choice', {
                'p_question_id': question_id,
                'p_chosen_option': chosen_option,
                'p_domain': domain,
                'p_intent': intent,
                'p_project': project,
                'p_user_id': user_id
            }).execute()
            
            logger.info(f"[LEARNING] Recorded clarification choice: {question_id}={chosen_option}")
            
        except Exception as e:
            logger.warning(f"[LEARNING] Error recording clarification: {e}")
    
    def get_likely_choice(
        self,
        question_id: str,
        domain: str = None,
        project: str = None,
        user_id: str = None
    ) -> Optional[Tuple[str, float]]:
        """
        Get the user's likely choice for a clarification question.
        
        Returns (chosen_option, confidence) if known, None otherwise.
        """
        if not self.supabase:
            return None
        
        try:
            result = self.supabase.rpc('get_likely_choice', {
                'p_question_id': question_id,
                'p_domain': domain,
                'p_project': project,
                'p_user_id': user_id
            }).execute()
            
            if result.data and len(result.data) > 0:
                choice = result.data[0]
                confidence = choice.get('confidence', 0)
                
                # Only return if confident enough
                if confidence >= 0.7:
                    logger.info(f"[LEARNING] Found likely choice for {question_id}: {choice['chosen_option']} ({confidence:.0%})")
                    return (choice['chosen_option'], confidence)
            
            return None
            
        except Exception as e:
            logger.warning(f"[LEARNING] Error getting likely choice: {e}")
            return None
    
    def should_skip_clarification(
        self,
        questions: List[Dict],
        domain: str = None,
        project: str = None,
        user_id: str = None
    ) -> Tuple[bool, Dict[str, str]]:
        """
        Check if we can skip clarification by using learned preferences.
        
        Returns:
            (can_skip, answers_dict)
            - can_skip: True if all questions have confident answers
            - answers_dict: The answers to use
        """
        if not self.supabase or not questions:
            return False, {}
        
        answers = {}
        all_confident = True
        
        for q in questions:
            question_id = q.get('id')
            if not question_id:
                continue
            
            likely = self.get_likely_choice(question_id, domain, project, user_id)
            
            if likely:
                answers[question_id] = likely[0]
            else:
                all_confident = False
        
        # Only skip if we have confident answers for ALL questions
        if all_confident and len(answers) == len(questions):
            logger.info(f"[LEARNING] Can skip clarification - all {len(questions)} questions have learned answers")
            return True, answers
        
        return False, answers
    
    # =========================================================================
    # USER PREFERENCES
    # =========================================================================
    
    def get_user_preference(
        self,
        user_id: str,
        preference_key: str,
        domain: str = None,
        project: str = None
    ) -> Optional[str]:
        """Get a specific user preference."""
        if not self.supabase:
            return None
        
        try:
            query = self.supabase.table('user_preferences').select('preference_value, confidence')
            query = query.eq('preference_key', preference_key)
            
            if user_id:
                query = query.eq('user_id', user_id)
            if domain:
                query = query.eq('semantic_domain', domain)
            if project:
                query = query.eq('project', project)
            
            result = query.order('confidence', desc=True).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]['preference_value']
            
            return None
            
        except Exception as e:
            logger.warning(f"[LEARNING] Error getting preference: {e}")
            return None
    
    def set_user_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_value: str,
        domain: str = None,
        project: str = None,
        learned_from: str = 'explicit'
    ):
        """Set a user preference."""
        if not self.supabase:
            return
        
        try:
            self.supabase.table('user_preferences').upsert({
                'user_id': user_id,
                'preference_key': preference_key,
                'preference_value': preference_value,
                'semantic_domain': domain,
                'project': project,
                'learned_from': learned_from,
                'updated_at': datetime.now().isoformat()
            }).execute()
            
            logger.info(f"[LEARNING] Set preference {preference_key}={preference_value}")
            
        except Exception as e:
            logger.warning(f"[LEARNING] Error setting preference: {e}")
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        if not text:
            return []
        
        # Lowercase and clean
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split into words
        words = text.split()
        
        # Remove stop words
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall',
            'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she', 'it',
            'they', 'them', 'their', 'this', 'that', 'these', 'those',
            'what', 'which', 'who', 'whom', 'where', 'when', 'why', 'how',
            'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'not', 'only', 'same', 'so', 'than', 'too',
            'very', 'just', 'can', 'also', 'any', 'and', 'or', 'but', 'if',
            'for', 'from', 'to', 'of', 'in', 'on', 'at', 'by', 'with',
            'show', 'give', 'get', 'find', 'list', 'display', 'tell', 'help',
            'please', 'want', 'need', 'like', 'know'
        }
        
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique.append(k)
        
        return unique[:10]  # Max 10 keywords
    
    def get_learning_stats(self) -> Dict:
        """Get statistics about what the system has learned."""
        if not self.supabase:
            return {'available': False}
        
        try:
            # Count learned queries
            queries_result = self.supabase.table('learned_queries').select('id', count='exact').execute()
            
            # Count feedback
            feedback_result = self.supabase.table('query_feedback').select('id', count='exact').execute()
            
            # Count preferences
            prefs_result = self.supabase.table('user_preferences').select('id', count='exact').execute()
            
            # Count clarification patterns
            clarif_result = self.supabase.table('clarification_patterns').select('id', count='exact').execute()
            
            return {
                'available': True,
                'learned_queries': queries_result.count or 0,
                'feedback_records': feedback_result.count or 0,
                'user_preferences': prefs_result.count or 0,
                'clarification_patterns': clarif_result.count or 0,
            }
            
        except Exception as e:
            logger.warning(f"[LEARNING] Error getting stats: {e}")
            return {'available': True, 'error': str(e)}


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_learning_module = None

def get_learning_module() -> LearningModule:
    """Get the singleton learning module instance."""
    global _learning_module
    if _learning_module is None:
        _learning_module = LearningModule()
    return _learning_module
