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

st.title(f"{fixed_team} データ（最大5人比較）")

# データが空なら終了
if df.empty:
    st.warning("Supabaseからデータが取得できませんでした（0件）。")
    st.stop()

# 測定日は Timestamp(datetime64) に統一して保持
df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
df = df.dropna(subset=["measurement_date"])

# --------------------------------------
# 指標名（日本語表示 ↔ Supabase列名）
# --------------------------------------
metric_dict = {
    "全般的な体調（mm）": "general_condition_mm", 
    "疲労感（mm）": "fatigue_mm",
    "睡眠時間（h）": "sleep_hours",
    "睡眠の深さ（mm）": "sleep_depth_mm",
    "食欲（mm）": "appetite_mm",
    "故障の程度（mm）": "injury_severity_mm",
    "練習強度（mm）": "training_intensity",
    "便の形": "stool_form",
    "走行距離（km）": "distance_km",
    "SpO2（%）": "spo2",
    "心拍数（bpm）": "heart_rate",
    "体温（℃）": "body_temp",
    "体重（kg）": "body_mass",
    "特記事項": "notes",
    "体重変化率（%）": "body_mass_change_pct",
    "sRPE": "srpe",
    "トレーニング時間（min）": "training_time_min",
    "RPE": "rpe",
    "d-ROMs": "d_roms",
    "BAP": "bap",
    "BAP/d-ROMs": "bap_droms_ratio",
    "CK": "ck",
    "TP": "tp",
    "HF": "hf",
    "LF": "lf",
    "LF/HF": "lf/hf",
    "ヘモグロビン濃度": "hb_conc",
    "総ヘモグロビン量": "hbmass",
    "総ヘモグロビン量/体重": "hbmass_per_kg",
    "推定VO2max/体重": "vo2max_per_kg",
    "蛋白": "pro",
    "クレアチニン": "cre",
    "pH": "pH",
    "尿比重": "sg",
    "その他": "another",
    "備考": "remarks",
    
}

# --------------------------------------
# 3. 選手選択（最大5人）
# --------------------------------------
athletes = sorted(df["name"].dropna().unique())
if len(athletes) == 0:
    st.warning("選手名（name）が見つかりません。")
    st.stop()

selected_names = st.multiselect(
    "選手を選択してください（最大5人）",
    options=athletes,
    default=[athletes[0]] if len(athletes) > 0 else []
)

if len(selected_names) == 0:
    st.info("少なくとも1人選択してください。")
    st.stop()

if len(selected_names) > 5:
    st.error("選択は最大5人までです。5人以内にしてください。")
    st.stop()

# 選択された選手で絞ったデータ
df_sel = df[df["name"].isin(selected_names)].copy()

# --------------------------------------
# 4. 期間選択：選択された選手たちに存在する測定日（共通候補）
# --------------------------------------
available_dates = sorted(df_sel["measurement_date"].dt.date.unique())
if len(available_dates) == 0:
    st.warning("選択した選手の測定日データがありません。")
    st.stop()

start_date = st.selectbox("開始日（測定日から選択）", available_dates, index=0)
end_date   = st.selectbox("終了日（測定日から選択）", available_dates, index=len(available_dates) - 1)

if start_date > end_date:
    st.error("開始日が終了日より後になっています。選び直してください。")
    st.stop()

# --------------------------------------
# 5. 指標選択（日本語）
# --------------------------------------
metric_ja = st.selectbox(
    "表示する指標を選択してください",
    options=list(metric_dict.keys())
)
column = metric_dict[metric_ja]

# --------------------------------------
# 6. データ抽出（期間で絞る）
# --------------------------------------
start_ts = pd.Timestamp(start_date)
end_ts   = pd.Timestamp(end_date)

mask = (
    (df_sel["measurement_date"] >= start_ts) &
    (df_sel["measurement_date"] <= end_ts)
)

plot_df = df_sel.loc[mask, ["measurement_date", "name", column]].sort_values(["name", "measurement_date"])

# --------------------------------------
# 7. グラフ表示（色＝選手）
# --------------------------------------
if not plot_df.empty:
    st.subheader(f"{', '.join(selected_names)} ： {metric_ja} の推移")

    chart = (
        alt.Chart(plot_df)
        .mark_line(point=True)
        .encode(
            x="measurement_date:T",
            y=alt.Y(f"{column}:Q", title=metric_ja),
            color=alt.Color("name:N", title="選手"),
            tooltip=[
                alt.Tooltip("name:N", title="選手"),
                alt.Tooltip("measurement_date:T", title="測定日"),
                alt.Tooltip(f"{column}:Q", title=metric_ja),
            ],
        )
        .properties(height=350)
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)

    # --------------------------------------
    # 8. 平均値（選手ごと）
    # --------------------------------------
    st.subheader("平均値（選手ごと）")
    summary = (
        plot_df.groupby("name")[column]
        .agg(["count", "mean", "std", "min", "max"])
        .reset_index()
    )

    summary = summary.rename(columns={
        "name": "選手",
        "count": "測定回数",
        "mean": "平均値",
        "std": "標準偏差",
        "min": "最小値",
        "max": "最大値"
    })

    # 表示用丸め
    for c in ["平均値", "標準偏差", "最小値", "最大値"]:
        summary[c] = summary[c].round(2)

    st.dataframe(summary, use_container_width=True)

else:
    st.info("指定期間のデータがありません。")







