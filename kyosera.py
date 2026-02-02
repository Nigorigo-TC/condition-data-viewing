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

st.title(f"{fixed_team} データ")

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
    "睡眠状況": "sleep_status",
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
    "LF/HF": "lf_hf_ratio",
    "ヘモグロビン濃度": "hb_conc",
    "総ヘモグロビン量": "hbmass",
    "総ヘモグロビン量/体重": "hbmass_per_kg",
    "推定VO2max/体重": "vo2max_per_kg",
    "蛋白": "pro",
    "クレアチニン": "cre",
    "pH": "ph",
    "尿比重": "sg",
    "その他": "another",
    "備考": "remarks",
}

# -----------------------------
# 4) 軸設定（項目ごと）
# -----------------------------
axis_config = {
    "全般的な体調（mm）": {"y_domain": (0, 100), "y_zero": True, "tick_step": 10},
    "疲労感（mm）": {"y_domain": (0, 100), "y_zero": True, "tick_step": 10},
    "睡眠の深さ（mm）": {"y_domain": (0, 100), "y_zero": True, "tick_step": 10},
    "食欲（mm）": {"y_domain": (0, 100), "y_zero": True, "tick_step": 10},
    "故障の程度（mm）": {"y_domain": (0, 100), "y_zero": True, "tick_step": 10},
    "練習強度（mm）": {"y_domain": (0, 100), "y_zero": True, "tick_step": 10},

    "睡眠時間（h）": {"y_domain": (0, 12), "y_zero": True, "tick_step": 1},
    "トレーニング時間（min）": {"y_domain": (0, 300), "y_zero": True, "tick_step": 30},
    "走行距離（km）": {"y_domain": (0, 50), "y_zero": True, "tick_step": 5},

    "SpO2（%）": {"y_domain": (88, 100), "y_zero": False, "tick_step": 1},
    "心拍数（bpm）": {"y_domain": (30, 80), "y_zero": False, "tick_step": 5},
    "体温（℃）": {"y_domain": (34, 40), "y_zero": False, "tick_step": 0.5},

    "RPE": {"y_domain": (0, 10), "y_zero": True, "tick_step": 1},
    "pH": {"y_domain": (4, 9), "y_zero": False, "tick_step": 1},
    "尿比重": {"y_domain": (1.000, 1.040), "y_zero": False, "tick_step": 0.005},
}

x_axis_format = "%Y-%m-%d"

# -----------------------------
# ★テキスト（文字列）列：自動で表に出す
# -----------------------------
# 「故障の箇所」の Supabase カラム名をここで指定（要修正）
INJURY_LOC_COL = "injury_location"  # 例: "injury_site" / "injury_part" など

TEXT_COLS = [
    ("睡眠状況", "sleep_status"),
    ("故障の箇所", INJURY_LOC_COL),
    ("特記事項", "notes"),
    ("その他", "another"),
    ("備考", "remarks"),
]

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
# 6) 抽出方法：期間 or 年度+合宿回数
# -----------------------------
CAMP_COL = "camp_number"   # ★合宿回数カラム名（必要なら変更）
YEAR_COL = "fiscal_year"   # ★年度カラム名（必要なら変更）

for colname in [CAMP_COL, YEAR_COL]:
    if colname not in df_sel.columns:
        st.error(f"必要な列 '{colname}' が見つかりません。列名を確認してください。")
        st.stop()

df_sel[CAMP_COL] = pd.to_numeric(df_sel[CAMP_COL], errors="coerce")
df_sel[YEAR_COL] = pd.to_numeric(df_sel[YEAR_COL], errors="coerce")

mode = st.radio(
    "データの選び方",
    options=["期間で選ぶ", "年度＋合宿回数で選ぶ"],
    horizontal=True
)

df_period = None
filter_label = ""

if mode == "年度＋合宿回数で選ぶ":
    years = sorted(df_sel[YEAR_COL].dropna().unique())
    years = [y for y in years if y >= 2016]

    if len(years) == 0:
        st.warning("年度（2016〜）のデータがありません。")
        st.stop()

    selected_year = st.selectbox(
        "年度を選択してください",
        options=years,
        index=len(years) - 1
    )

    df_year = df_sel[df_sel[YEAR_COL] == selected_year].copy()
    camps = sorted(df_year[CAMP_COL].dropna().unique())
    camps = [c for c in camps if 1 <= c <= 7]

    if len(camps) == 0:
        st.warning("指定年度に合宿回数（1〜7）のデータがありません。")
        st.stop()

    selected_camps = st.multiselect(
        "合宿回数を選択してください（複数可）",
        options=camps,
        default=[camps[-1]]
    )

    if len(selected_camps) == 0:
        st.info("少なくとも1つ選択してください。")
        st.stop()

    df_period = df_sel[
        (df_sel[YEAR_COL] == selected_year) &
        (df_sel[CAMP_COL].isin(selected_camps))
    ].copy()

    filter_label = (
        f"年度：{int(selected_year)} / 合宿回数：{', '.join(str(int(x)) for x in selected_camps)}"
    )

