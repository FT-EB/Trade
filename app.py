import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Market Score Monitor",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Market Score Monitor")
st.caption(
    "主要市場データを取得し、市場環境スコアを表示します。"
    "日経225マイクロ取引の参考情報であり、売買を推奨するものではありません。"
)


WATCH_ITEMS = [
    {
        "name": "NASDAQ",
        "ticker": "^IXIC",
        "weight": 1,
        "condition": "positive",
        "reason_ok": "NASDAQが前日比プラス",
        "reason_ng": "NASDAQが前日比マイナス",
    },
    {
        "name": "S&P500",
        "ticker": "^GSPC",
        "weight": 1,
        "condition": "positive",
        "reason_ok": "S&P500が前日比プラス",
        "reason_ng": "S&P500が前日比マイナス",
    },
    {
        "name": "SOX",
        "ticker": "^SOX",
        "fallback": "SOXX",
        "weight": 1,
        "condition": "positive",
        "reason_ok": "半導体指数が前日比プラス",
        "reason_ng": "半導体指数が前日比マイナス",
    },
    {
        "name": "NVIDIA",
        "ticker": "NVDA",
        "weight": 1,
        "condition": "positive",
        "reason_ok": "NVIDIAが前日比プラス",
        "reason_ng": "NVIDIAが前日比マイナス",
    },
    {
        "name": "USDJPY",
        "ticker": "JPY=X",
        "weight": 1,
        "condition": "no_sharp_yen_strength",
        "reason_ok": "急激な円高ではない",
        "reason_ng": "円高警戒",
    },
    {
        "name": "日経平均",
        "ticker": "^N225",
        "weight": 1,
        "condition": "positive",
        "reason_ok": "日経平均が前日比プラス",
        "reason_ng": "日経平均が前日比マイナス",
    },
    {
        "name": "日経平均5日線",
        "ticker": "^N225",
        "weight": 1,
        "condition": "above_ma5",
        "reason_ok": "日経平均が5日移動平均を上回る",
        "reason_ng": "日経平均が5日移動平均を下回る",
    },
    {
        "name": "アドバンテスト",
        "ticker": "6857.T",
        "weight": 1,
        "condition": "positive",
        "reason_ok": "アドバンテストが前日比プラス",
        "reason_ng": "アドバンテストが前日比マイナス",
    },
    {
        "name": "東京エレクトロン",
        "ticker": "8035.T",
        "weight": 1,
        "condition": "positive",
        "reason_ok": "東京エレクトロンが前日比プラス",
        "reason_ng": "東京エレクトロンが前日比マイナス",
    },
    {
        "name": "日経先物",
        "ticker": "NK=F",
        "fallback": "JP225.F",
        "weight": 1,
        "condition": "positive",
        "reason_ok": "日経先物が前日比プラス",
        "reason_ng": "日経先物が前日比マイナス",
    },
]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_history(ticker: str, period: str = "7d"):
    """yfinanceから履歴データを取得（10分間キャッシュ）。"""
    try:
        data = yf.Ticker(ticker).history(period=period)
        if data is None or data.empty:
            return None
        return data
    except Exception:
        return None


def fetch_with_fallback(item):
    ticker = item["ticker"]
    data = fetch_history(ticker)

    if data is None and item.get("fallback"):
        ticker = item["fallback"]
        data = fetch_history(ticker)

    return ticker, data


def analyze_item(item):
    used_ticker, data = fetch_with_fallback(item)

    if data is None or len(data) < 2:
        return {
            "項目": item["name"],
            "ticker": used_ticker,
            "現在値": None,
            "前日終値": None,
            "前日比": None,
            "前日比率(%)": None,
            "判定": "未対応",
            "得点": 0,
            "理由": "データ取得不可",
        }

    close = data["Close"].dropna()

    if len(close) < 2:
        return {
            "項目": item["name"],
            "ticker": used_ticker,
            "現在値": None,
            "前日終値": None,
            "前日比": None,
            "前日比率(%)": None,
            "判定": "未対応",
            "得点": 0,
            "理由": "終値データ不足",
        }

    current = float(close.iloc[-1])
    previous = float(close.iloc[-2])
    diff = current - previous
    pct = (diff / previous) * 100 if previous else 0

    ok = False

    if item["condition"] == "positive":
        ok = diff > 0

    elif item["condition"] == "no_sharp_yen_strength":
        # USDJPYが-0.5%以上下落した場合は円高警戒
        ok = pct > -0.5

    elif item["condition"] == "above_ma5":
        if len(close) >= 5:
            ma5 = float(close.tail(5).mean())
            ok = current > ma5
            previous = ma5
            diff = current - ma5
            pct = (diff / ma5) * 100 if ma5 else 0
        else:
            ok = False

    score = item["weight"] if ok else 0

    return {
        "項目": item["name"],
        "ticker": used_ticker,
        "現在値": round(current, 2),
        "前日終値": round(previous, 2),
        "前日比": round(diff, 2),
        "前日比率(%)": round(pct, 2),
        "判定": "OK" if ok else "NG",
        "得点": score,
        "理由": item["reason_ok"] if ok else item["reason_ng"],
    }


def run_analysis():
    return [analyze_item(item) for item in WATCH_ITEMS]


def score_label(score: int):
    if score <= 3:
        return "警戒"
    elif score <= 5:
        return "中立"
    elif score <= 7:
        return "やや強い"
    elif score <= 9:
        return "強い"
    return "非常に強い"


def reference_lot(score: int):
    if score <= 3:
        return 0
    elif score <= 5:
        return 1
    elif score <= 7:
        return 2
    elif score <= 9:
        return 3
    return 5


# --- データ取得 ---------------------------------------------------------------
if st.button("最新データ取得", type="primary"):
    # ボタン押下時はキャッシュをクリアして強制再取得
    fetch_history.clear()
    st.session_state["last_fetch"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["results"] = run_analysis()

if "results" not in st.session_state:
    st.session_state["last_fetch"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["results"] = run_analysis()

results = st.session_state["results"]
df = pd.DataFrame(results)

total_score = int(df["得点"].sum())
max_score = sum(item["weight"] for item in WATCH_ITEMS)
confidence = round(total_score / max_score * 100, 1) if max_score else 0
lot = reference_lot(total_score)
label = score_label(total_score)

st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("総合スコア", f"{total_score} / {max_score}")

with col2:
    st.metric("市場環境", label)

with col3:
    st.metric("信頼度", f"{confidence}%")

with col4:
    st.metric("参考ロット", f"{lot}枚")

st.info(
    f"取得時刻：{st.session_state['last_fetch']} / "
    f"参考ロットはリスク確認用の目安です。実際の売買判断はご自身で行ってください。"
)

st.subheader("市場環境チェック")

display_df = df.copy()

numeric_cols = ["現在値", "前日終値", "前日比", "前日比率(%)"]
for col in numeric_cols:
    display_df[col] = pd.to_numeric(display_df[col], errors="coerce")

st.dataframe(display_df, use_container_width=True)

st.subheader("判定メモ")

ok_count = len(df[df["判定"] == "OK"])
ng_count = len(df[df["判定"] == "NG"])
unsupported_count = len(df[df["判定"] == "未対応"])

st.write(f"OK：{ok_count}件 / NG：{ng_count}件 / 未対応：{unsupported_count}件")

if total_score >= 8:
    st.success("市場環境は強めです。ロット管理と損切り設定を確認してください。")
elif total_score >= 6:
    st.warning("市場環境はやや強めです。過度なロット拡大は避けてください。")
else:
    st.error("市場環境は弱めです。無理な取引を避ける判断も重要です。")
