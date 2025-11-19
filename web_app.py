import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from app.rci_aggregate import calculate_rci

# --------------------------------------------------
# Page Setup

# To run locally:
# streamlit run web_app.py

# --------------------------------------------------
st.set_page_config(
    page_title="Regional Sustainability Index (RCI)",
    page_icon="🌎",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #F5F7FA; }
    .metric-card {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .small-note {
        font-size: 0.9em;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Sidebar
# --------------------------------------------------
st.sidebar.header("Enter a ZIP Code")
zip_code = st.sidebar.text_input("ZIP Code:", max_chars=10)

st.sidebar.markdown("---")
st.sidebar.markdown("### Options")
show_raw = st.sidebar.checkbox("Show raw data output")
show_components = st.sidebar.checkbox("Show component breakdown")
show_explanations = st.sidebar.checkbox("Show scoring explanations", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("Built by **Eric Rodriguez**")

# --------------------------------------------------
# Header
# --------------------------------------------------
st.title("Regional Sustainability Index")
st.subheader("A data-driven evaluation of environmental resilience & infrastructure stability")

st.markdown("""
This tool provides a combined **Regional Sustainability Score (RCI)** 
by aggregating multiple datasets covering hazard mitigation, infrastructure, 
financial resilience, and expected annual losses.
""")

# --------------------------------------------------
# Main logic
# --------------------------------------------------
if zip_code:
    with st.spinner("Analyzing data…"):
        result = calculate_rci(zip_code)

    if "error" in result:
        st.error(result["error"])
        st.stop()

    st.markdown("## Overall Rating")

    # --------------------------------------------------
    # Score Gauge
    # --------------------------------------------------
    def gauge_chart(value):
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#2F80ED"},
                'steps': [
                    {'range': [0, 40], 'color': '#ffcccc'},
                    {'range': [40, 70], 'color': '#fff2cc'},
                    {'range': [70, 100], 'color': '#ccffcc'}
                ],
            }
        ))
        fig.update_layout(height=250, margin=dict(l=30, r=30, t=10, b=10))
        return fig

    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.plotly_chart(gauge_chart(result["rci"]), use_container_width=True)
    with col2:
        st.markdown(f"""
        ### **RCI Score: `{result['rci']}`**

        **Region:** {result['county']}, {result['state']}  
        **ZIP Code:** {result['zip']}

        A higher score indicates **stronger resilience**, **better infrastructure**,  
        and **lower expected environmental risk exposure**.
        """)

    # --------------------------------------------------
    # Component Metrics
    # --------------------------------------------------
    st.markdown("## Component Scores")

    colA, colB, colC, colD = st.columns(4)

    components = {
        "Hazard Mitigation": result["hazard_score"],
        "Debt-to-Revenue": result["debt_revenue_score"],
        "Bridge Condition": result["bridge_score"],
        "Expected Annual Loss": result["eal_score"],
    }

    for (title, value), col in zip(components.items(), [colA, colB, colC, colD]):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <h4 style="color:#333333; margin-bottom:8px;">{title}</h4>
                <h2 style="color:#2F80ED;">{value if value is not None else "N/A"}</h2>
                <p class="small-note">0 to 100 scale</p>
            </div>
            """, unsafe_allow_html=True)


    # --------------------------------------------------
    # Optional raw data
    # --------------------------------------------------
    if show_raw:
        st.markdown("### Raw Result Dictionary")
        st.json(result)

    # --------------------------------------------------
    # Component breakdown chart
    # --------------------------------------------------
    if show_components:
        st.markdown("### Component Contribution Radar Chart")

        radar_fig = go.Figure()
        radar_fig.add_trace(go.Scatterpolar(
            r=list(components.values()),
            theta=list(components.keys()),
            fill='toself',
            name="Scores"
        ))
        radar_fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            height=400
        )
        st.plotly_chart(radar_fig, use_container_width=True)

    # --------------------------------------------------
    # Explanations
    # --------------------------------------------------
    if show_explanations:
        st.markdown("## How the RCI Score Works")

        with st.expander("Hazard Mitigation Score"):
            st.write("""
            Measures FEMA-approved mitigation planning coverage at the ZIP level.
            Higher scores indicate stronger planning and better disaster preparedness.
            """)

        with st.expander("Debt-to-Revenue Score"):
            st.write("""
            Evaluates financial resilience using state-level government debt relative to revenue.
            """)

        with st.expander("Bridge Condition Score"):
            st.write("""
            Uses county-level infrastructure data to assess the structural condition of critical bridges.
            """)

        with st.expander("Expected Annual Loss (EAL) Score"):
            st.write("""
            Derived from FEMA’s National Risk Index, estimating long-term expected economic losses from natural hazards.
            """)

    st.markdown("---")
    st.caption("Data sources: FEMA NRI, DOT Bridge Inventory, Gov Finance data, Hazard Plan datasets.")

else:
    st.info("Enter a ZIP code in the left sidebar to begin your analysis.")
