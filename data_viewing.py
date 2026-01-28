import streamlit as st
from supabase import create_client
import pandas as pd
import altair as alt
from datetime import datetime

# --------------------------------------
# 1. Supabase 接続
# --------------------------------------
SUPABASE_URL = st.secrets["https://zadmkthnxgbgsipxciuf.supabase.co"]
SUPABASE_KEY = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InphZG1rdGhueGdiZ3NpcHhjaXVmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2NjMxNTEsImV4cCI6MjA1OTIzOTE1MX0.dv5vl3aZ6gcaDHi2-W3F4rT4wTrB3U1jgretX-yG_VU"]
TABLE = st.secrets["support_data"]
FIXED_TEAM = st.secrets["トーエネック"]  # ← チーム固定

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --------------------------------------
# 2. データ取得（チーム固定）
# --------------------------------------
def load_data():
    result = (
        supabase.table(TABLE)
        .select("*")
        .eq("team", FIXED_TEAM)
        .eq("is_active", True)  # 無効行除外
        .execute()
    )
    return pd.DataFrame(result.data)

df = load_data()

st.title(f"{FIXED_TEAM} サポートデータ閲覧アプリ")

# --------------------------------------
# 3. ユーザー選択UI
# --------------------------------------
athletes = sorted(df["name"].unique())
name = st.selectbox("選手を選択してください", athletes)

# 測定日範囲
min_date = pd.to_datetime(df["measurement_date"]).min()
max_date = pd.to_datetime(df["measurement_date"]).max()

start_date = st.date_input("開始日", min_value=min_date, value=min_date)
end_date = st.date_input("終了日", min_value=min_date, value=max_date)

# 項目選択
columns_candidates = [
    "fatigue_mm", "sleep_hours", "training_intensity",
    "body_mass", "spo2", "heart_rate", "ck", "tp",
    "lf_hf_ratio", "hb_conc", "vo2max_per_kg"
]
column = st.selectbox("表示する指標を選択してください", columns_candidates)

# --------------------------------------
# 4. データ抽出処理
# --------------------------------------
df["measurement_date"] = pd.to_datetime(df["measurement_date"])

mask = (
    (df["name"] == name) &
    (df["measurement_date"] >= pd.to_datetime(start_date)) &
    (df["measurement_date"] <= pd.to_datetime(end_date))
)

plot_df = df[mask][["measurement_date", column]].sort_values("measurement_date")

# --------------------------------------
# 5. グラフ表示
# --------------------------------------
if not plot_df.empty:
    st.subheader(f"{name} ： {column} の推移")

    chart = (
        alt.Chart(plot_df)
        .mark_line(point=True)
        .encode(
            x="measurement_date:T",
            y=f"{column}:Q"
        )
        .properties(height=300)
    )

    st.altair_chart(chart, use_container_width=True)

    # 平均値
    mean_val = plot_df[column].mean()
    st.metric(label=f"{column} の平均値", value=round(mean_val, 2))
else:
    st.info("指定期間のデータがありません。")

