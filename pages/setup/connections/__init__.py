"""
API Connections Management
Configure UKG Pro and WFM API credentials
"""

import streamlit as st


def render_connections_page():
    """Render API connections configuration page"""
    
    st.markdown("## 🔌 API Connections")
    
    st.markdown("""
    <div class='info-box'>
        <strong>API Configuration:</strong> Configure API credentials for UKG Pro and WFM
        to enable direct data integration and automated template uploads.
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize API credentials
    if 'api_credentials' not in st.session_state:
        st.session_state.api_credentials = {'pro': {}, 'wfm': {}}
    
    # Connection status
    pro_configured = bool(st.session_state.api_credentials['pro'])
    wfm_configured = bool(st.session_state.api_credentials['wfm'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        status = "✅ Connected" if pro_configured else "⚠️ Not Configured"
        st.metric("UKG Pro", status)
    
    with col2:
        status = "✅ Connected" if wfm_configured else "⚠️ Not Configured"
        st.metric("UKG WFM", status)
    
    st.markdown("---")
    
    # UKG Pro Configuration
    st.markdown("### 🔵 UKG Pro Configuration")
    
    with st.expander("Configure UKG Pro API", expanded=not pro_configured):
        with st.form("pro_api_form"):
            pro_tenant_url = st.text_input(
                "Tenant URL *",
                value=st.session_state.api_credentials['pro'].get('tenant_url', ''),
                placeholder="https://service.ultipro.com",
                help="Your UKG Pro tenant URL"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                pro_username = st.text_input(
                    "API Username *",
                    value=st.session_state.api_credentials['pro'].get('username', ''),
                    help="API service account username"
                )
            with col2:
                pro_password = st.text_input(
                    "API Password *",
                    type="password",
                    value=st.session_state.api_credentials['pro'].get('password', ''),
                    help="API service account password"
                )
            
            col1, col2 = st.columns(2)
            with col1:
                pro_app_key = st.text_input(
                    "Application Key *",
                    value=st.session_state.api_credentials['pro'].get('app_key', ''),
                    type="password",
                    help="API application key"
                )
            with col2:
                pro_customer_key = st.text_input(
                    "Customer API Key *",
                    value=st.session_state.api_credentials['pro'].get('customer_key', ''),
                    type="password",
                    help="Customer-specific API key"
                )
            
            submitted_pro = st.form_submit_button("💾 Save UKG Pro Credentials", use_container_width=True)
            
            if submitted_pro:
                if all([pro_tenant_url, pro_username, pro_password, pro_app_key, pro_customer_key]):
                    st.session_state.api_credentials['pro'] = {
                        'tenant_url': pro_tenant_url,
                        'username': pro_username,
                        'password': pro_password,
                        'app_key': pro_app_key,
                        'customer_key': pro_customer_key
                    }
                    st.success("✅ UKG Pro credentials saved!")
                    st.rerun()
                else:
                    st.error("❌ All fields are required")
    
    # UKG WFM Configuration
    st.markdown("### 🟢 UKG WFM (Dimensions) Configuration")
    
    with st.expander("Configure UKG WFM API", expanded=not wfm_configured):
        with st.form("wfm_api_form"):
            wfm_base_url = st.text_input(
                "Base URL *",
                value=st.session_state.api_credentials['wfm'].get('base_url', ''),
                placeholder="https://wfm.ultipro.com",
                help="Your UKG WFM instance URL"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                wfm_username = st.text_input(
                    "API Username *",
                    value=st.session_state.api_credentials['wfm'].get('username', ''),
                    help="WFM API username"
                )
            with col2:
                wfm_password = st.text_input(
                    "API Password *",
                    type="password",
                    value=st.session_state.api_credentials['wfm'].get('password', ''),
                    help="WFM API password"
                )
            
            wfm_app_key = st.text_input(
                "Application Key *",
                value=st.session_state.api_credentials['wfm'].get('app_key', ''),
                type="password",
                help="WFM application key"
            )
            
            submitted_wfm = st.form_submit_button("💾 Save UKG WFM Credentials", use_container_width=True)
            
            if submitted_wfm:
                if all([wfm_base_url, wfm_username, wfm_password, wfm_app_key]):
                    st.session_state.api_credentials['wfm'] = {
                        'base_url': wfm_base_url,
                        'username': wfm_username,
                        'password': wfm_password,
                        'app_key': wfm_app_key
                    }
                    st.success("✅ UKG WFM credentials saved!")
                    st.rerun()
                else:
                    st.error("❌ All fields are required")
    
    # Clear credentials option
    st.markdown("---")
    st.markdown("### 🗑️ Manage Credentials")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if pro_configured and st.button("Clear UKG Pro Credentials"):
            st.session_state.api_credentials['pro'] = {}
            st.success("✅ UKG Pro credentials cleared")
            st.rerun()
    
    with col2:
        if wfm_configured and st.button("Clear UKG WFM Credentials"):
            st.session_state.api_credentials['wfm'] = {}
            st.success("✅ UKG WFM credentials cleared")
            st.rerun()
    
    # Security notice
    st.markdown("---")
    st.markdown("""
    <div class='warning-box'>
        <strong>🔒 Security Note:</strong> API credentials are stored in your session only
        and are never saved to disk or transmitted to external servers. They are cleared
        when you close your browser or session expires.
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    st.title("Connections - Test")
    render_connections_page()
