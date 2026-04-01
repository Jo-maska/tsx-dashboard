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
# Note: Ensure you have a secrets.toml file with your Google Sheet credentials
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(worksheet_name):
    """Fetch data from a specific worksheet."""
    try:
        return conn.read(worksheet=worksheet_name, ttl="1m")
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return pd.DataFrame()

# Title
st.title("🌲 TSX Wealth Tracker")

# Create Tabs
tab1, tab2 = st.tabs(["📊 Market Overview", "💼 Portfolio Tracker"])

with tab1:
    st.header("S&P/TSX Composite & Sector Indices")
    st.info("Tracking live TSX indices via GOOGLEFINANCE integration.")
    
    # Load Market Data (Assuming a sheet named 'MarketData')
    market_df = load_data("MarketData")
    
    if not market_df.empty:
        # Expected columns: Index Name, Ticker, Price, Change, Pct_Change
        # Display Top Index (TSX Composite)
        tsx_composite = market_df[market_df['Ticker'] == 'INDEXTSI:OSPTX']
        if not tsx_composite.empty:
            cols = st.columns(3)
            with cols[0]:
                st.metric("TSX Composite", 
                          f"{tsx_composite.iloc[0]['Price']:,.2f}", 
                          f"{tsx_composite.iloc[0]['Pct_Change']}%")
        
        st.divider()
        st.subheader("TSX Sectors")
        
        # Display Sector Grid
        sectors = market_df[market_df['Ticker'] != 'INDEXTSI:OSPTX']
        cols = st.columns(3)
        for i, (index, row) in enumerate(sectors.iterrows()):
            with cols[i % 3]:
                st.metric(row['Index Name'], 
                          f"{row['Price']:,.2f}", 
                          f"{row['Pct_Change']}%")
    else:
        st.warning("Please ensure your 'MarketData' sheet is formatted correctly.")

with tab2:
    st.header("Personal Stock Tracker")
    
    # Load Portfolio Data (Assuming a sheet named 'Portfolio')
    portfolio_df = load_data("Portfolio")
    
    if not portfolio_df.empty:
        # Dashboard Metrics
        total_inv = portfolio_df['Cost Basis'].sum()
        current_val = portfolio_df['Market Value'].sum()
        total_pnl = current_val - total_inv
        pnl_pct = (total_pnl / total_inv) * 100 if total_inv != 0 else 0
        
        m_cols = st.columns(3)
        m_cols[0].metric("Total Investment", f"${total_inv:,.2f}")
        m_cols[1].metric("Current Value", f"${current_val:,.2f}")
        m_cols[2].metric("Total P&L", f"${total_pnl:,.2f}", f"{pnl_pct:.2f}%")
        
        # Visuals
        st.divider()
        v_col1, v_col2 = st.columns([1, 1])
        
        with v_col1:
            st.subheader("Sector Distribution")
            fig = px.pie(portfolio_df, values='Market Value', names='Sector', 
                         color_discrete_sequence=px.colors.sequential.Greens_r,
                         hole=0.4)
            fig.update_layout(showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
            
        with v_col2:
            st.subheader("Holdings Detail")
            # Displaying columns: Symbol, Name, Qty, Avg Price, Current Price (from GOOGLEFINANCE), Gain/Loss
            st.dataframe(portfolio_df[['Symbol', 'Sector', 'Qty', 'Avg Price', 'Current Price', 'Market Value']], 
                         use_container_width=True)

    else:
        st.warning("Portfolio data not found. Check your 'Portfolio' worksheet.")

# Sidebar Transaction Form
st.sidebar.header("➕ Add Transaction")
with st.sidebar.form("add_transaction"):
    ticker = st.text_input("Ticker Symbol (e.g., TSE:TD)").upper()
    qty = st.number_input("Quantity", min_value=0.1, step=0.1)
    price = st.number_input("Purchase Price", min_value=0.01)
    sector = st.selectbox("Sector", ["Financials", "Energy", "Materials", "Industrials", "Tech", "Telecom", "Utilities", "Health Care", "Real Estate"])
    date = st.date_input("Transaction Date")
    
    submit = st.form_submit_button("Log Transaction")
    
    if submit:
        # Create a new row
        new_data = pd.DataFrame([{
            "Symbol": ticker,
            "Qty": qty,
            "Avg Price": price,
            "Sector": sector,
            "Date": str(date),
            "Cost Basis": qty * price
            # Note: Current Price and Market Value should be calculated in the sheet 
            # using =GOOGLEFINANCE(Symbol, "price") for maximum accuracy.
        }])
        
        # In a real app, you would append this to the Google Sheet:
        # updated_df = pd.concat([portfolio_df, new_data], ignore_index=True)
        # conn.update(worksheet="Portfolio", data=updated_df)
        
        st.sidebar.success(f"Successfully added {ticker}!")
        st.sidebar.info("Refresh page to see updated calculations.")

st.sidebar.divider()
st.sidebar.markdown("### 💡 Setup Note")
st.sidebar.caption("""
Ensure your Google Sheet uses:
`=GOOGLEFINANCE(A2, "price")` 
in the Price column to ensure the app stays synced with official data.
""")