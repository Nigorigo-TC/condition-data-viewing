import streamlit as st
from supabase import create_client
import pandas as pd
import altair as alt
import re

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

# -----------------------------
# 2.5) 測定日と name 正規化（スペース揺れ対策）
# -----------------------------
df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
df = df.dropna(subset=["measurement_date"])

def normalize_name(x: str) -> str:
    """前後空白除去 + 全角スペース→半角 + 連続空白→1つ"""
    if pd.isna(x):
        return ""
    s = str(x).strip()
    s = s.replace("\u3000", " ")       # 全角スペース→半角
    s = re.sub(r"\s+", " ", s)         # 連続空白→1つ
    return s

# UI・抽出・凡例に使う正規化名
df["name_norm"] = df["name"].apply(normalize_name)

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
    "練習強度（mm）": "training_intensity_mm",
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
INJURY_LOC_COL = "injury_location"  # 必要なら変更

TEXT_COLS = [
    ("睡眠状況", "sleep_status"),
    ("故障の箇所", INJURY_LOC_COL),
    ("特記事項", "notes"),
    ("その他", "another"),
    ("備考", "remarks"),
]

# -----------------------------
# 5) 比較モード
# -----------------------------
compare_mode = st.radio(
    "比較モード",
    options=["複数選手比較（最大5人）", "同一選手比較"],
    horizontal=True
)

# -----------------------------
# 6) 選手選択（name揺れ対策：name_normで統一）
# -----------------------------
athletes = sorted(df["name_norm"].dropna().unique())
athletes = [a for a in athletes if str(a).strip() != ""]

if len(athletes) == 0:
    st.warning("選手名（name）が見つかりません。")
    st.stop()

if compare_mode == "複数選手比較（最大5人）":
    selected_names_norm = st.multiselect(
        "選手を選択してください（最大5人）",
        options=athletes,
        default=[athletes[0]] if len(athletes) > 0 else []
    )
    if len(selected_names_norm) == 0:
        st.info("1人以上選択してください。")
        st.stop()
    if len(selected_names_norm) > 5:
        st.error("選択は最大5人までです。")
        st.stop()
else:
    selected_name_norm = st.selectbox(
        "選手を選択してください（同一選手比較：1人）",
        options=athletes,
        index=0
    )
    selected_names_norm = [selected_name_norm]

# 抽出は name_norm で行う
df_sel = df[df["name_norm"].isin(selected_names_norm)].copy()

# 以降の既存処理（color="name" 等）を壊さないため、表示用 name を統一
df_sel["name"] = df_sel["name_norm"]

# -----------------------------
# 7) 抽出：期間 or 年度+月
# -----------------------------
YEAR_COL = "fiscal_year"
if YEAR_COL not in df_sel.columns:
    st.error(f"必要な列 '{YEAR_COL}' が見つかりません。列名を確認してください。")
    st.stop()

df_sel[YEAR_COL] = pd.to_numeric(df_sel[YEAR_COL], errors="coerce")

mode = st.radio(
    "データの選び方",
    options=["期間で選ぶ", "年度＋月で選ぶ"],
    horizontal=True
)

df_period = None
filter_label = ""

if mode == "年度＋月で選ぶ":
    years_all = sorted(df_sel[YEAR_COL].dropna().unique())
    years_all = [y for y in years_all if y >= 2016]
    if len(years_all) == 0:
        st.warning("年度（2016〜）のデータがありません。")
        st.stop()

    if compare_mode == "同一選手の年度比較（1人＋最大5年）":
        selected_years = st.multiselect(
            "年度を選択してください（最大5年）",
            options=years_all,
            default=[years_all[-1]]
        )
        if len(selected_years) == 0:
            st.info("少なくとも1つ年度を選択してください。")
            st.stop()
        if len(selected_years) > 5:
            st.error("年度の選択は最大5年までです。5年以内にしてください。")
            st.stop()

        df_year = df_sel[df_sel[YEAR_COL].isin(selected_years)].copy()

        df_year["month"] = df_year["measurement_date"].dt.month
        months = sorted(df_year["month"].dropna().unique())
        if len(months) == 0:
            st.info("指定年度に測定日のある月がありません。")
            st.stop()

        selected_months = st.multiselect(
            "月を選択してください（複数可 / 測定日が存在する月のみ）",
            options=months,
            default=[months[-1]]
        )
        if len(selected_months) == 0:
            st.info("少なくとも1つ月を選択してください。")
            st.stop()

        df_period = df_year[df_year["month"].isin(selected_months)].copy()

        years_str  = ", ".join(str(int(y)) for y in selected_years)
        months_str = ", ".join(str(int(m)) for m in selected_months)
        filter_label = f"年度：{years_str} / 月：{months_str}"

    else:
        selected_year = st.selectbox(
            "年度を選択してください",
            options=years_all,
            index=len(years_all) - 1
        )

        df_year = df_sel[df_sel[YEAR_COL] == selected_year].copy()
        if df_year.empty:
            st.info("指定年度のデータがありません。")
            st.stop()

        df_year["month"] = df_year["measurement_date"].dt.month
        months = sorted(df_year["month"].dropna().unique())
        if len(months) == 0:
            st.info("指定年度に測定日のある月がありません。")
            st.stop()

        selected_months = st.multiselect(
            "月を選択してください（複数選択可 / 測定日が存在する月のみ）",
            options=months,
            default=[months[-1]]
        )
        if len(selected_months) == 0:
            st.info("少なくとも1つ月を選択してください。")
            st.stop()

        df_period = df_year[df_year["month"].isin(selected_months)].copy()
        months_str = ", ".join(str(int(m)) for m in selected_months)
        filter_label = f"年度：{int(selected_year)} / 月：{months_str}"

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
# 8) 指標選択（最大5項目） ※文字列系は選ばせない
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
# 9) 見出し
# -----------------------------
st.subheader(f"選手：{', '.join(selected_names_norm)} / {filter_label}")

