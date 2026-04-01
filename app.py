import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="TSX Wealth Tracker",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background-color: #f0f4f0; }
    div[data-testid="stMetricValue"] { color: #1b5e20; font-weight: 700; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; background-color: #e8f5e9; border-radius: 10px; padding: 4px;
    }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 8px 20px; font-weight: 500; }
    .stTabs [aria-selected="true"] { background-color: #2e7d32 !important; color: white !important; }
    .stButton > button {
        background-color: #2e7d32; color: white; border-radius: 8px;
        border: none; font-weight: 600; width: 100%;
    }
    .stButton > button:hover { background-color: #1b5e20; }
    div[data-testid="stSidebar"] { background-color: #1b5e20; }
    div[data-testid="stSidebar"] * { color: white !important; }
    </style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ⚙️  PASTE YOUR TWO CSV URLs HERE
#
# HOW TO GET THEM:
# 1. Open your Google Sheet
# 2. Click Share → "Anyone with the link" → Viewer → Done
# 3. Your sheet URL looks like:
#    https://docs.google.com/spreadsheets/d/SHEET_ID/edit#gid=TAB_GID
# 4. Build the CSV URL like this:
#    https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=TAB_GID
#
# To find each tab's gid:
#   - Click the MarketData tab → look at URL bar → copy number after gid=
#   - Click the Portfolio tab  → do the same
# ─────────────────────────────────────────────

MARKET_DATA_CSV_URL = "https://docs.google.com/spreadsheets/d/1DND5r7Zt3VRwpVLzzbEELtn1htFSf6-_twH0Nfevg6E/export?format=csv&gid=0#gid=0"
PORTFOLIO_CSV_URL   = "https://docs.google.com/spreadsheets/d/1DND5r7Zt3VRwpVLzzbEELtn1htFSf6-_twH0Nfevg6E/export?format=csv&gid=1345739298#gid=1345739298"


# ─────────────────────────────────────────────
# DATA LOADER — pure CSV, zero credentials
# ─────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def load_csv(url: str, label: str) -> pd.DataFrame:
    """Fetch a public Google Sheet tab as CSV. No API key needed."""
    if "YOUR_SHEET_ID" in url:
        return pd.DataFrame()
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        df = df.dropna(how="all")
        return df
    except Exception as e:
        st.error(f"❌ Could not load **{label}**. Make sure the sheet is set to 'Anyone with the link → Viewer'. Error: {e}")
        return pd.DataFrame()


def safe_float(val):
    """Convert value to float, stripping $, %, commas."""
    try:
        return float(str(val).replace('%', '').replace(',', '').replace('$', '').strip())
    except (ValueError, TypeError):
        return 0.0


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
c1, c2 = st.columns([5, 1])
with c1:
    st.markdown("## 🌲 TSX Wealth Tracker")
    st.caption(f"Last refreshed: {datetime.now().strftime('%b %d, %Y  %I:%M %p')}")
with c2:
    st.write("")
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# Setup banner
if "YOUR_SHEET_ID" in MARKET_DATA_CSV_URL:
    st.warning("""
    ⚙️ **Quick Setup — 2 steps only:**
    1. Share your Google Sheet → **Anyone with the link → Viewer**
    2. Paste your two CSV export URLs into `app.py` at the top (see comments for instructions)
    """)

st.divider()
tab1, tab2 = st.tabs(["📊 Market Overview", "💼 Portfolio Tracker"])


# ══════════════════════════════════════════════
# TAB 1 — MARKET OVERVIEW
# ══════════════════════════════════════════════
with tab1:
    st.subheader("S&P/TSX Composite & Sector Indices")

    with st.spinner("Loading market data..."):
        market_df = load_csv(MARKET_DATA_CSV_URL, "MarketData")

    if market_df.empty:
        st.info("""
        💡 **Your `MarketData` sheet tab needs these exact column headers in Row 1:**

        | Index Name | Ticker | Price | Change | Pct_Change |
        |---|---|---|---|---|
        | TSX Composite | INDEXTSI:OSPTX | =GOOGLEFINANCE(...) | ... | ... |
        | Financials | INDEXTSI:STFINL | ... | ... | ... |
        """)
    else:
        col_lower = {c.lower().replace(' ', '_'): c for c in market_df.columns}
        required  = ['index_name', 'ticker', 'price', 'pct_change']
        missing   = [r for r in required if r not in col_lower]

        if missing:
            st.error(
                f"❌ Missing columns: **{', '.join(missing)}**\n\n"
                f"Columns found in your sheet: `{list(market_df.columns)}`"
            )
        else:
            market_df = market_df.rename(columns={
                col_lower['index_name']: 'Index Name',
                col_lower['ticker']:     'Ticker',
                col_lower['price']:      'Price',
                col_lower['pct_change']: 'Pct_Change',
            })
            if 'change' in col_lower:
                market_df = market_df.rename(columns={col_lower['change']: 'Change'})

            market_df['Price']      = market_df['Price'].apply(safe_float)
            market_df['Pct_Change'] = market_df['Pct_Change'].apply(safe_float)

            # TSX Composite highlight card
            tsx = market_df[market_df['Ticker'].astype(str).str.upper() == 'INDEXTSI:OSPTX']
            if not tsx.empty:
                row   = tsx.iloc[0]
                pct   = row['Pct_Change']
                arrow = "▲" if pct >= 0 else "▼"
                color = "#2e7d32" if pct >= 0 else "#c62828"
                st.markdown(f"""
                    <div style="background:white;border-radius:14px;padding:1.4rem 2rem;
                                box-shadow:0 2px 10px rgba(0,0,0,0.08);
                                border-left:5px solid {color};margin-bottom:1rem;">
                        <div style="font-size:0.8rem;color:#666;font-weight:600;letter-spacing:1px;">
                            S&P/TSX COMPOSITE INDEX
                        </div>
                        <div style="font-size:2.4rem;font-weight:700;color:#1b5e20;line-height:1.2;">
                            {row['Price']:,.2f}
                        </div>
                        <div style="font-size:1rem;color:{color};font-weight:500;">
                            {arrow} {pct:+.2f}% today
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            sectors = market_df[market_df['Ticker'].astype(str).str.upper() != 'INDEXTSI:OSPTX']
            if not sectors.empty:
                st.markdown("#### TSX Sectors")
                cols = st.columns(3)
                for i, (_, row) in enumerate(sectors.iterrows()):
                    with cols[i % 3]:
                        st.metric(row['Index Name'], f"{row['Price']:,.2f}", f"{row['Pct_Change']:+.2f}%")

                st.divider()
                st.markdown("#### Sector Performance")
                fig = go.Figure(go.Bar(
                    x=sectors['Index Name'],
                    y=sectors['Pct_Change'],
                    marker_color=['#2e7d32' if v >= 0 else '#c62828' for v in sectors['Pct_Change']],
                    text=[f"{v:+.2f}%" for v in sectors['Pct_Change']],
                    textposition='outside'
                ))
                fig.update_layout(
                    plot_bgcolor='white', paper_bgcolor='white',
                    yaxis_title="% Change", height=360,
                    margin=dict(t=20, b=40), font=dict(family="Inter")
                )
                st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════
# TAB 2 — PORTFOLIO TRACKER
# ══════════════════════════════════════════════
with tab2:
    st.subheader("Personal Portfolio")

    with st.spinner("Loading portfolio..."):
        portfolio_df = load_csv(PORTFOLIO_CSV_URL, "Portfolio")

    if portfolio_df.empty:
        st.info("""
        💡 **Your `Portfolio` sheet tab needs these exact column headers in Row 1:**

        | Symbol | Sector | Qty | Avg Price | Current Price | Market Value | Cost Basis |
        |---|---|---|---|---|---|---|
        | TSE:TD | Financials | 10 | 85.00 | =GOOGLEFINANCE(A2,"price") | =C2*E2 | =C2*D2 |
        """)
    else:
        num_cols = ['Qty', 'Avg Price', 'Current Price', 'Market Value', 'Cost Basis']
        for col in num_cols:
            if col in portfolio_df.columns:
                portfolio_df[col] = portfolio_df[col].apply(safe_float)

        required_p = ['Cost Basis', 'Market Value']
        missing_p  = [c for c in required_p if c not in portfolio_df.columns]

        if missing_p:
            st.error(
                f"❌ Missing columns: **{', '.join(missing_p)}**\n\n"
                f"Columns found: `{list(portfolio_df.columns)}`"
            )
        else:
            total_inv   = portfolio_df['Cost Basis'].sum()
            current_val = portfolio_df['Market Value'].sum()
            total_pnl   = current_val - total_inv
            pnl_pct     = (total_pnl / total_inv * 100) if total_inv != 0 else 0

            m1, m2, m3 = st.columns(3)
            m1.metric("💰 Total Invested", f"${total_inv:,.2f}")
            m2.metric("📈 Current Value",  f"${current_val:,.2f}")
            m3.metric("💹 Total P&L",      f"${total_pnl:,.2f}", f"{pnl_pct:+.2f}%")

            st.divider()
            v1, v2 = st.columns(2)

            with v1:
                st.markdown("#### Sector Allocation")
                if 'Sector' in portfolio_df.columns:
                    fig_pie = px.pie(
                        portfolio_df, values='Market Value', names='Sector',
                        color_discrete_sequence=px.colors.sequential.Greens_r, hole=0.45
                    )
                    fig_pie.update_layout(
                        margin=dict(t=10, b=10), font=dict(family="Inter"), paper_bgcolor='white'
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

            with v2:
                st.markdown("#### Holdings Detail")
                show_cols = [c for c in ['Symbol','Sector','Qty','Avg Price','Current Price','Market Value','Cost Basis']
                             if c in portfolio_df.columns]
                fmt = {c: '${:,.2f}' for c in ['Avg Price','Current Price','Market Value','Cost Basis'] if c in show_cols}
                if 'Qty' in show_cols:
                    fmt['Qty'] = '{:,.2f}'
                st.dataframe(
                    portfolio_df[show_cols].style.format(fmt),
                    use_container_width=True, height=300
                )

            if 'Symbol' in portfolio_df.columns:
                st.divider()
                st.markdown("#### Gain / Loss per Holding")
                portfolio_df['P&L %'] = (
                    (portfolio_df['Market Value'] - portfolio_df['Cost Basis'])
                    / portfolio_df['Cost Basis'] * 100
                ).round(2)
                fig_bar = go.Figure(go.Bar(
                    x=portfolio_df['Symbol'],
                    y=portfolio_df['P&L %'],
                    marker_color=['#2e7d32' if v >= 0 else '#c62828' for v in portfolio_df['P&L %']],
                    text=[f"{v:+.1f}%" for v in portfolio_df['P&L %']],
                    textposition='outside'
                ))
                fig_bar.update_layout(
                    plot_bgcolor='white', paper_bgcolor='white',
                    yaxis_title="% Gain / Loss", height=300,
                    margin=dict(t=20, b=20), font=dict(family="Inter")
                )
                st.plotly_chart(fig_bar, use_container_width=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
st.sidebar.markdown("## 📋 How to Add Transactions")
st.sidebar.markdown("""
Since the sheet is read-only (no API), add transactions **directly in Google Sheets**:

1. Open your Google Sheet
2. Go to the **Portfolio** tab
3. Add a new row:
   - Symbol, Sector, Qty, Avg Price
   - `=GOOGLEFINANCE(A2,"price")` → Current Price column
   - `=C2*E2` → Market Value column
   - `=C2*D2` → Cost Basis column
4. Come back here and click **🔄 Refresh**
""")
st.sidebar.divider()
st.sidebar.markdown("#### ⚙️ One-Time Setup")
st.sidebar.markdown("""
1. Share sheet → **Anyone with link → Viewer**
2. Get CSV export URLs for each tab
3. Paste into `app.py` at the top
4. Deploy — **no secrets.toml needed!**
""")
st.sidebar.caption("Auto-refreshes every 60s. GOOGLEFINANCE may delay up to 20 min.")
