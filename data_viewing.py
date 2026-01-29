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

# 2. データ取得（チーム固定）
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

# 測定日は Timestamp(datetime64) に統一して保持
df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
df = df.dropna(subset=["measurement_date"])

# --------------------------------------
# 3. 選手選択
# --------------------------------------
athletes = sorted(df["name"].dropna().unique())
if len(athletes) == 0:
    st.warning("選手名（name）が見つかりません。")
    st.stop()

name = st.selectbox("選手を選択してください", athletes)

# ★選手で絞ったデータ
df_ath = df[df["name"] == name].copy()

# ★この選手に存在する測定日だけ候補にする（表示用はdate）
available_dates = sorted(df_ath["measurement_date"].dt.date.unique())
if len(available_dates) == 0:
    st.warning("この選手の測定日データがありません。")
    st.stop()

start_date = st.selectbox("開始日（この選手の測定日から選択）", available_dates, index=0)
end_date   = st.selectbox("終了日（この選手の測定日から選択）", available_dates, index=len(available_dates) - 1)

if start_date > end_date:
    st.error("開始日が終了日より後になっています。選び直してください。")
    st.stop()

# --------------------------------------
# 4. 指標選択
# --------------------------------------
columns_candidates = [
    "fatigue_mm", "sleep_hours", "training_intensity",
    "body_mass", "spo2", "heart_rate", "ck", "tp",
    "lf_hf_ratio", "hb_conc", "vo2max_per_kg"
]
column = st.selectbox("表示する指標を選択してください", columns_candidates)

# --------------------------------------
# 5. データ抽出
# --------------------------------------
start_ts = pd.Timestamp(start_date)
end_ts   = pd.Timestamp(end_date)

mask = (
    (df_ath["measurement_date"] >= start_ts) &
    (df_ath["measurement_date"] <= end_ts)
)

plot_df = df_ath.loc[mask, ["measurement_date", column]].sort_values("measurement_date")

# --------------------------------------
# 6. グラフ表示
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






