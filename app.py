import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
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

# ─────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main { background-color: #f0f4f0; }

    div[data-testid="stMetricValue"] {
        color: #1b5e20;
        font-weight: 700;
        font-size: 1.6rem;
    }
    div[data-testid="stMetricDelta"] { font-size: 0.9rem; }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #e8f5e9;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2e7d32 !important;
        color: white !important;
    }

    .stButton > button {
        background-color: #2e7d32;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1.2rem;
        font-weight: 600;
        width: 100%;
    }
    .stButton > button:hover { background-color: #1b5e20; }

    div[data-testid="stSidebar"] { background-color: #1b5e20; }
    div[data-testid="stSidebar"] * { color: white !important; }
    div[data-testid="stSidebar"] .stSelectbox label,
    div[data-testid="stSidebar"] .stTextInput label,
    div[data-testid="stSidebar"] .stNumberInput label,
    div[data-testid="stSidebar"] .stDateInput label { color: #c8e6c9 !important; }

    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        border-left: 4px solid #2e7d32;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# GOOGLE SHEETS CONNECTION (via gspread)
# ─────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """
    Authenticate using service account credentials stored in st.secrets.
    In secrets.toml, store your entire service account JSON under [gcp_service_account].
    """
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        return gspread.authorize(creds)
    except KeyError:
        st.error("❌ Missing `[gcp_service_account]` in your secrets.toml. See setup instructions in the sidebar.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Authentication failed: {e}")
        st.stop()


@st.cache_data(ttl=60, show_spinner=False)
def load_worksheet(sheet_url: str, worksheet_name: str) -> pd.DataFrame:
    """
    Load a worksheet by name from a Google Sheet URL.
    Returns an empty DataFrame on any error, with a descriptive message.
    """
    client = get_gspread_client()
    try:
        spreadsheet = client.open_by_url(sheet_url)
    except gspread.exceptions.APIError as e:
        st.error(f"❌ Could not open spreadsheet. Check the URL and sharing permissions. Details: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Unexpected error opening spreadsheet: {e}")
        return pd.DataFrame()

    # List available tabs for better debugging
    available = [ws.title for ws in spreadsheet.worksheets()]

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        st.warning(
            f"⚠️ Worksheet **'{worksheet_name}'** not found. "
            f"Available tabs: {', '.join(f'`{t}`' for t in available)}"
        )
        return pd.DataFrame()

    try:
        records = worksheet.get_all_records(numericise_ignore=['all'])
        if not records:
            st.info(f"ℹ️ Worksheet **'{worksheet_name}'** is empty — add some data rows.")
            return pd.DataFrame()
        df = pd.DataFrame(records)
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"❌ Error reading worksheet '{worksheet_name}': {e}")
        return pd.DataFrame()


def safe_float(val):
    """Convert a value to float, stripping % signs and commas."""
    try:
        return float(str(val).replace('%', '').replace(',', '').strip())
    except (ValueError, TypeError):
        return 0.0


def append_to_worksheet(sheet_url: str, worksheet_name: str, row: list):
    """Append a single row to a worksheet."""
    client = get_gspread_client()
    try:
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.worksheet(worksheet_name)
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"❌ Failed to write to sheet: {e}")
        return False


# ─────────────────────────────────────────────
# SHEET URL — read from secrets or let user input
# ─────────────────────────────────────────────
try:
    SHEET_URL = st.secrets["sheet_url"]
except KeyError:
    SHEET_URL = None

if not SHEET_URL:
    st.warning("⚠️ No `sheet_url` found in secrets.toml. Enter your Google Sheet URL below to continue.")
    SHEET_URL = st.text_input("Google Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/...")
    if not SHEET_URL:
        st.stop()


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
col_title, col_refresh = st.columns([5, 1])
with col_title:
    st.markdown("## 🌲 TSX Wealth Tracker")
    st.caption(f"Last refreshed: {datetime.now().strftime('%b %d, %Y  %I:%M %p')}")
with col_refresh:
    st.write("")
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

st.divider()

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊 Market Overview", "💼 Portfolio Tracker"])


# ══════════════════════════════════════════════
# TAB 1 — MARKET OVERVIEW
# ══════════════════════════════════════════════
with tab1:
    st.subheader("S&P/TSX Composite & Sector Indices")

    with st.spinner("Loading market data..."):
        market_df = load_worksheet(SHEET_URL, "MarketData")

    if market_df.empty:
        st.info("💡 **Expected columns in your `MarketData` sheet:** `Index Name` | `Ticker` | `Price` | `Change` | `Pct_Change`")
        st.code(
            "Index Name        | Ticker            | Price    | Change | Pct_Change\n"
            "TSX Composite     | INDEXTSI:OSPTX    | =GOOGLEFINANCE(...) | ...  | ...\n"
            "Financials        | INDEXTSI:STFINL   | ...      | ...    | ...",
            language="text"
        )
    else:
        # Normalize column names (case-insensitive)
        col_map = {c.lower().replace(' ', '_'): c for c in market_df.columns}

        required = ['index_name', 'ticker', 'price', 'pct_change']
        missing = [r for r in required if r not in col_map]
        if missing:
            st.error(
                f"❌ Missing columns in MarketData: **{', '.join(missing)}**. "
                f"Found columns: {list(market_df.columns)}"
            )
        else:
            # Standardize to known names
            market_df = market_df.rename(columns={
                col_map.get('index_name', 'Index Name'): 'Index Name',
                col_map.get('ticker', 'Ticker'): 'Ticker',
                col_map.get('price', 'Price'): 'Price',
                col_map.get('change', 'Change'): 'Change',
                col_map.get('pct_change', 'Pct_Change'): 'Pct_Change',
            })

            market_df['Price'] = market_df['Price'].apply(safe_float)
            market_df['Pct_Change'] = market_df['Pct_Change'].apply(safe_float)

            # TSX Composite highlight
            tsx = market_df[market_df['Ticker'].astype(str).str.upper() == 'INDEXTSI:OSPTX']
            if not tsx.empty:
                row = tsx.iloc[0]
                pct = row['Pct_Change']
                delta_color = "🟢" if pct >= 0 else "🔴"
                st.markdown(
                    f"""<div class="metric-card">
                        <div style="font-size:0.85rem;color:#555;font-weight:500;">S&P/TSX COMPOSITE INDEX</div>
                        <div style="font-size:2.2rem;font-weight:700;color:#1b5e20;">{row['Price']:,.2f}</div>
                        <div style="font-size:1rem;color:{'#2e7d32' if pct >= 0 else '#c62828'};">
                            {delta_color} {pct:+.2f}% today
                        </div>
                    </div>""",
                    unsafe_allow_html=True
                )

            st.divider()
            st.markdown("#### TSX Sector Indices")

            sectors = market_df[market_df['Ticker'].astype(str).str.upper() != 'INDEXTSI:OSPTX']

            if not sectors.empty:
                cols = st.columns(3)
                for i, (_, row) in enumerate(sectors.iterrows()):
                    pct = row['Pct_Change']
                    with cols[i % 3]:
                        st.metric(
                            label=row['Index Name'],
                            value=f"{row['Price']:,.2f}",
                            delta=f"{pct:+.2f}%"
                        )

                # Bar chart of sector performance
                st.divider()
                st.markdown("#### Sector Performance Chart")
                fig = go.Figure(go.Bar(
                    x=sectors['Index Name'],
                    y=sectors['Pct_Change'],
                    marker_color=['#2e7d32' if v >= 0 else '#c62828' for v in sectors['Pct_Change']],
                    text=[f"{v:+.2f}%" for v in sectors['Pct_Change']],
                    textposition='outside'
                ))
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    yaxis_title="% Change",
                    xaxis_title="",
                    height=380,
                    margin=dict(t=20, b=40),
                    font=dict(family="Inter")
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No sector data rows found (only the composite index was detected).")


# ══════════════════════════════════════════════
# TAB 2 — PORTFOLIO TRACKER
# ══════════════════════════════════════════════
with tab2:
    st.subheader("Personal Portfolio")

    with st.spinner("Loading portfolio..."):
        portfolio_df = load_worksheet(SHEET_URL, "Portfolio")

    if portfolio_df.empty:
        st.info(
            "💡 **Expected columns in your `Portfolio` sheet:** "
            "`Symbol` | `Sector` | `Qty` | `Avg Price` | `Current Price` | `Market Value` | `Cost Basis`"
        )
        st.code(
            "Symbol | Sector     | Qty | Avg Price | Current Price              | Market Value   | Cost Basis\n"
            "TSE:TD | Financials | 10  | 85.00     | =GOOGLEFINANCE(A2,\"price\") | =C2*E2         | =C2*D2",
            language="text"
        )
    else:
        # Normalize columns
        portfolio_df.columns = portfolio_df.columns.str.strip()
        num_cols = ['Qty', 'Avg Price', 'Current Price', 'Market Value', 'Cost Basis']
        for col in num_cols:
            if col in portfolio_df.columns:
                portfolio_df[col] = portfolio_df[col].apply(safe_float)

        # Check required columns
        required_p = ['Cost Basis', 'Market Value']
        missing_p = [c for c in required_p if c not in portfolio_df.columns]
        if missing_p:
            st.error(f"❌ Missing columns in Portfolio sheet: **{', '.join(missing_p)}**. Found: {list(portfolio_df.columns)}")
        else:
            total_inv = portfolio_df['Cost Basis'].sum()
            current_val = portfolio_df['Market Value'].sum()
            total_pnl = current_val - total_inv
            pnl_pct = (total_pnl / total_inv * 100) if total_inv != 0 else 0

            # Summary metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("💰 Total Invested", f"${total_inv:,.2f}")
            m2.metric("📈 Current Value", f"${current_val:,.2f}")
            m3.metric(
                "💹 Total P&L",
                f"${total_pnl:,.2f}",
                f"{pnl_pct:+.2f}%"
            )

            st.divider()
            v1, v2 = st.columns([1, 1])

            with v1:
                st.markdown("#### Sector Allocation")
                if 'Sector' in portfolio_df.columns:
                    fig_pie = px.pie(
                        portfolio_df,
                        values='Market Value',
                        names='Sector',
                        color_discrete_sequence=px.colors.sequential.Greens_r,
                        hole=0.45
                    )
                    fig_pie.update_layout(
                        showlegend=True,
                        margin=dict(t=10, b=10),
                        font=dict(family="Inter"),
                        paper_bgcolor='white'
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.warning("No 'Sector' column found in Portfolio sheet.")

            with v2:
                st.markdown("#### Holdings Detail")
                display_cols = [c for c in ['Symbol', 'Sector', 'Qty', 'Avg Price', 'Current Price', 'Market Value', 'Cost Basis']
                                if c in portfolio_df.columns]
                st.dataframe(
                    portfolio_df[display_cols].style.format({
                        'Qty': '{:,.2f}',
                        'Avg Price': '${:,.2f}',
                        'Current Price': '${:,.2f}',
                        'Market Value': '${:,.2f}',
                        'Cost Basis': '${:,.2f}',
                    }),
                    use_container_width=True,
                    height=320
                )

            # Gain/Loss per holding bar chart
            if 'Symbol' in portfolio_df.columns:
                st.divider()
                st.markdown("#### Gain / Loss per Holding")
                portfolio_df['P&L'] = portfolio_df['Market Value'] - portfolio_df['Cost Basis']
                portfolio_df['P&L %'] = (portfolio_df['P&L'] / portfolio_df['Cost Basis'] * 100).round(2)

                fig_bar = go.Figure(go.Bar(
                    x=portfolio_df['Symbol'],
                    y=portfolio_df['P&L %'],
                    marker_color=['#2e7d32' if v >= 0 else '#c62828' for v in portfolio_df['P&L %']],
                    text=[f"{v:+.1f}%" for v in portfolio_df['P&L %']],
                    textposition='outside'
                ))
                fig_bar.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    yaxis_title="% Gain / Loss",
                    height=320,
                    margin=dict(t=20, b=20),
                    font=dict(family="Inter")
                )
                st.plotly_chart(fig_bar, use_container_width=True)


# ─────────────────────────────────────────────
# SIDEBAR — Add Transaction
# ─────────────────────────────────────────────
st.sidebar.markdown("## ➕ Add Transaction")
st.sidebar.divider()

with st.sidebar:
    ticker = st.text_input("Ticker (e.g. TSE:TD)").upper().strip()
    qty = st.number_input("Quantity", min_value=0.1, step=0.1, format="%.2f")
    price = st.number_input("Purchase Price ($)", min_value=0.01, format="%.2f")
    sector = st.selectbox("Sector", [
        "Financials", "Energy", "Materials", "Industrials",
        "Technology", "Telecom", "Utilities", "Health Care", "Real Estate", "Consumer"
    ])
    date = st.date_input("Transaction Date")

    if st.button("Log Transaction"):
        if not ticker:
            st.error("Please enter a ticker symbol.")
        else:
            cost_basis = qty * price
            # Append row: Symbol, Sector, Qty, Avg Price, Current Price (formula), Market Value (formula), Cost Basis, Date
            new_row = [
                ticker,
                sector,
                qty,
                price,
                f'=GOOGLEFINANCE("{ticker}","price")',
                f"=C{{row}}*E{{row}}",   # placeholder; gspread appends to next available row
                cost_basis,
                str(date)
            ]
            # Use a simpler row without self-referencing formulas
            simple_row = [ticker, sector, qty, price, f'=GOOGLEFINANCE("{ticker}","price")', "", cost_basis, str(date)]
            if append_to_worksheet(SHEET_URL, "Portfolio", simple_row):
                st.success(f"✅ {ticker} logged!")
                st.info("Refresh to see updated data. Set `=C{row}*E{row}` in Market Value column manually or via sheet formula.")
                st.cache_data.clear()

    st.divider()
    st.markdown("#### 🛠️ Setup Checklist")
    st.markdown("""
- ✅ Share sheet with service account email  
- ✅ Tab named exactly `MarketData`  
- ✅ Tab named exactly `Portfolio`  
- ✅ `secrets.toml` has `[gcp_service_account]` block  
- ✅ `secrets.toml` has `sheet_url = "https://..."`
    """)

    st.divider()
    st.caption("Data may be delayed up to 20 min via GOOGLEFINANCE.")
