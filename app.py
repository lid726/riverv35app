import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="存股App v3.3", layout="wide")

# =========================
# 🧯 安全數值轉換（核心）
# =========================
def safe_float(x, default=0.0):
    try:
        if x is None:
            return default
        if isinstance(x, pd.Series):
            x = x.iloc[0]
        if isinstance(x, (list, tuple)):
            x = x[0]
        return float(x)
    except:
        return default


# =========================
# 🧼 資料清洗
# =========================
def clean_data(df):
    df = df.copy()

    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna(how="all")

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.dropna()


# =========================
# 📈 RSI
# =========================
def calc_rsi(series, period=14):
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50)


# =========================
# 📊 KD
# =========================
def calc_kd(df, n=9):
    low_min = df["Low"].rolling(n).min()
    high_max = df["High"].rolling(n).max()

    denom = (high_max - low_min).replace(0, np.nan)
    rsv = (df["Close"] - low_min) / denom * 100

    k = rsv.ewm(com=2).mean()
    d = k.ewm(com=2).mean()

    return k.fillna(50), d.fillna(50)


# =========================
# 📦 載入資料（穩定層）
# =========================
@st.cache_data
def load_stock(stock):
    try:
        df = yf.download(stock, period="6mo", progress=False, auto_adjust=False)
        return clean_data(df)
    except:
        return pd.DataFrame()


# =========================
# 📱 UI
# =========================
st.title("📊 存股分析 App v3.3（人生像河流）")

stock = st.text_input("輸入股票代號（2330.TW / AAPL）")

if st.button("🚀 開始分析"):

    df = load_stock(stock)

    if df.empty or "Close" not in df.columns:
        st.error("❌ 無法取得資料")
        st.stop()

    # =========================
    # 📊 指標
    # =========================
    df["MA60"] = df["Close"].rolling(60).mean()
    df["RSI"] = calc_rsi(df["Close"])
    df["K"], df["D"] = calc_kd(df)

    # =========================
    # 🔒 安全取值
    # =========================
    price = safe_float(df["Close"].iloc[-1])
    ma60 = safe_float(df["MA60"].iloc[-1])
    rsi = safe_float(df["RSI"].iloc[-1])
    k = safe_float(df["K"].iloc[-1])
    d = safe_float(df["D"].iloc[-1])

    # =========================
    # 💰 基本面
    # =========================
    try:
        ticker = yf.Ticker(stock)
        info = ticker.info or {}
    except:
        info = {}

    div_yield = safe_float(info.get("dividendYield"))
    pe = safe_float(info.get("trailingPE"))

    # =========================
    # ⭐ 評分系統
    # =========================
    score = 0

    if price > ma60:
        score += 30
    if rsi < 40:
        score += 20
    if k < 30 and d < 30:
        score += 20
    if div_yield > 0.03:
        score += 20
    if 0 < pe < 20:
        score += 10

    # =========================
    # 📱 KPI
    # =========================
    st.subheader(f"📊 {stock}")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("💰 股價", f"{price:.2f}")
    c2.metric("📉 MA60", f"{ma60:.2f}")
    c3.metric("📈 RSI", f"{rsi:.2f}")
    c4.metric("⭐ 評分", f"{score}/100")

    # =========================
    # 🎯 買賣訊號
    # =========================
    st.subheader("🎯 買賣訊號")

    if price > ma60 and rsi < 40:
        signal = "🟢 低檔布局區（趨勢+超賣）"
    elif price > ma60:
        signal = "📈 多頭趨勢（續抱/分批）"
    elif rsi > 70:
        signal = "🔴 過熱區（避免追高）"
    elif price < ma60:
        signal = "📉 空頭區（保守）"
    else:
        signal = "🟡 盤整區（觀望）"

    st.info(signal)

    # =========================
    # 📊 圖表
    # =========================
    st.subheader("📈 趨勢")
    st.line_chart(df[["Close", "MA60"]])

    # ➕ 新增：趨勢說明
    st.markdown("### 🧠 趨勢說明")
    st.write("• 股價 > MA60 → 偏多頭")
    st.write("• 股價 < MA60 → 偏空頭")
    st.write("• MA60 = 中期趨勢基準")

    col1, col2 = st.columns(2)

    with col1:
        st.line_chart(df["RSI"])

        # ➕ 新增：RSI說明
        st.markdown("### 🧠 RSI 說明")
        st.write("• RSI > 70 → 過熱（可能回檔）")
        st.write("• RSI < 30 → 超賣（可能反彈）")
        st.write("• 50附近 → 無明確趨勢")

    with col2:
        st.line_chart(df[["K", "D"]])

        # ➕ 新增：KD說明
        st.markdown("### 🧠 KD 說明")
        st.write("• K 上穿 D → 短線轉強（黃金交叉）")
        st.write("• K 下穿 D → 短線轉弱（死亡交叉）")
        st.write("• 高檔鈍化 → 可能回檔")

    # =========================
    # 💰 配息資訊
    # =========================
    st.subheader("💰 配息 / 殖利率")

    st.write(f"💵 殖利率：{div_yield*100:.2f}%")
    st.write(f"📊 本益比：{pe:.2f}" if pe > 0 else "📊 本益比：無資料")

    # =========================
    # ➕ 新增：評分系統說明
    # =========================
    st.markdown("### 🧠 評分系統說明")

    st.write("📊 評分組成如下：")
    st.write("• 30分 → 股價 > MA60（多頭）")
    st.write("• 20分 → RSI < 40（低檔）")
    st.write("• 20分 → KD 低檔區")
    st.write("• 20分 → 殖利率 > 3%")
    st.write("• 10分 → 本益比合理（0~20）")

    st.write("📌 80分以上：適合存股")
    st.write("📌 50~80分：觀察區")
    st.write("📌 50分以下：保守")

    # =========================
    # 📈 配息資訊
    # =========================
    try:
        divs = ticker.dividends

        if divs is not None and not divs.empty:
            divs = divs.tail(10)

            st.write("📈 最近配息紀錄")
            st.dataframe(divs)

            yearly = divs.groupby(divs.index.year).sum()
            latest_year = yearly.index.max()

            st.write(f"📊 今年配息總額：約 {yearly.loc[latest_year]:.2f}")
        else:
            st.write("📉 無配息資料")
    except:
        st.write("📉 配息資料無法取得")