"""
AI Analysis Module
Uses ACTUAL LLM (Ollama) with RAG for document analysis
"""

import streamlit as st
from typing import Dict, Any
import requests
from requests.auth import HTTPBasicAuth


def analyze_document(parsed_data: Dict[str, Any], depth: str) -> Dict[str, Any]:
    """
    Run ACTUAL AI analysis on parsed document using Ollama + RAG
    
    Args:
        parsed_data: Parsed document data with text and tables
        depth: Analysis depth ("Quick Overview", "Standard Analysis", "Deep Analysis")
    
    Returns:
        Dictionary with analysis results
    """
    
    # Get LLM config from session state or config
    llm_endpoint = st.session_state.get('llm_endpoint', 'http://localhost:11435')
    llm_model = st.session_state.get('llm_model', 'llama3.2:latest')
    llm_username = st.session_state.get('llm_username', 'xlr8')
    llm_password = st.session_state.get('llm_password', 'Argyle76226#')
    
    # Extract text from parsed data
    text = parsed_data.get('text', '')
    
    if not text:
        return {
            "success": False,
            "message": "No text content to analyze",
            "findings": [],
            "recommendations": []
        }
    
    # Build prompt based on depth
    prompt = _build_analysis_prompt(text, depth)
    
    # Get RAG context if available
    rag_context = _get_rag_context(text)
    if rag_context:
        prompt = f"HCMPACT Knowledge Base Context:\n{rag_context}\n\n{prompt}"
    
    # Call LLM
    try:
        analysis_result = _call_llm(
            prompt=prompt,
            endpoint=llm_endpoint,
            model=llm_model,
            username=llm_username,
            password=llm_password
        )
        
        if analysis_result:
            return {
                "success": True,
                "analysis": analysis_result,
                "depth": depth,
                "findings": _extract_findings(analysis_result),
                "recommendations": _extract_recommendations(analysis_result),
                "raw_response": analysis_result
            }
        else:
            return {
                "success": False,
                "message": "LLM returned no response",
                "findings": [],
                "recommendations": []
            }
            
    except Exception as e:
        st.error(f"Analysis error: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "findings": [],
            "recommendations": []
        }


def _build_analysis_prompt(text: str, depth: str) -> str:
    """Build analysis prompt based on depth"""
    
    base_prompt = f"""Analyze this customer document for UKG implementation:

DOCUMENT CONTENT:
{text[:2000]}  # Limit for token efficiency

"""
    
    if depth == "Quick Overview":
        return base_prompt + """
Provide a BRIEF analysis:
1. Document type and purpose
2. Key data elements found
3. Potential UKG modules affected
4. Major data quality issues (if any)
"""
    
    elif depth == "Deep Analysis":
        return base_prompt + """
Provide a COMPREHENSIVE analysis:
1. Document structure and completeness
2. All data elements mapped to UKG fields
3. Data quality assessment per field
4. Transformation rules needed
5. Integration requirements
6. Implementation risks and recommendations
7. Step-by-step migration plan
"""
    
    else:  # Standard Analysis
        return base_prompt + """
Analyze this document for UKG implementation:
1. Document type and data structure
2. Key fields and their UKG mappings
3. Data quality observations
4. Recommended transformations
5. Implementation considerations
"""


def _get_rag_context(text: str, n_results: int = 3) -> str:
    """Get relevant context from RAG knowledge base"""
    
    if 'rag_handler' not in st.session_state:
        return ""
    
    try:
        rag = st.session_state.rag_handler
        
        # Search for relevant knowledge
        results = rag.search(text[:200], n_results=n_results)
        
        if results:
            context = "\n\n".join([
                f"[{r['metadata'].get('doc_name', 'Unknown')}]: {r['content']}"
                for r in results
            ])
            return context
        
    except Exception as e:
        st.warning(f"RAG search failed: {str(e)}")
    
    return ""


def _call_llm(prompt: str, endpoint: str, model: str, username: str, password: str) -> str:
    """Call Ollama LLM API"""
    
    try:
        url = f"{endpoint}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        auth = HTTPBasicAuth(username, password)
        
        response = requests.post(url, json=payload, auth=auth, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        return result.get('response', '')
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"LLM API error: {str(e)}")


def _extract_findings(analysis_text: str) -> list:
    """Extract key findings from analysis"""
    # Simple extraction - look for numbered or bulleted items
    findings = []
    for line in analysis_text.split('\n'):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
            findings.append(line.lstrip('0123456789.-•) '))
    
    return findings[:10]  # Top 10


def _extract_recommendations(analysis_text: str) -> list:
    """Extract recommendations from analysis"""
    # Look for recommendation-like content
    recommendations = []
    in_rec_section = False
    
    for line in analysis_text.split('\n'):
        line = line.strip()
        if 'recommend' in line.lower():
            in_rec_section = True
        if in_rec_section and line and (line[0].isdigit() or line.startswith('-')):
            recommendations.append(line.lstrip('0123456789.-•) '))
    
    return recommendations[:5]  # Top 5


# Standalone testing
if __name__ == "__main__":
    st.title("AI Analyzer - Using ACTUAL LLM")
    
    test_text = st.text_area("Test document text", height=200)
    depth = st.selectbox("Analysis depth", ["Quick Overview", "Standard Analysis", "Deep Analysis"])
    
    if st.button("Analyze") and test_text:
        with st.spinner("Running AI analysis..."):
            result = analyze_document({'text': test_text}, depth)
        
        if result.get('success'):
            st.success("✅ Analysis complete!")
            st.markdown("### Analysis Result")
            st.write(result.get('analysis'))
            
            if result.get('findings'):
                st.markdown("### Key Findings")
                for f in result['findings']:
                    st.markdown(f"- {f}")
            
            if result.get('recommendations'):
                st.markdown("### Recommendations")
                for r in result['recommendations']:
                    st.markdown(f"- {r}")
        else:
            st.error(result.get('message', 'Analysis failed'))
