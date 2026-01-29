import streamlit as st
from supabase import create_client
import pandas as pd
import altair as alt

# 1. Supabase 接続
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
table_name   = st.secrets["SUPABASE_TABLE"]
fixed_team   = st.secrets["FIXED_TEAM"]

supabase = create_client(supabase_url, supabase_key)

# 2. データ取得
def load_data():
    result = (
        supabase.table(table_name)
        .select("*")
        .eq("team", fixed_team)
        .execute()
    )
    return pd.DataFrame(result.data)

df = load_data()

st.title(f"{fixed_team} データ")

# データが空なら終了
if df.empty:
    st.warning("Supabaseからデータが取得できませんでした（0件）。")
    st.stop()

# ★測定日は Timestamp(datetime64) に統一して保持（ここが重要）
df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
df = df.dropna(subset=["measurement_date"])

# --------------------------------------
# 3. ユーザー選択UI
# --------------------------------------
athletes = sorted(df["name"].dropna().unique())
if len(athletes) == 0:
    st.warning("選手名（name）が見つかりません。")
    st.stop()

name = st.selectbox("選手を選択してください", athletes)

# 測定日候補（表示用はdate）
available_dates = sorted(df["measurement_date"].dt.date.unique())
if len(available_dates) == 0:
    st.warning("測定日データがありません。")
    st.stop()

start_date = st.selectbox("開始日（測定日から選択）", available_dates, index=0)
end_date   = st.selectbox("終了日（測定日から選択）", available_dates, index=len(available_dates) - 1)

if start_date > end_date:
    st.error("開始日が終了日より後になっています。選び直してください。")
    st.stop()

columns_candidates = [
    "fatigue_mm", "sleep_hours", "training_intensity",
    "body_mass", "spo2", "heart_rate", "ck", "tp",
    "lf_hf_ratio", "hb_conc", "vo2max_per_kg"
]
column = st.selectbox("表示する指標を選択してください", columns_candidates)

# --------------------------------------
# 4. データ抽出処理
# --------------------------------------
# ★start/end も Timestamp に変換してから比較（ここが重要）
start_ts = pd.Timestamp(start_date)
end_ts   = pd.Timestamp(end_date)

mask = (
    (df["name"] == name) &
    (df["measurement_date"] >= start_ts) &
    (df["measurement_date"] <= end_ts)
)

plot_df = df.loc[mask, ["measurement_date", column]].sort_values("measurement_date")

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
            y=alt.Y(f"{column}:Q")
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)

    mean_val = plot_df[column].mean()
    st.metric(label=f"{column} の平均値", value=round(mean_val, 2))
else:
    st.info("指定期間のデータがありません。")






