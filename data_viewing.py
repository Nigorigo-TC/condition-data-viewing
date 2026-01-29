import streamlit as st
from supabase import create_client
import pandas as pd
import altair as alt

# -----------------------------
# 1) Supabase 接続
# -----------------------------
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
table_name   = st.secrets["SUPABASE_TABLE"]
fixed_team   = st.secrets["FIXED_TEAM"]

supabase = create_client(supabase_url, supabase_key)

# -----------------------------
# 2) データ取得（チーム固定）
# -----------------------------
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

if df.empty:
    st.warning("Supabaseからデータが取得できませんでした（0件）。")
    st.stop()

# 測定日は Timestamp に統一
df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
df = df.dropna(subset=["measurement_date"])

# -----------------------------
# 3) 指標名（日本語 ↔ Supabase列名）
# -----------------------------
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
    # ★ここ重要：Supabaseの列名は lf_hf_ratio のような形が普通
    "LF/HF": "lf_hf_ratio",
    "ヘモグロビン濃度": "hb_conc",
    "総ヘモグロビン量": "hbmass",
    "総ヘモグロビン量/体重": "hbmass_per_kg",
    "推定VO2max/体重": "vo2max_per_kg",
    "蛋白": "pro",
    "クレアチニン": "cre",
    "pH": "ph",          # ★Supabase側が "pH" なら "pH" に戻してください
    "尿比重": "sg",
    "その他": "another",
    "備考": "remarks",
}

# -----------------------------
# 4) 軸設定（項目ごと）
#    y_domain: (min,max) or None（自動）
#    y_zero:   0起点にするか
# -----------------------------
axis_config = {
    # mm系（0-100固定）
    "全般的な体調（mm）": {"y_domain": (0, 100), "y_zero": True},
    "疲労感（mm）": {"y_domain": (0, 100), "y_zero": True},
    "睡眠の深さ（mm）": {"y_domain": (0, 100), "y_zero": True},
    "食欲（mm）": {"y_domain": (0, 100), "y_zero": True},
    "故障の程度（mm）": {"y_domain": (0, 100), "y_zero": True},
    "練習強度（mm）": {"y_domain": (0, 100), "y_zero": True},

    # 時間・距離など（例。必要なら調整）
    "睡眠時間（h）": {"y_domain": (0, 12), "y_zero": True},
    "トレーニング時間（min）": {"y_domain": (0, 300), "y_zero": True},
    "走行距離（km）": {"y_domain": (0, 50), "y_zero": True},

    # 生理指標の例
    "SpO2（%）": {"y_domain": (70, 100), "y_zero": False},
    "心拍数（bpm）": {"y_domain": (30, 220), "y_zero": False},
    "体温（℃）": {"y_domain": (34, 41), "y_zero": False},

    # 体重・血液などは個人差大 → 基本は自動（None）
    "体重（kg）": {"y_domain": None, "y_zero": False},
    "体重変化率（%）": {"y_domain": None, "y_zero": True},
    "sRPE": {"y_domain": None, "y_zero": True},
    "RPE": {"y_domain": (0, 10), "y_zero": True},
    "d-ROMs": {"y_domain": None, "y_zero": False},
    "BAP": {"y_domain": None, "y_zero": False},
    "BAP/d-ROMs": {"y_domain": None, "y_zero": False},
    "CK": {"y_domain": None, "y_zero": False},
    "TP": {"y_domain": None, "y_zero": False},
    "HF": {"y_domain": None, "y_zero": True},
    "LF": {"y_domain": None, "y_zero": True},
    "LF/HF": {"y_domain": None, "y_zero": True},
    "ヘモグロビン濃度": {"y_domain": None, "y_zero": False},
    "総ヘモグロビン量": {"y_domain": None, "y_zero": False},
    "総ヘモグロビン量/体重": {"y_domain": None, "y_zero": False},
    "推定VO2max/体重": {"y_domain": None, "y_zero": False},
    "蛋白": {"y_domain": None, "y_zero": False},
    "クレアチニン": {"y_domain": None, "y_zero": False},
    "pH": {"y_domain": (4, 9), "y_zero": False},   # 尿pHならこのくらい
    "尿比重": {"y_domain": (1.000, 1.040), "y_zero": False},
    # 文字列系（notes/remarks/another/stool_form）はグラフ対象外にするのが安全
}

