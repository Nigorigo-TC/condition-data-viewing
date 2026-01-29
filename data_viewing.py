import streamlit as st
from supabase import create_client
import pandas as pd
import altair as alt
from datetime import datetime

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
        # .eq("is_active", True)  # カラムがないならコメントアウトのまま
        .execute()
    )
    return pd.DataFrame(result.data)

df = load_data()

st.title(f"{fixed_team} データ")

# （以下は今のコードのままでOK）


# --------------------------------------
# 3. ユーザー選択UI
# --------------------------------------
athletes = sorted(df["name"].dropna().unique())
name = st.selectbox("選手を選択してください", athletes)


# 測定日（DBに存在する日付だけ）を候補にする
df["measurement_date"] = pd.to_datetime(df["measurement_date"]).dt.date

available_dates = sorted(df["measurement_date"].dropna().unique())

if len(available_dates) == 0:
    st.warning("測定日データがありません。")
    st.stop()

# 開始日・終了日を「候補日」から選択
start_date = st.selectbox("開始日（測定日から選択）", available_dates, index=0)
end_date = st.selectbox("終了日（測定日から選択）", available_dates, index=len(available_dates)-1)

# ユーザーが開始＞終了を選んでも壊れないように補正
if start_date > end_date:
    st.error("開始日が終了日より後になっています。選び直してください。")
    st.stop()


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
mask = (
    (df["name"] == name) &
    (df["measurement_date"] >= pd.to_datetime(start_date)) &
    (df["measurement_date"] <= pd.to_datetime(end_date))
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
            y=f"{column}:Q"
        )
        .properties(height=300)
    )

    st.altair_chart(chart, use_container_width=True)

    mean_val = plot_df[column].mean()
    st.metric(label=f"{column} の平均値", value=round(mean_val, 2))
else:
    st.info("指定期間のデータがありません。")