else:
    available_dates = sorted(df_sel["measurement_date"].dt.date.unique())
    if len(available_dates) == 0:
        st.warning("選択した選手の測定日データがありません。")
        st.stop()

    start_date = st.selectbox("開始日（測定日から選択）", available_dates, index=0)
    end_date   = st.selectbox("終了日（測定日から選択）", available_dates, index=len(available_dates) - 1)

    if start_date > end_date:
        st.error("開始日が終了日より後になっています。選び直してください。")
        st.stop()

    start_ts = pd.Timestamp(start_date)
    end_ts   = pd.Timestamp(end_date)

    mask = (
        (df_sel["measurement_date"] >= start_ts) &
        (df_sel["measurement_date"] <= end_ts)
    )
    df_period = df_sel.loc[mask].copy()
    filter_label = f"期間：{start_date} 〜 {end_date}"

if df_period is None or df_period.empty:
    st.info("指定条件のデータがありません。")
    st.stop()

# -----------------------------
# 7) 指標選択（最大5項目） ※文字列系は選ばせない
# -----------------------------
non_numeric_cols = {"sleep_status", "notes", "another", "remarks", "stool_form", INJURY_LOC_COL}

metric_options = [k for k, v in metric_dict.items() if v not in non_numeric_cols]

selected_metrics_ja = st.multiselect(
    "表示する指標を選択してください（最大5項目）",
    options=metric_options,
    default=[metric_options[0]] if len(metric_options) > 0 else []
)

if len(selected_metrics_ja) == 0:
    st.info("少なくとも1項目選択してください。")
    st.stop()

if len(selected_metrics_ja) > 5:
    st.error("指標の選択は最大5項目までです。5項目以内にしてください。")
    st.stop()

# -----------------------------
# 8) 見出し
# -----------------------------
st.subheader(f"選手：{', '.join(selected_names)} / {filter_label}")

# -----------------------------
# 9) 指標ごとにグラフを表示（最大5枚）
# -----------------------------
for metric_ja in selected_metrics_ja:
    col = metric_dict[metric_ja]

    df_period[col] = pd.to_numeric(df_period[col], errors="coerce")

    plot_df = (
        df_period.loc[:, ["measurement_date", "name", col]]
        .dropna()
        .sort_values(["name", "measurement_date"])
    )

    if plot_df.empty:
        st.info(f"{metric_ja} は指定条件のデータがありません。")
        continue

    cfg = axis_config.get(metric_ja, {"y_domain": None, "y_zero": False, "tick_step": None})
    y_domain  = cfg.get("y_domain", None)
    y_zero    = cfg.get("y_zero", False)
    tick_step = cfg.get("tick_step", None)

    y_scale = alt.Scale(domain=y_domain, zero=y_zero) if y_domain else alt.Scale(zero=y_zero)

    y_axis = alt.Axis()
    if y_domain and tick_step:
        y_min, y_max = y_domain
        ticks = []
        v = y_min
        while v <= y_max + 1e-9:
            ticks.append(round(v, 6))
            v += tick_step
        y_axis = alt.Axis(values=ticks)

    st.markdown(f"### {metric_ja}")

    chart = (
        alt.Chart(plot_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("measurement_date:T", title="測定日", axis=alt.Axis(format=x_axis_format)),
            y=alt.Y(f"{col}:Q", title=metric_ja, scale=y_scale, axis=y_axis),
            color=alt.Color("name:N", title="選手"),
            tooltip=[
                alt.Tooltip("name:N", title="選手"),
                alt.Tooltip("measurement_date:T", title="測定日", format=x_axis_format),
                alt.Tooltip(f"{col}:Q", title=metric_ja),
            ],
        )
        .properties(height=300)
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)

    summary = (
        plot_df.groupby("name")[col]
        .agg(["count", "mean", "min", "max"])
        .reset_index()
        .rename(columns={
            "name": "選手",
            "count": "測定回数",
            "mean": "平均値",
            "min": "最小値",
            "max": "最大値",
        })
    )
    for c in ["平均値", "最小値", "最大値"]:
        summary[c] = summary[c].round(2)

    st.dataframe(summary, use_container_width=True)

# -----------------------------
# ★10) テキスト項目はグラフの下に表で出す
# -----------------------------
st.markdown("## テキスト項目（自動表示）")

text_cols_exist = [(ja, col) for (ja, col) in TEXT_COLS if col in df_period.columns]

if len(text_cols_exist) == 0:
    st.info("テキスト項目の列が見つかりません。")
else:
    show_cols = ["measurement_date", "name"] + [col for (_, col) in text_cols_exist]
    text_df = df_period.loc[:, show_cols].copy()

    # 表示用に日付を文字列へ
    text_df["measurement_date"] = text_df["measurement_date"].dt.strftime(x_axis_format)

    # 文字列の前後空白を除去
    for _, col in text_cols_exist:
        text_df[col] = text_df[col].astype(str).str.strip()
        text_df.loc[text_df[col].isin(["nan", "None", "NaT"]), col] = ""

    # テキストが全部空の行は落とす（必要なら）
    text_only_cols = [col for (_, col) in text_cols_exist]
    text_df = text_df.dropna(subset=text_only_cols, how="all")
    text_df = text_df[~(text_df[text_only_cols].apply(lambda r: all(str(x).strip() == "" for x in r), axis=1))]

    # 列名を日本語に
    rename_map = {col: ja for (ja, col) in text_cols_exist}
    text_df = text_df.rename(columns=rename_map)

    # 並び
    text_df = text_df.sort_values(["name", "measurement_date"])

    if text_df.empty:
        st.info("指定条件の範囲で、テキスト入力があるデータはありません。")
    else:
        st.dataframe(text_df, use_container_width=True)