# X軸表示
x_axis_format = "%Y-%m-%d"

# -----------------------------
# 5) 選手選択（最大5人）
# -----------------------------
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

df_sel = df[df["name"].isin(selected_names)].copy()

# -----------------------------
# 6) 期間選択（選択された選手の測定日候補）
# -----------------------------
available_dates = sorted(df_sel["measurement_date"].dt.date.unique())
if len(available_dates) == 0:
    st.warning("選択した選手の測定日データがありません。")
    st.stop()

start_date = st.selectbox("開始日（測定日から選択）", available_dates, index=0)
end_date   = st.selectbox("終了日（測定日から選択）", available_dates, index=len(available_dates) - 1)

if start_date > end_date:
    st.error("開始日が終了日より後になっています。選び直してください。")
    st.stop()

# -----------------------------
# 7) 指標選択（日本語）
# -----------------------------
metric_ja = st.selectbox("表示する指標を選択してください", options=list(metric_dict.keys()))
column = metric_dict[metric_ja]

# 文字列系を選んだ場合のガード（グラフ化不可）
non_numeric_cols = {"notes", "remarks", "another", "stool_form"}
if column in non_numeric_cols:
    st.warning("この項目は文字データのため、折れ線グラフ表示に向きません。別の項目を選んでください。")
    st.stop()

# 数値化（安全策：数値にならない値は NaN）
df_sel[column] = pd.to_numeric(df_sel[column], errors="coerce")

# -----------------------------
# 8) データ抽出（期間で絞る）
# -----------------------------
start_ts = pd.Timestamp(start_date)
end_ts   = pd.Timestamp(end_date)

mask = (
    (df_sel["measurement_date"] >= start_ts) &
    (df_sel["measurement_date"] <= end_ts)
)

plot_df = df_sel.loc[mask, ["measurement_date", "name", column]].dropna().sort_values(["name", "measurement_date"])

# -----------------------------
# 9) グラフ表示（色＝選手、項目ごとに縦軸設定）
# -----------------------------
if plot_df.empty:
    st.info("指定期間のデータがありません。")
    st.stop()

cfg = axis_config.get(metric_ja, {"y_domain": None, "y_zero": False})
y_domain = cfg.get("y_domain", None)
y_zero   = cfg.get("y_zero", False)

y_scale = alt.Scale(domain=y_domain, zero=y_zero) if y_domain else alt.Scale(zero=y_zero)

st.subheader(f"{', '.join(selected_names)} ： {metric_ja} の推移")

chart = (
    alt.Chart(plot_df)
    .mark_line(point=True)
    .encode(
        x=alt.X("measurement_date:T", title="測定日", axis=alt.Axis(format=x_axis_format)),
        y=alt.Y(f"{column}:Q", title=metric_ja, scale=y_scale),
        color=alt.Color("name:N", title="選手"),
        tooltip=[
            alt.Tooltip("name:N", title="選手"),
            alt.Tooltip("measurement_date:T", title="測定日", format=x_axis_format),
            alt.Tooltip(f"{column}:Q", title=metric_ja),
        ],
    )
    .properties(height=350)
    .interactive()
)

st.altair_chart(chart, use_container_width=True)

# -----------------------------
# 10) 平均値（選手ごと）
# -----------------------------
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

for c in ["平均値", "標準偏差", "最小値", "最大値"]:
    summary[c] = summary[c].round(2)

st.dataframe(summary, use_container_width=True)









