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
            # Clean column names: remove extra spaces and standardize
            df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error reading worksheet '{worksheet_name}': {e}")
        return pd.DataFrame()

# Sidebar Debugging & Info
st.sidebar.header("⚙️ Settings")
debug_mode = st.sidebar.checkbox("Show Debug Info", value=False)

# Title
st.title("🌲 TSX Wealth Tracker")

# Create Tabs
tab1, tab2 = st.tabs(["📊 Market Overview", "💼 Portfolio Tracker"])

with tab1:
    st.header("S&P/TSX Composite & Sector Indices")
    st.info("Tracking live TSX indices via GOOGLEFINANCE integration.")
    
    market_df = load_data("MarketData")
    
    if debug_mode and not market_df.empty:
        st.write("Debug: MarketData Columns found:", list(market_df.columns))
        st.write(market_df.head())

    if not market_df.empty:
        # We search for columns that contain 'Ticker' or 'Price' or 'Pct'
        ticker_col = next((c for c in market_df.columns if 'ticker' in c.lower()), None)
        price_col = next((c for c in market_df.columns if 'price' in c.lower()), None)
        change_col = next((c for c in market_df.columns if 'pct' in c.lower() or 'change' in c.lower()), None)
        name_col = next((c for c in market_df.columns if 'name' in c.lower()), None)

        if ticker_col and price_col:
            # Check for TSX Composite (OSPTX)
            tsx_composite = market_df[market_df[ticker_col].astype(str).str.contains('OSPTX', na=False, case=False)]
            
            if not tsx_composite.empty:
                cols = st.columns(3)
                with cols[0]:
                    val = tsx_composite.iloc[0][price_col]
                    delta = tsx_composite.iloc[0][change_col] if change_col else None
                    st.metric("TSX Composite", f"{val:,.2f}", f"{delta}%" if delta else None)
            
            st.divider()
            st.subheader("TSX Sectors")
            
            # Filter out the composite
            sectors = market_df[~market_df[ticker_col].astype(str).str.contains('OSPTX', na=False, case=False)]
            
            if not sectors.empty:
                display_cols = st.columns(3)
                for i, (index, row) in enumerate(sectors.iterrows()):
                    with display_cols[i % 3]:
                        label = row[name_col] if name_col else row[ticker_col]
                        val = row[price_col]
                        delta = row[change_col] if change_col else None
                        st.metric(label, f"{val:,.2f}", f"{delta}%" if delta else None)
        else:
            st.error(f"Could not find required columns. I found: {list(market_df.columns)}. Please ensure columns are named 'Ticker' and 'Price'.")
    else:
        st.warning("Data not found. Verify your Google Sheet has a tab named 'MarketData' and check the 'Show Debug Info' checkbox in the sidebar for more details.")

with tab2:
    st.header("Personal Stock Tracker")
    
    portfolio_df = load_data("Portfolio")
    
    if debug_mode and not portfolio_df.empty:
        st.write("Debug: Portfolio Columns found:", list(portfolio_df.columns))

    if not portfolio_df.empty:
        # Standardizing for Portfolio
        cost_col = next((c for c in portfolio_df.columns if 'cost' in c.lower()), None)
        mkt_col = next((c for c in portfolio_df.columns if 'market' in c.lower()), None)
        sec_col = next((c for c in portfolio_df.columns if 'sector' in c.lower()), None)
        
        if cost_col and mkt_col and sec_col:
            total_inv = portfolio_df[cost_col].sum()
            current_val = portfolio_df[mkt_col].sum()
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
                fig = px.pie(portfolio_df, values=mkt_col, names=sec_col, 
                             color_discrete_sequence=px.colors.sequential.Greens_r,
                             hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
                
            with v_col2:
                st.subheader("Holdings Detail")
                st.dataframe(portfolio_df, use_container_width=True)
        else:
            st.error("Missing required columns in Portfolio sheet (Cost Basis, Market Value, or Sector).")
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
        st.sidebar.info("Writing requires Service Account JSON in Secrets.")

st.sidebar.divider()
st.sidebar.caption("Connected to Google Sheets API")
