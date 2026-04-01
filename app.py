import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# Set page configuration
st.set_page_config(
    page_title="TSX Investment Dashboard",
    page_icon="📈",
    layout="wide"
)

# Custom Green Theme Styling
st.markdown("""
    <style>
    :root {
        --main-green: #2e7d32;
        --light-green: #e8f5e9;
    }
    .main {
        background-color: #f1f8e9;
    }
    div[data-testid="stMetricValue"] {
        color: #1b5e20;
    }
    .stButton>button {
        background-color: #2e7d32;
        color: white;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize Connection
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Connection Error: Please check your 'Advanced Settings' Secrets.")
    st.stop()

def load_data(worksheet_name):
    """Fetch data from a specific worksheet with fallback diagnostics."""
    try:
        # Standardize loading
        df = conn.read(worksheet=worksheet_name, ttl="1m")
        if df is not None:
            df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error reading worksheet '{worksheet_name}': {e}")
        st.info("💡 Tip: Check if the tab name in your Google Sheet exactly matches '" + worksheet_name + "'.")
        return pd.DataFrame()

# Title
st.title("🌲 TSX Wealth Tracker")

# Create Tabs
tab1, tab2 = st.tabs(["📊 Market Overview", "💼 Portfolio Tracker"])

with tab1:
    st.header("S&P/TSX Composite & Sector Indices")
    st.info("Tracking live TSX indices via GOOGLEFINANCE integration.")
    
    market_df = load_data("MarketData")
    
    if not market_df.empty:
        # Check for TSX Composite
        # Using a more flexible check in case Ticker column has extra text
        tsx_composite = market_df[market_df['Ticker'].astype(str).str.contains('OSPTX', na=False, case=False)]
        
        if not tsx_composite.empty:
            cols = st.columns(3)
            with cols[0]:
                st.metric("TSX Composite", 
                          f"{tsx_composite.iloc[0]['Price']:,.2f}", 
                          f"{tsx_composite.iloc[0]['Pct_Change']}%")
        
        st.divider()
        st.subheader("TSX Sectors")
        
        # Filter out the composite to show only sectors
        sectors = market_df[~market_df['Ticker'].astype(str).str.contains('OSPTX', na=False, case=False)]
        
        if not sectors.empty:
            cols = st.columns(3)
            for i, (index, row) in enumerate(sectors.iterrows()):
                with cols[i % 3]:
                    st.metric(row['Index Name'], 
                              f"{row['Price']:,.2f}", 
                              f"{row['Pct_Change']}%")
        else:
            st.info("No sector data rows found in 'MarketData'.")
    else:
        st.warning("Data not found. Please verify that your Google Sheet has a tab named 'MarketData'.")

with tab2:
    st.header("Personal Stock Tracker")
    
    portfolio_df = load_data("Portfolio")
    
    if not portfolio_df.empty:
        required_cols = ['Cost Basis', 'Market Value', 'Sector']
        # Check if required columns exist (case insensitive)
        actual_cols = [c.lower() for c in portfolio_df.columns]
        missing = [col for col in required_cols if col.lower() not in actual_cols]
        
        if not missing:
            # Map column names to ensure consistency
            col_map = {c: c for c in portfolio_df.columns if c.lower() in [rc.lower() for rc in required_cols]}
            
            total_inv = portfolio_df['Cost Basis'].sum()
            current_val = portfolio_df['Market Value'].sum()
            total_pnl = current_val - total_inv
            pnl_pct = (total_pnl / total_inv) * 100 if total_inv != 0 else 0
            
            m_cols = st.columns(3)
            m_cols[0].metric("Total Investment", f"${total_inv:,.2f}")
            m_cols[1].metric("Current Value", f"${current_val:,.2f}")
            m_cols[2].metric("Total P&L", f"${total_pnl:,.2f}", f"{pnl_pct:.2f}%")
            
            st.divider()
            v_col1, v_col2 = st.columns([1, 1])
            
            with v_col1:
                st.subheader("Sector Distribution")
                fig = px.pie(portfolio_df, values='Market Value', names='Sector', 
                             color_discrete_sequence=px.colors.sequential.Greens_r,
                             hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
                
            with v_col2:
                st.subheader("Holdings Detail")
                st.dataframe(portfolio_df, use_container_width=True)
        else:
            st.error(f"Missing columns in Portfolio sheet: {missing}")
            st.write("Found columns:", list(portfolio_df.columns))
    else:
        st.warning("Portfolio worksheet is empty or not found.")

# Sidebar Transaction Form
st.sidebar.header("➕ Add Transaction")
with st.sidebar.form("add_transaction"):
    ticker = st.text_input("Ticker Symbol (e.g., TSE:TD)").upper()
    qty = st.number_input("Quantity", min_value=0.1, step=0.1)
    price = st.number_input("Purchase Price", min_value=0.01)
    sector = st.selectbox("Sector", ["Financials", "Energy", "Materials", "Industrials", "Tech", "Telecom", "Utilities", "Health Care", "Real Estate"])
    
    submit = st.form_submit_button("Log Transaction")
    
    if submit:
        st.sidebar.success(f"Log request for {ticker} received.")
        st.sidebar.info("To enable writing, please use Service Account credentials in Secrets.")

st.sidebar.divider()
st.sidebar.caption("Connected to Google Sheets API")
