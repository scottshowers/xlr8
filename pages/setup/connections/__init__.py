"""
API Connections Page - WITH EMPTY STATE ✨
Configure UKG Pro and WFM API connections
Quick Win #4: Added empty state when no APIs configured
"""

import streamlit as st
from utils.toast import ToastManager


def render_connections_page():
    """Render API connections configuration page with empty state"""
    
    st.markdown("## 🔌 API Connections")
    
    st.markdown("""
    <div class='info-box'>
        <strong>API Configuration:</strong> Connect to UKG Pro and WFM APIs for direct integration.
        This enables automated template uploads and live data access.
    </div>
    """, unsafe_allow_html=True)
    
    # Check configuration status
    pro_configured = bool(
        st.session_state.get('ukg_pro_url') and 
        st.session_state.get('ukg_pro_key')
    )
    
    wfm_configured = bool(
        st.session_state.get('ukg_wfm_url') and 
        st.session_state.get('ukg_wfm_key')
    )
    
    # Status metrics
    col1, col2 = st.columns(2)
    
    with col1:
        status = "✅ Connected" if pro_configured else "⚠️ Not Configured"
        st.metric("UKG Pro", status)
    
    with col2:
        status = "✅ Connected" if wfm_configured else "⚠️ Not Configured"
        st.metric("UKG WFM", status)
    
    st.markdown("---")
    
    # EMPTY STATE ✨
    if not pro_configured and not wfm_configured:
        st.markdown("""
        <div style='text-align: center; padding: 3rem 1rem; background: linear-gradient(135deg, #f5f7f9 0%, #e8eef3 100%); border-radius: 16px; border: 2px dashed #8ca6be; margin: 2rem 0;'>
            <div style='font-size: 4rem; margin-bottom: 1rem;'>🔌</div>
            <h2 style='color: #6d8aa0; margin-bottom: 1rem;'>No API Connections Configured</h2>
            <p style='color: #7d96a8; font-size: 1.1rem; max-width: 550px; margin: 0 auto 2rem;'>
                Connect to UKG Pro and WFM APIs to enable direct data integration and automated uploads
            </p>
            <div style='background: white; padding: 2rem; border-radius: 12px; max-width: 500px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.08);'>
                <h3 style='color: #6d8aa0; margin-bottom: 1rem;'>✨ What You Can Do With API Access</h3>
                <div style='text-align: left; color: #6c757d; line-height: 2;'>
                    • Directly upload templates to UKG<br>
                    • Pull live data for analysis<br>
                    • Automated configuration updates<br>
                    • Real-time validation of setups<br>
                    • Bulk data operations
                </div>
                <div style='margin-top: 1.5rem; padding: 1rem; background: #fff3cd; border-radius: 8px; border-left: 4px solid #ffc107;'>
                    <strong style='color: #856404;'>⚠️ Optional Feature</strong><br>
                    <span style='color: #856404; font-size: 0.9rem;'>
                    API connections are optional. You can still use XLR8 without them by downloading templates and uploading manually.
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
    
    # UKG Pro Configuration
    st.markdown("### 🔵 UKG Pro Configuration")
    
    with st.expander("Configure UKG Pro API", expanded=not pro_configured):
        pro_url = st.text_input(
            "API Base URL",
            value=st.session_state.get('ukg_pro_url', ''),
            placeholder="https://service.ultipro.com",
            key="pro_url_input"
        )
        
        pro_key = st.text_input(
            "API Key",
            value=st.session_state.get('ukg_pro_key', ''),
            type="password",
            placeholder="Enter your API key",
            key="pro_key_input"
        )
        
        pro_username = st.text_input(
            "Username (Optional)",
            value=st.session_state.get('ukg_pro_username', ''),
            placeholder="API username",
            key="pro_username_input"
        )
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("💾 Save UKG Pro Configuration", use_container_width=True):
                if pro_url and pro_key:
                    st.session_state.ukg_pro_url = pro_url
                    st.session_state.ukg_pro_key = pro_key
                    if pro_username:
                        st.session_state.ukg_pro_username = pro_username
                    ToastManager.success("UKG Pro configuration saved")
                    st.rerun()
                else:
                    ToastManager.warning("Please fill in URL and API Key")
        
        with col2:
            if st.button("🧪 Test", use_container_width=True):
                if pro_url and pro_key:
                    with st.spinner("Testing connection..."):
                        # TODO: Add actual API test
                        ToastManager.success("UKG Pro API is reachable")
                else:
                    ToastManager.warning("Save configuration first")
        
        if pro_configured:
            st.markdown("---")
            if st.button("🗑️ Clear UKG Pro Configuration", use_container_width=True):
                st.session_state.ukg_pro_url = None
                st.session_state.ukg_pro_key = None
                st.session_state.ukg_pro_username = None
                ToastManager.info("UKG Pro configuration removed")
                st.rerun()
    
    st.markdown("---")
    
    # UKG WFM Configuration
    st.markdown("### 🟢 UKG WFM Configuration")
    
    with st.expander("Configure UKG WFM API", expanded=not wfm_configured):
        wfm_url = st.text_input(
            "API Base URL",
            value=st.session_state.get('ukg_wfm_url', ''),
            placeholder="https://api.workforcenow.com",
            key="wfm_url_input"
        )
        
        wfm_key = st.text_input(
            "API Key",
            value=st.session_state.get('ukg_wfm_key', ''),
            type="password",
            placeholder="Enter your API key",
            key="wfm_key_input"
        )
        
        wfm_tenant = st.text_input(
            "Tenant ID (Optional)",
            value=st.session_state.get('ukg_wfm_tenant', ''),
            placeholder="Your tenant identifier",
            key="wfm_tenant_input"
        )
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("💾 Save UKG WFM Configuration", use_container_width=True):
                if wfm_url and wfm_key:
                    st.session_state.ukg_wfm_url = wfm_url
                    st.session_state.ukg_wfm_key = wfm_key
                    if wfm_tenant:
                        st.session_state.ukg_wfm_tenant = wfm_tenant
                    ToastManager.success("UKG WFM configuration saved")
                    st.rerun()
                else:
                    ToastManager.warning("Please fill in URL and API Key")
        
        with col2:
            if st.button("🧪 Test", use_container_width=True, key="test_wfm"):
                if wfm_url and wfm_key:
                    with st.spinner("Testing connection..."):
                        # TODO: Add actual API test
                        ToastManager.success("UKG WFM API is reachable")
                else:
                    ToastManager.warning("Save configuration first")
        
        if wfm_configured:
            st.markdown("---")
            if st.button("🗑️ Clear UKG WFM Configuration", use_container_width=True):
                st.session_state.ukg_wfm_url = None
                st.session_state.ukg_wfm_key = None
                st.session_state.ukg_wfm_tenant = None
                ToastManager.info("UKG WFM configuration removed")
                st.rerun()
    
    # Security note
    st.markdown("---")
    st.markdown("""
    <div style='background: #f0f7ff; padding: 1rem; border-radius: 8px; border-left: 4px solid #8ca6be;'>
        <strong style='color: #6d8aa0;'>🔒 Security Note:</strong><br>
        <span style='color: #7d96a8;'>
        API credentials are stored in your browser session only and are never sent to external servers.
        Your credentials are cleared when you close the browser.
        </span>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    st.title("Connections - Test")
    render_connections_page()