# -----------------------------
# 10) 指標ごとにグラフ
# -----------------------------
for metric_ja in selected_metrics_ja:
    col = metric_dict[metric_ja]
    df_period[col] = pd.to_numeric(df_period[col], errors="coerce")

    use_cols = ["measurement_date", "name", YEAR_COL, col]
    use_cols = [c for c in use_cols if c in df_period.columns]

    plot_df = (
        df_period.loc[:, use_cols]
        .dropna(subset=["measurement_date", col])
        .sort_values(["measurement_date"])
        .copy()
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

    if compare_mode == "同一選手の年度比較（1人＋最大5年）" and mode == "年度＋月で選ぶ":
        plot_df[YEAR_COL] = pd.to_numeric(plot_df[YEAR_COL], errors="coerce").astype("Int64")
        plot_df["month"] = pd.to_datetime(plot_df["measurement_date"], errors="coerce").dt.month.astype("Int64")
        plot_df["year_month_label"] = plot_df[YEAR_COL].astype(str) + "-" + plot_df["month"].astype(str)

        plot_df["overlay_date"] = pd.to_datetime(
            "2000-" + plot_df["measurement_date"].dt.strftime("%m-%d"),
            errors="coerce"
        )
        plot_df = plot_df.dropna(subset=["overlay_date", "year_month_label"])
        plot_df["group_key"] = plot_df["year_month_label"]

        chart = (
            alt.Chart(plot_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("overlay_date:T", title="月日", axis=alt.Axis(format="%m-%d")),
                y=alt.Y(f"{col}:Q", title=metric_ja, scale=y_scale, axis=y_axis),
                color=alt.Color("year_month_label:N", title="年度-月"),
                detail=alt.Detail("group_key:N"),
                tooltip=[
                    alt.Tooltip("year_month_label:N", title="年度-月"),
                    alt.Tooltip("measurement_date:T", title="測定日", format=x_axis_format),
                    alt.Tooltip(f"{col}:Q", title=metric_ja),
                ],
            )
            .properties(height=300)
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

        summary = (
            plot_df.groupby("year_month_label")[col]
            .agg(["count", "mean", "min", "max"])
            .reset_index()
            .rename(columns={
                "year_month_label": "年度-月",
                "count": "測定回数",
                "mean": "平均値",
                "min": "最小値",
                "max": "最大値",
            })
            .sort_values("年度-月")
        )
        for c in ["平均値", "最小値", "最大値"]:
            summary[c] = summary[c].round(2)
        st.dataframe(summary, use_container_width=True)

    else:
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
# 11) テキスト項目（自動表示）
# -----------------------------
st.markdown("## テキスト項目")

text_cols_exist = [(ja, col) for (ja, col) in TEXT_COLS if col in df_period.columns]

if len(text_cols_exist) == 0:
    st.info("テキスト項目の列が見つかりません。")
else:
    text_base_cols = ["measurement_date", "name"]
    if compare_mode == "同一選手の年度比較（1人＋最大5年）" and mode == "年度＋月で選ぶ":
        df_period["_fy"] = pd.to_numeric(df_period[YEAR_COL], errors="coerce").astype("Int64")
        df_period["_m"] = pd.to_datetime(df_period["measurement_date"], errors="coerce").dt.month.astype("Int64")
        df_period["_year_month_label"] = df_period["_fy"].astype(str) + "-" + df_period["_m"].astype(str)
        text_base_cols = ["measurement_date", "_year_month_label", "name"]

    show_cols = text_base_cols + [col for (_, col) in text_cols_exist]
    show_cols = [c for c in show_cols if c in df_period.columns]

    text_df = df_period.loc[:, show_cols].copy()
    text_df["measurement_date"] = pd.to_datetime(text_df["measurement_date"], errors="coerce").dt.strftime(x_axis_format)

    for _, col in text_cols_exist:
        if col in text_df.columns:
            text_df[col] = text_df[col].astype(str).str.strip()
            text_df.loc[text_df[col].isin(["nan", "None", "NaT"]), col] = ""

    rename_map = {col: ja for (ja, col) in text_cols_exist}
    text_df = text_df.rename(columns=rename_map)

    if "_year_month_label" in text_df.columns:
        text_df = text_df.rename(columns={"_year_month_label": "年度-月"})

    sort_cols = ["name", "measurement_date"]
    if "年度-月" in text_df.columns:
        sort_cols = ["年度-月"] + sort_cols
    text_df = text_df.sort_values(sort_cols)

    text_only_cols = [ja for (ja, col) in text_cols_exist if ja in text_df.columns]
    if len(text_only_cols) > 0:
        text_df = text_df[~(text_df[text_only_cols].apply(lambda r: all(str(x).strip() == "" for x in r), axis=1))]

    if text_df.empty:
        st.info("指定条件の範囲で、テキスト入力があるデータはありません。")
    else:
        st.dataframe(text_df, use_container_width=True)
