"""System Settings Page"""
import streamlit as st
import requests
import os

def render_settings_page():
    st.markdown("## ⚙️ System Settings")
    
    # Tabs for different settings
    tab1, tab2 = st.tabs(["🔧 General", "🔍 Diagnostics"])
    
    with tab1:
        st.info("🚧 General system settings - under development")
    
    with tab2:
        render_ollama_diagnostics()


def render_ollama_diagnostics():
    """Ollama authentication diagnostics."""
    
    st.subheader("🔍 Ollama Diagnostics")
    
    st.markdown("""
    Test Ollama server connection and discover available models.
    """)
    
    OLLAMA_URL = "http://178.156.190.64:11435"
    
    st.info(f"**Testing:** {OLLAMA_URL}")
    
    if st.button("🚀 Check Ollama Server", type="primary"):
        
        # Test 1: Check available models
        st.markdown("### Test 1: Available Models")
        with st.spinner("Fetching models..."):
            try:
                from requests.auth import HTTPBasicAuth
                
                response = requests.get(
                    f"{OLLAMA_URL}/api/tags",
                    auth=HTTPBasicAuth("xlr8", "Argyle76226#"),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get('models', [])
                    
                    if models:
                        st.success(f"✅ Found {len(models)} model(s)")
                        
                        st.markdown("**Available Models:**")
                        for model in models:
                            model_name = model.get('name', 'Unknown')
                            model_size = model.get('size', 0)
                            size_gb = model_size / (1024**3) if model_size else 0
                            
                            st.code(f"{model_name}  ({size_gb:.1f} GB)")
                        
                        # Show recommendation
                        st.markdown("---")
                        st.markdown("### 🎯 Recommendation")
                        
                        # Look for llama models
                        llama_models = [m['name'] for m in models if 'llama' in m['name'].lower()]
                        
                        if llama_models:
                            recommended = llama_models[0]
                            st.success(f"**Use this model:** `{recommended}`")
                            
                            st.code(f"""# Update enhanced_llm_synthesizer.py line 88:
self.model = "{recommended}"

# Or add to Railway Variables:
LLM_MODEL = {recommended}
""", language="python")
                        else:
                            st.warning("No Llama models found. Using first available model:")
                            if models:
                                st.code(f"Use: {models[0]['name']}")
                    else:
                        st.warning("No models found on server")
                elif response.status_code == 401:
                    st.error("❌ Authentication failed")
                else:
                    st.error(f"❌ Server returned: {response.status_code}")
                    
            except Exception as e:
                st.error(f"❌ Error: {e}")
        
        # Test 2: Test model generation
        st.markdown("---")
        st.markdown("### Test 2: Test Text Generation")
        
        test_model = st.text_input("Enter model name to test:", "llama3.2")
        
        if st.button("Test This Model"):
            with st.spinner(f"Testing {test_model}..."):
                try:
                    from requests.auth import HTTPBasicAuth
                    
                    payload = {
                        "model": test_model,
                        "prompt": "Say 'Hello, I am working!' and nothing else.",
                        "stream": False,
                        "options": {"num_predict": 20}
                    }
                    
                    response = requests.post(
                        f"{OLLAMA_URL}/api/generate",
                        json=payload,
                        auth=HTTPBasicAuth("xlr8", "Argyle76226#"),
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        answer = result.get('response', '')
                        st.success(f"✅ Model works!")
                        st.code(answer)
                    elif response.status_code == 404:
                        st.error(f"❌ Model '{test_model}' not found")
                        st.info("Try one of the models listed above")
                    else:
                        st.error(f"❌ Error: {response.status_code}")
                        st.code(response.text)
                        
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        
        # Test 1: No auth
        st.markdown("### Test 1: No Authentication")
        with st.spinner("Testing..."):
            try:
                response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
                if response.status_code == 200:
                    st.success(f"✅ No auth needed! Status: {response.status_code}")
                    st.info("Your Ollama server doesn't require authentication")
                    return
                elif response.status_code == 401:
                    st.error(f"❌ Auth required (401 Authorization Required)")
                else:
                    st.warning(f"⚠️ Unexpected status: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Connection error: {e}")
        
        # Test 2: Check environment variables
        st.markdown("---")
        st.markdown("### Test 2: Environment Variables")
        
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
                st.success(f"✅ Found: **{var}** = `***...{value[-4:]}`")
                found_vars.append((var, value))
            else:
                st.caption(f"❌ {var} - not set")
        
        if not found_vars:
            st.warning("⚠️ No relevant environment variables found")
            st.markdown("""
            **This means:**
            - Auth token not set in Railway Variables
            - Need to add `OLLAMA_AUTH_TOKEN` to Railway
            - Or check your rag_handler.py for hardcoded auth
            """)
        else:
            st.info(f"Found {len(found_vars)} potential auth token(s)")
        
        # Test 3: Try found tokens
        if found_vars:
            st.markdown("---")
            st.markdown("### Test 3: Testing Found Tokens")
            
            solution_found = False
            
            for var_name, token in found_vars:
                st.markdown(f"**Testing `{var_name}`...**")
                
                col1, col2 = st.columns(2)
                
                # Try Bearer token
                with col1:
                    st.markdown("*Bearer Token*")
                    try:
                        headers = {"Authorization": f"Bearer {token}"}
                        response = requests.get(f"{OLLAMA_URL}/api/tags", headers=headers, timeout=5)
                        
                        if response.status_code == 200:
                            st.success(f"✅ SUCCESS!")
                            solution_found = True
                            
                            st.markdown("---")
                            st.markdown("### 🎉 SOLUTION FOUND")
                            
                            st.success(f"""
**Auth Method:** Bearer Token  
**Source Variable:** `{var_name}`
""")
                            
                            st.code(f"""# Add to Railway Variables:
OLLAMA_AUTH_TOKEN = [copy value from {var_name}]

# Then redeploy enhanced_llm_synthesizer.py
""", language="bash")
                            
                            st.info("""
**Next Steps:**
1. Go to Railway → Variables tab
2. Click "+ New Variable"
3. Name: `OLLAMA_AUTH_TOKEN`
4. Value: Copy from `{var_name}` above
5. Click "Add"
6. Redeploy
7. Test analysis again!
""".format(var_name=var_name))
                            
                            break
                        else:
                            st.caption(f"Status: {response.status_code}")
                    except Exception as e:
                        st.caption(f"Error: {str(e)[:30]}...")
                
                # Try X-API-Key
                with col2:
                    st.markdown("*X-API-Key*")
                    try:
                        headers = {"X-API-Key": token}
                        response = requests.get(f"{OLLAMA_URL}/api/tags", headers=headers, timeout=5)
                        
                        if response.status_code == 200:
                            st.success(f"✅ SUCCESS!")
                            solution_found = True
                            
                            st.markdown("---")
                            st.markdown("### 🎉 SOLUTION FOUND")
                            
                            st.success(f"""
**Auth Method:** X-API-Key Header  
**Source Variable:** `{var_name}`
""")
                            
                            st.code(f"""# Add to Railway Variables:
OLLAMA_AUTH_TOKEN = [copy value from {var_name}]
OLLAMA_AUTH_HEADER = X-API-Key

# Then redeploy enhanced_llm_synthesizer.py
""", language="bash")
                            
                            st.info("""
**Next Steps:**
1. Railway → Variables tab
2. Add: `OLLAMA_AUTH_TOKEN` = value from above
3. Add: `OLLAMA_AUTH_HEADER` = `X-API-Key`
4. Redeploy
5. Test analysis!
""")
                            
                            break
                        else:
                            st.caption(f"Status: {response.status_code}")
                    except Exception as e:
                        st.caption(f"Error: {str(e)[:30]}...")
                
                if solution_found:
                    break
            
            # No solution found
            if not solution_found:
                st.markdown("---")
                st.error("❌ Could not determine authentication automatically")
                
                st.markdown("""
### 🔍 Manual Investigation Required

**Option 1: Check rag_handler.py**
- Look for how it authenticates to Ollama
- Search for "Authorization" or "Bearer"
- Copy the same auth method

**Option 2: Contact Server Admin**
- Ask whoever set up the Ollama server
- Get the correct auth token

**Option 3: Share with Claude**
- Screenshot Railway Variables tab
- Share your rag_handler.py code
- Claude will help diagnose
""")
        else:
            st.markdown("---")
            st.warning("No tokens found to test. Need to add auth token to Railway Variables.")
