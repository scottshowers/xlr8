"""
Sidebar Component - Professional & Polished
Beautiful visual hierarchy, polished displays, professional typography
Version: 3.0
"""

import streamlit as st


def render_sidebar():
    """Render the main sidebar with professional polish"""
    
    with st.sidebar:
        # Logo - PROFESSIONAL & CLEAN
        st.markdown("""
        <div style='text-align: center; padding-bottom: 2rem; border-bottom: 3px solid #d1dce5; margin-bottom: 2rem;'>
            <div style='width: 90px; height: 90px; margin: 0 auto 1rem; background: linear-gradient(135deg, #8ca6be 0%, #6d8aa0 100%); border: 4px solid white; border-radius: 20px; display: flex; align-items: center; justify-content: center; color: white; font-size: 2.5rem; font-weight: 700; box-shadow: 0 8px 24px rgba(140, 166, 190, 0.3);'>⚡</div>
            <div style='font-size: 1.8rem; font-weight: 800; background: linear-gradient(135deg, #8ca6be 0%, #6d8aa0 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.25rem; letter-spacing: 1px;'>XLR8</div>
            <div style='font-size: 0.9rem; color: #7d96a8; font-weight: 600; letter-spacing: 0.5px;'>by HCMPACT</div>
            <div style='display: inline-block; background: linear-gradient(135deg, rgba(140, 166, 190, 0.15) 0%, rgba(109, 138, 160, 0.15) 100%); color: #6d8aa0; padding: 0.3rem 0.9rem; border-radius: 14px; font-size: 0.75rem; font-weight: 700; margin-top: 0.75rem; border: 2px solid rgba(109, 138, 160, 0.2);'>v3.0</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Project selector
        _render_project_selector_11()
        
        st.markdown("<div style='border-top: 2px solid #e8eef3; margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
        
        # AI/RAG status
        _render_ai_selector_11()
        
        st.markdown("<div style='border-top: 2px solid #e8eef3; margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
        
        # Status
        _render_status_11()


def _render_project_selector_11():
    """Render project selector with professional polish"""
    st.markdown("""
    <h3 style='color: #6d8aa0; font-size: 1.1rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; font-weight: 700;'>
        📁 Active Project
    </h3>
    """, unsafe_allow_html=True)
    
    if st.session_state.get('projects'):
        project_names = list(st.session_state.projects.keys())
        current = st.session_state.get('current_project')
        
        selected = st.selectbox(
            "Select Project",
            [""] + project_names,
            index=project_names.index(current) + 1 if current in project_names else 0,
            key="sidebar_project_selector",
            label_visibility="collapsed"
        )
        
        if selected and selected != st.session_state.get('current_project'):
            st.session_state.current_project = selected
            st.rerun()
        
        if current:
            project_data = st.session_state.projects.get(current, {})
            
            # Get project type styling
            impl_type = project_data.get('implementation_type', 'N/A')
            if 'Pro' in impl_type and 'WFM' in impl_type:
                type_icon = "🔵🟢"
                bg_color = "linear-gradient(135deg, #e3f2fd 0%, #e8f5e9 100%)"
            elif 'Pro' in impl_type:
                type_icon = "🔵"
                bg_color = "linear-gradient(135deg, #e3f2fd 0%, #f0f7ff 100%)"
            elif 'WFM' in impl_type:
                type_icon = "🟢"
                bg_color = "linear-gradient(135deg, #e8f5e9 0%, #f1f8f4 100%)"
            else:
                type_icon = "📁"
                bg_color = "linear-gradient(135deg, #f5f7f9 0%, #e8eef3 100%)"
            
            st.markdown(f"""
            <div style='background: {bg_color}; padding: 1rem; border-radius: 10px; margin-top: 0.75rem; border: 2px solid rgba(109, 138, 160, 0.15); box-shadow: 0 2px 8px rgba(0,0,0,0.05);'>
                <div style='font-size: 1.5rem; margin-bottom: 0.5rem;'>{type_icon}</div>
                <div style='color: #6c757d; font-size: 0.85rem; line-height: 1.6;'>
                    <div style='margin-bottom: 0.4rem;'>
                        <strong style='color: #8ca6be;'>Type:</strong> 
                        <span style='color: #6d8aa0; font-weight: 600;'>{impl_type}</span>
                    </div>
                    <div style='margin-bottom: 0.4rem;'>
                        <strong style='color: #8ca6be;'>Customer:</strong> 
                        <span style='color: #6d8aa0; font-weight: 600;'>{project_data.get('customer_id', 'N/A')}</span>
                    </div>
                    {f"<div><strong style='color: #8ca6be;'>Consultant:</strong> <span style='color: #6d8aa0; font-weight: 600;'>{project_data.get('consultant')}</span></div>" if project_data.get('consultant') else ""}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #fff3cd 0%, #fffef0 100%); padding: 1rem; border-radius: 10px; border: 2px solid #ffc107; text-align: center;'>
            <div style='font-size: 1.5rem; margin-bottom: 0.5rem;'>📋</div>
            <div style='color: #856404; font-size: 0.85rem; font-weight: 600;'>
                No projects yet
            </div>
            <div style='color: #856404; font-size: 0.75rem; margin-top: 0.25rem;'>
                Create one in Setup tab
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_ai_selector_11():
    """Render AI/RAG status and LLM provider selector with professional polish"""
    st.markdown("""
    <h3 style='color: #6d8aa0; font-size: 1.1rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; font-weight: 700;'>
        🧠 AI System
    </h3>
    """, unsafe_allow_html=True)
    
    # LLM Provider Selection
    llm_provider = st.selectbox(
        "🤖 AI Provider",
        ["Local LLM", "Claude API"],
        index=0 if st.session_state.get('llm_provider', 'local') == 'local' else 1,
        help="Choose between local DeepSeek or Claude API"
    )
    
    # Update session state
    new_provider = 'local' if llm_provider == "Local LLM" else 'claude'
    if st.session_state.get('llm_provider') != new_provider:
        st.session_state.llm_provider = new_provider
    
    # Show provider-specific config
    if llm_provider == "Local LLM":
        st.markdown("""
        <div style='background: linear-gradient(135deg, #e8f5e9 0%, #f1f8f4 100%); padding: 1rem; border-radius: 10px; border: 2px solid #28a745; margin-top: 0.75rem; box-shadow: 0 2px 8px rgba(40, 167, 69, 0.1);'>
            <div style='display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;'>
                <span style='font-size: 1.2rem;'>⚡</span>
                <strong style='color: #28a745; font-size: 0.95rem;'>Local DeepSeek</strong>
            </div>
            <div style='color: #155724; font-size: 0.8rem; line-height: 1.6;'>
                <div>✓ Free & Private</div>
                <div>✓ Good for detailed docs</div>
                <div>✓ Model: deepseek-r1:7b</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:  # Claude API
        api_key = st.text_input(
            "Claude API Key",
            type="password",
            value=st.session_state.get('claude_api_key', ''),
            help="Get your key at console.anthropic.com",
            key="claude_api_key_input"
        )
        
        if st.button("💾 Save API Key", type="primary", use_container_width=True):
            st.session_state.claude_api_key = api_key
            st.success("API Key saved!")
            st.rerun()
        
        if st.session_state.get('claude_api_key'):
            st.markdown("""
            <div style='background: linear-gradient(135deg, #e3f2fd 0%, #f0f7ff 100%); padding: 1rem; border-radius: 10px; border: 2px solid #2196F3; margin-top: 0.75rem; box-shadow: 0 2px 8px rgba(33, 150, 243, 0.1);'>
                <div style='display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;'>
                    <span style='font-size: 1.2rem;'>🧠</span>
                    <strong style='color: #1976d2; font-size: 0.95rem;'>Claude API</strong>
                </div>
                <div style='color: #0d47a1; font-size: 0.8rem; line-height: 1.6;'>
                    <div>✓ Excellent quality</div>
                    <div>✓ ~$0.015 per response</div>
                    <div>✓ Model: Claude Sonnet 4</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #fff3cd 0%, #fffef0 100%); padding: 1rem; border-radius: 10px; border: 2px solid #ffc107; margin-top: 0.75rem; text-align: center;'>
                <div style='color: #856404; font-size: 0.85rem; font-weight: 600;'>⚠️ API key required</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("[Get API key →](https://console.anthropic.com/)", unsafe_allow_html=True)
    
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    
    # RAG Status
    rag_handler = st.session_state.get('rag_handler')
    rag_type = st.session_state.get('rag_type', 'none')
    
    if rag_handler:
        try:
            rag_stats = rag_handler.get_stats()
            
            # Check if advanced format
            if isinstance(rag_stats, dict) and any(isinstance(v, dict) for v in rag_stats.values()):
                total_docs = sum(s.get('unique_documents', 0) for s in rag_stats.values() if isinstance(s, dict))
                total_chunks = sum(s.get('total_chunks', 0) for s in rag_stats.values() if isinstance(s, dict))
            else:
                total_docs = rag_stats.get('unique_documents', 0)
                total_chunks = rag_stats.get('total_chunks', 0)
            
            if total_docs > 0:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #e8f5e9 0%, #f1f8f4 100%); padding: 1rem; border-radius: 10px; border: 2px solid #28a745; box-shadow: 0 2px 8px rgba(40, 167, 69, 0.1);'>
                    <div style='display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;'>
                        <div style='display: flex; align-items: center; gap: 0.5rem;'>
                            <span style='font-size: 1.2rem;'>📚</span>
                            <strong style='color: #28a745; font-size: 0.95rem;'>RAG Active</strong>
                        </div>
                        <div style='background: #28a745; color: white; padding: 0.2rem 0.6rem; border-radius: 8px; font-size: 0.7rem; font-weight: 700;'>✓</div>
                    </div>
                    <div style='color: #155724; font-size: 0.85rem; font-weight: 600;'>
                        <div>{total_docs} documents</div>
                        <div>{total_chunks} chunks indexed</div>
                    </div>
                    <div style='margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid rgba(40, 167, 69, 0.2);'>
                        <small style='color: #155724; font-size: 0.75rem;'>
                            {'🚀 Advanced RAG' if rag_type == 'advanced' else '📚 Standard RAG'}
                        </small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style='background: linear-gradient(135deg, #fff3cd 0%, #fffef0 100%); padding: 1rem; border-radius: 10px; border: 2px solid #ffc107; text-align: center;'>
                    <div style='font-size: 1.2rem; margin-bottom: 0.25rem;'>📋</div>
                    <div style='color: #856404; font-size: 0.85rem; font-weight: 600;'>No documents yet</div>
                    <div style='color: #856404; font-size: 0.75rem; margin-top: 0.25rem;'>Upload in HCMPACT LLM</div>
                </div>
                """, unsafe_allow_html=True)
                
        except Exception as e:
            st.markdown("""
            <div style='background: #f8d7da; padding: 1rem; border-radius: 10px; border: 2px solid #dc3545; text-align: center;'>
                <div style='color: #721c24; font-size: 0.85rem; font-weight: 600;'>⚠️ RAG status unavailable</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background: #f8d7da; padding: 1rem; border-radius: 10px; border: 2px solid #dc3545; text-align: center;'>
            <div style='color: #721c24; font-size: 0.85rem; font-weight: 600;'>⚠️ RAG not initialized</div>
        </div>
        """, unsafe_allow_html=True)
    
    # LLM config - Collapsible
    with st.expander("🤖 LLM Configuration"):
        llm_endpoint = st.session_state.get('llm_endpoint', 'Not configured')
        llm_model = st.session_state.get('llm_model', 'Not configured')
        
        st.markdown(f"""
        <div style='background: #f8f9fa; padding: 0.75rem; border-radius: 8px; font-size: 0.8rem; line-height: 1.6;'>
            <div><strong style='color: #8ca6be;'>Endpoint:</strong><br>
            <span style='color: #6d8aa0; font-size: 0.75rem;'>{llm_endpoint}</span></div>
            <div style='margin-top: 0.5rem;'><strong style='color: #8ca6be;'>Model:</strong><br>
            <span style='color: #6d8aa0; font-size: 0.75rem;'>{llm_model}</span></div>
        </div>
        """, unsafe_allow_html=True)


def _render_status_11():
    """Render system status with professional polish"""
    st.markdown("""
    <h3 style='color: #6d8aa0; font-size: 1.1rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; font-weight: 700;'>
        ⚡ System Status
    </h3>
    """, unsafe_allow_html=True)
    
    # API status
    api_credentials = st.session_state.get('api_credentials', {'pro': {}, 'wfm': {}})
    pro_configured = bool(api_credentials.get('pro'))
    wfm_configured = bool(api_credentials.get('wfm'))
    
    st.markdown(f"""
    <div style='background: white; padding: 1rem; border-radius: 10px; border: 2px solid #e8eef3; box-shadow: 0 2px 8px rgba(0,0,0,0.05);'>
        <div style='font-size: 0.9rem; line-height: 2;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <span style='color: #6c757d;'><strong style='color: #8ca6be;'>UKG Pro:</strong></span>
                <span style='font-size: 1.2rem;'>{'✅' if pro_configured else '⚪'}</span>
            </div>
            <div style='display: flex; justify-content: space-between; align-items: center; padding-top: 0.5rem; border-top: 1px solid #e8eef3; margin-top: 0.5rem;'>
                <span style='color: #6c757d;'><strong style='color: #8ca6be;'>UKG WFM:</strong></span>
                <span style='font-size: 1.2rem;'>{'✅' if wfm_configured else '⚪'}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Security info
    with st.expander("🔒 Security & Privacy"):
        st.markdown("""
        <div style='background: linear-gradient(135deg, #f5f7f9 0%, #e8eef3 100%); padding: 1rem; border-radius: 8px; font-size: 0.8rem; line-height: 1.8; border: 2px solid rgba(109, 138, 160, 0.15);'>
            <div style='color: #28a745; font-weight: 600; margin-bottom: 0.5rem;'>✓ Fully Secure</div>
            <div style='color: #6c757d;'>
                <div>• Local Processing</div>
                <div>• Session-Only Storage</div>
                <div>• No External APIs</div>
                <div>• PII Protected</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
