import os
import json
from dotenv import load_dotenv
load_dotenv()

# ── API Settings ────────────────────────────────────────────────────────────
GROWW_API_KEY      = os.getenv("GROWW_API_KEY", "")
GROWW_SECRET_KEY   = os.getenv("GROWW_SECRET_KEY", "")
GROWW_CLIENT_ID    = os.getenv("GROWW_CLIENT_ID", "")
GROWW_BASE_URL     = "https://api.groww.in/v1"

# ── File Paths ──────────────────────────────────────────────────────────────
SIGNALS_DB         = "data/signals.json"
TRADES_DB          = "data/trades.json"
BACKTEST_DB        = "data/backtest_results.json"
FORWARD_TEST_DB    = "data/forward_test.json"
USER_SETTINGS_FILE = "data/user_settings.json"

# ── Static Settings (For imports) ───────────────────────────────────────────
BACKTEST_START_DATE = "2024-01-01"
BACKTEST_END_DATE   = "2024-12-31"
USE_MARKET_FILTER   = True
MAX_TRADES_PER_DAY  = 2
CIRCUIT_BREAKER_PCT = 50.0

# ── DYNAMIC SETTINGS ENGINE ─────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "capital": 2000.0,
    "risk_pct": 5.0,
    "max_sl_pct": 12.0,
    "min_quality": 85,
    "vol_mult": 1.5,
    "expansion_pct": 4.0,
    "rsi_oversold": 30,
    "paper_trading": True
}

def get_settings():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(USER_SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(USER_SETTINGS_FILE, "r") as f:
            user_data = json.load(f)
            merged = DEFAULT_SETTINGS.copy()
            merged.update(user_data)
            return merged
    except:
        return DEFAULT_SETTINGS.copy()

def save_settings(new_settings):
    os.makedirs("data", exist_ok=True)
    current = get_settings()
    current.update(new_settings)
    with open(USER_SETTINGS_FILE, "w") as f:
        json.dump(current, f, indent=2)
    return current

# ── Stock Universe: Expanded Nifty 500 ──────────────────────────────────────
STOCK_UNIVERSE = [
    # --- BLUE CHIPS (NIFTY 50) ---
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "BHARTIARTL", "SBIN", "INFY", "LICI", "ITC", "HINDUNILVR",
    "LT", "BAJFINANCE", "HCLTECH", "MARUTI", "SUNPHARMA", "ADANIENT", "KOTAKBANK", "TITAN", "ONGC", "AXISBANK",
    "NTPC", "TATAMOTORS", "ADANIPORTS", "ULTRACEMCO", "ASIANPAINT", "COALINDIA", "BAJAJFINSV", "BPCL", "M&M", "JSWSTEEL",
    "TATASTEEL", "ADANIPOWER", "GRASIM", "HINDALCO", "NESTLEIND", "POWERGRID", "ADANIGREEN", "ADANITRANS", "SBILIFE", "BEL",
    "HAL", "BAJAJ-AUTO", "TRENT", "INDUSINDBK", "DLF", "EICHERMOT", "HINDZINC", "BRITANNIA", "CIPLA", "HDFCLIFE",

    # --- MIDCAP & GROWTH LEADERS ---
    "LTIM", "VBL", "TATACONSUM", "SHREECEM", "JIOFIN", "JSWENERGY", "INDIGO", "ZOMATO", "CHOLAFIN", "DRREDDY",
    "PNB", "TVSMOTOR", "HAVELLS", "UNITDSPR", "BOSCHLTD", "HEROMOTOCO", "GAIL", "ABB", "SIEMENS", "SUZLON",
    "IRFC", "SJVN", "NHPC", "HUDCO", "NBCC", "IDFCFIRSTB", "SOUTHBANK", "UCOBANK", "MAHABANK", "UNIONBANK",
    "CENTRALBK", "IEX", "RVNL", "IRCON", "TEXRAIL", "GMRINFRA", "IDEA", "YESBANK", "HFCL", "IFCI",
    "MAZDOCK", "COCHINSHIP", "GRSE", "BEML", "BDL", "HAL", "DATAPATT", "KAYNES", "SYRMA", "TEJASNET",
    "CDSL", "MCX", "BSE", "ANGELONE", "CAMS", "KFINTECH", "MOTILALOFS", "ABCAPITAL", "PFC", "RECLTD",
    "POLYCAB", "KEI", "HAVELLS", "DIXON", "AMBER", "CUMMINSIND", "THERMAX", "PRAJIND", "VOLTAS", "BLUESTARCO",
    "TATAELXSI", "KPITTECH", "PERSISTENT", "COFORGE", "MPHASIS", "ZENSARTECH", "BSOFT", "SONACOMS", "CYIENT",
    "NYKAA", "PAYTM", "POLICYBZR", "DELHIVERY", "ZOMATO", "CARTRADE", "MAPMYIND", "RATEGAIN", "NAUKRI",

    # --- DEFENSIVE & SECTORAL STRENGTH ---
    "AUROPHARMA", "LUPIN", "ALKEM", "GLENMARK", "BIOCON", "LAURUSLABS", "GRANULES", "IPCALAB", "DIVISLAB",
    "TATACHEM", "DEEPAKNTR", "AARTIIND", "SRF", "PIIND", "NAVINFLUOR", "COROMANDEL", "UPL", "GUJGASLTD",
    "DLF", "LODHA", "GODREJPROP", "OBEROIRLTY", "PHOENIXLTD", "PRESTIGE", "BRIGADE", "SOBHA",
    "VBL", "DEVYANI", "SAPPHIRE", "WESTLIFE", "CAMPUS", "METROBRAND", "BATAINDIA", "RELAXO", "TITAN",
    "PATANJALI", "AWL", "MARICO", "COLPAL", "DABUR", "GODREJCP", "TATACONSUM", "VGUARD", "CROMPTON",
    
    # --- AFFORDABLE MOMENTUM (For Students) ---
    "GTLINFRA", "JPPOWER", "RPOWER", "VIKASECO", "ALOKINDS", "TRIDENT", "INFIBEAM", "RENUKA", "HFCL", "IFCI",
    "SREEL", "SURAJEST", "TV18BRDCST", "NETWORK18", "BLS", "FIEMIND", "LUMAXIND", "GABRIEL", "KRSNAA",
    "YATHARTH", "VIJAYA", "AMIORG", "NEOGEN", "BIKAJI", "METROBRAND", "FINPIPE", "PRINCEPIPE", "GREENPANEL"
]