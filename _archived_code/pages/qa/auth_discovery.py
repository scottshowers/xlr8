"""
Ollama Auth Discovery - Streamlit Page
Run this from the browser to discover authentication method
"""

import streamlit as st
import requests
import json
import os

st.title("🔍 Ollama Authentication Discovery")

st.markdown("""
This tool will test your Ollama server to discover what authentication method it uses.
Click the button below to run all tests.
""")

OLLAMA_URL = "http://178.156.190.64:11435"

if st.button("🚀 Run Authentication Tests", type="primary"):
    
    results = []
    
    # Test 1: No auth
    st.subheader("Test 1: No Authentication")
    with st.spinner("Testing..."):
        try:
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                st.success(f"✅ No auth needed! Status: {response.status_code}")
                st.info("Your Ollama server doesn't require authentication")
                st.stop()
            elif response.status_code == 401:
                st.error(f"❌ Auth required (401)")
                results.append(("No Auth", "401 - Auth Required"))
            else:
                st.warning(f"⚠️ Unexpected status: {response.status_code}")
                results.append(("No Auth", f"Status: {response.status_code}"))
        except Exception as e:
            st.error(f"❌ Error: {e}")
            results.append(("No Auth", f"Error: {e}"))
    
    # Test 2: Check environment variables
    st.markdown("---")
    st.subheader("Test 2: Environment Variables")
    
    possible_vars = [
        'OLLAMA_TOKEN',
        'OLLAMA_API_KEY',
        'OLLAMA_AUTH_TOKEN',
        'OLLAMA_AUTH',
        'API_TOKEN',
        'AUTH_TOKEN',
        'BEARER_TOKEN',
        'HETZNER_TOKEN',
        'HETZNER_API_KEY',
    ]
    
    found_vars = []
    for var in possible_vars:
        value = os.environ.get(var)
        if value:
            # Show last 4 chars only for security
            st.success(f"✅ Found: **{var}** = ***...{value[-4:]}")
            found_vars.append((var, value))
        else:
            st.caption(f"❌ {var} - not set")
    
    if not found_vars:
        st.warning("No relevant environment variables found")
        st.info("""
        **What this means:** Either:
        1. Auth token not set in Railway Variables
        2. Auth is configured differently
        3. Need to check your rag_handler.py code
        """)
    
    # Test 3: Try found tokens
    if found_vars:
        st.markdown("---")
        st.subheader("Test 3: Testing Found Tokens")
        
        for var_name, token in found_vars:
            st.markdown(f"**Testing {var_name}...**")
            
            # Try Bearer
            try:
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get(f"{OLLAMA_URL}/api/tags", headers=headers, timeout=5)
                
                if response.status_code == 200:
                    st.success(f"🎉 **SUCCESS!** Bearer token from `{var_name}` works!")
                    
                    st.markdown("---")
                    st.subheader("✅ SOLUTION FOUND")
                    
                    st.code(f"""
# Add to Railway Variables:
OLLAMA_AUTH_TOKEN = [copy value from {var_name}]

# Or if {var_name} is different:
# 1. Copy the value of {var_name}
# 2. Create new variable: OLLAMA_AUTH_TOKEN = that value
# 3. Redeploy
""")
                    
                    st.info(f"""
                    **Next Steps:**
                    1. Go to Railway → Variables
                    2. Add: `OLLAMA_AUTH_TOKEN` = value from `{var_name}`
                    3. Deploy updated enhanced_llm_synthesizer.py
                    4. Test analysis!
                    """)
                    st.stop()
                else:
                    st.caption(f"Bearer: {response.status_code}")
            except Exception as e:
                st.caption(f"Bearer: Error - {str(e)[:50]}")
            
            # Try X-API-Key
            try:
                headers = {"X-API-Key": token}
                response = requests.get(f"{OLLAMA_URL}/api/tags", headers=headers, timeout=5)
                
                if response.status_code == 200:
                    st.success(f"🎉 **SUCCESS!** X-API-Key from `{var_name}` works!")
                    
                    st.markdown("---")
                    st.subheader("✅ SOLUTION FOUND")
                    
                    st.code(f"""
# Add to Railway Variables:
OLLAMA_AUTH_TOKEN = [copy value from {var_name}]
OLLAMA_AUTH_HEADER = X-API-Key
""")
                    
                    st.info(f"""
                    **Next Steps:**
                    1. Go to Railway → Variables
                    2. Add: `OLLAMA_AUTH_TOKEN` = value from `{var_name}`
                    3. Add: `OLLAMA_AUTH_HEADER` = `X-API-Key`
                    4. Deploy updated enhanced_llm_synthesizer.py
                    5. Test analysis!
                    """)
                    st.stop()
                else:
                    st.caption(f"X-API-Key: {response.status_code}")
            except Exception as e:
                st.caption(f"X-API-Key: Error - {str(e)[:50]}")
    
    # No solution found
    st.markdown("---")
    st.error("❌ Could not determine authentication method automatically")
    
    st.markdown("""
    ### 🔍 Manual Investigation Needed
    
    **Next Steps:**
    
    1. **Check your `rag_handler.py` file:**
       - Look for how it calls Ollama
       - Search for "Authorization" or "Bearer"
       - Check if there's auth code
    
    2. **Check Railway Variables:**
       - Go to Railway → Variables tab
       - Look for ANY variable with auth/token/key
       - Screenshot and share with Claude
    
    3. **Contact Ollama Server Admin:**
       - Ask how authentication is configured
       - Get the correct auth method and token
    
    4. **Check if RAG uses different endpoint:**
       - Maybe RAG uses port 11434 (no auth)?
       - Enhanced synthesizer uses 11435 (auth)?
    """)

else:
    st.info("Click the button above to start testing")
    
    st.markdown("---")
    st.markdown("### What This Tool Does")
    st.markdown("""
    1. Tests if Ollama server requires authentication
    2. Checks Railway environment variables for tokens
    3. Tries different authentication methods
    4. Tells you exactly what to configure
    """)
