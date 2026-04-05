"""
config.py — All strategy parameters in one place.
"""
import os
from dotenv import load_dotenv
load_dotenv()

# ── Groww API ─────────────────────────────────────────────────────────────────
GROWW_API_KEY    = os.getenv("GROWW_API_KEY", "")
GROWW_SECRET_KEY = os.getenv("GROWW_SECRET_KEY", "")
GROWW_CLIENT_ID  = os.getenv("GROWW_CLIENT_ID", "")
GROWW_BASE_URL   = "https://api.groww.in/v1"

# ── Capital & Risk ────────────────────────────────────────────────────────────
TRADING_CAPITAL     = float(os.getenv("TRADING_CAPITAL", 2000))
RISK_PER_TRADE_PCT  = float(os.getenv("RISK_PER_TRADE_PCT", 2))
MAX_STOP_LOSS_PCT   = float(os.getenv("MAX_STOP_LOSS_PCT", 5))
PAPER_TRADING       = os.getenv("PAPER_TRADING", "TRUE").upper() == "TRUE"

# ── Market / Index Filter ─────────────────────────────────────────────────────
INDEX_EMA_PERIOD    = 10
USE_MARKET_FILTER   = True

# ── Stage 2 (VCP strategy) ────────────────────────────────────────────────────
EMA_200_PERIOD      = 200
EMA_20_PERIOD       = 20
EMA_10_PERIOD       = 10

# ── VCP Pullback Rules ────────────────────────────────────────────────────────
PULLBACK_MIN_PCT    = 12
PULLBACK_MAX_PCT    = 20
PULLBACK_MAX_DAYS   = 30
HARD_PULLBACK_3DAY  = 20

# ── Volume Contraction ────────────────────────────────────────────────────────
VOLUME_DRY_UP_PCT   = 40

# ── Inside Bar ────────────────────────────────────────────────────────────────
EMA_PROXIMITY_PCT   = 3

# ── Exit / Trade Management ───────────────────────────────────────────────────
BREAKEVEN_R         = 2
PARTIAL_EXIT_R      = 4
AGGRESSIVE_EXIT_PCT = 40

# ── Smart Risk Guardrails ─────────────────────────────────────────────────────
MAX_TRADES_PER_DAY  = 2
MIN_QUALITY_SCORE   = 75    # lowered from 85 so scanner actually finds signals
CIRCUIT_BREAKER_PCT = 50

# ── Backtesting ───────────────────────────────────────────────────────────────
BACKTEST_START_DATE = "2024-01-01"
BACKTEST_END_DATE   = "2024-12-31"

# ── Paths ─────────────────────────────────────────────────────────────────────
LOG_FILE        = "logs/bot.log"
TRADES_DB       = "data/trades.json"
SIGNALS_DB      = "data/signals.json"
BACKTEST_DB     = "data/backtest_results.json"
FORWARD_TEST_DB = "data/forward_test.json"   # NEW: server-side forward test persistence

# ── Stock Universe (deduplicated) ─────────────────────────────────────────────
STOCK_UNIVERSE = [
    # Affordable Momentum
    "SUZLON", "IRFC", "SJVN", "NHPC", "ZOMATO", "HUDCO", "NBCC", "NTPC", "PNB",
    "IDFCFIRSTB", "SOUTHBANK", "UCOBANK", "MAHABANK", "UNIONBANK", "CENTRALBK",
    "IEX", "RVNL", "IRCON", "TEXRAIL", "GMRINFRA", "YESBANK", "HFCL",
    "IFCI", "JPPOWER", "TRIDENT", "RPOWER", "INFIBEAM",
    # Mid-Range Growth
    "TITAGARH", "BEML", "BEL", "BDL", "ASTRAMICRO", "ZENTECH", "MTARTECH",
    "DCXINDIA", "CAMS", "CDSL", "MCX", "ANGELONE", "KFINTECH",
    "ZAGGLE", "NYKAA", "DELHIVERY", "BLS", "OLECTRA", "JBMMA",
    "ASHOKLEY", "ESCORTS", "KRSNAA", "YATHARTH", "VIJAYA", "MAXHEALTH", "FORTIS",
    "NARAYANA", "NATCOPHARM", "CAPLIPOINT", "AETHER", "NEOGEN",
    "DEEPAKNTR", "AARTIIND", "BALAMINES", "ALKYLAMINE", "CAMPUS",
    "SAPPHIRE", "DEVYANI", "RBA", "WESTLIFE", "BIKAJI", "BATAINDIA",
    "SUPREMEIND", "VOLTAS", "BLUESTARCO", "VBL", "LEMONTREE",
    "NUVOCO", "GREENPANEL", "AHLUCONT", "PRINCEPIPE",
    "FUSION", "APTUS", "HOMEFIRST", "EQUITASBNK", "SURYODAY", "ABSLAMC", "360ONE",
    "ANANDRAY", "PRUDENT", "MANAPPURAM", "PFC", "RECLTD",
    "FEDERALBNK", "KARURVYSYA", "NCC", "PNCINFRA", "KNRCON",
    # High-Value Leaders
    "KAYNES", "DIXON", "AMBER", "SYRMA", "AVALON", "NEWGEN", "RATEGAIN",
    "LATENTVIEW", "DATAPATT", "MAPMYIND", "PARAS", "PGEL", "ROUTE",
    "CYIENTDLM", "KPITTECH", "TATAELXSI", "CYIENT", "PERSISTENT", "COFORGE",
    "ZENSARTECH", "SONACOMS", "BSE", "HAL", "MAZDOCK", "COCHINSHIP",
    "GRSE", "POLYCAB", "KEI", "APARINDS", "HAVELLS", "CGPOWER",
    "INOXWIND", "KPIGREEN", "PRAJIND", "THERMAX", "ELECON",
    "SCHAEFFLER", "TIMKEN", "WAAREEENER", "JSWENERGY", "TATAPOWER",
    "IREDA", "INOXGREEN", "TVSMOTOR", "EICHERMOT", "MEDANTA", "APOLLOHOSP",
    "DIVISLAB", "LAURUSLABS", "GRANULES", "NEULANDLAB", "TARSONS",
    "LUPIN", "AUROPHARMA", "CIPLA", "FINEORG", "CLEAN", "SRF",
    "PIIND", "TATACHEM", "DOMS", "TRENT", "ASTRAL", "PIDILITIND",
    "BERGERPAINT", "JKCEMENT", "CENTURYPLY", "CHOLAFIN",
    "BAJFINANCE", "SHRIRAMFIN", "MUTHOOTFIN",
    "INDUSINDBK", "HGINFRA",
]