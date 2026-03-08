import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path

st.set_page_config(page_title="Franchise Difference Heatmap", layout="wide")

st.title("Franchise Difference Heatmap")
st.write(
	"Compare franchises across years with a heatmap. "
	"Click a square to see the yearly breakdown below."
)

APP_DIR = Path(__file__).parent
DEFAULT_CSV_PATH = APP_DIR / "win_diff.csv"

@st.cache_data
def load_data(csv_path_str: str) -> pd.DataFrame:
	path_obj = Path(csv_path_str)
	df = pd.read_csv(path_obj)
	df.columns = [c.strip() for c in df.columns]

	column_map = {}
	for col in df.columns:
		lower = col.lower().replace("-", " ").replace("_", " ").strip()
		if lower in ["year id", "yearid", "year"]:
			column_map[col] = "Year ID"
		elif lower in ["franchid 1", "franchid1"]:
			column_map[col] = "franchid_1"
		elif lower in ["franchid 2", "franchid2"]:
			column_map[col] = "franchid_2"
		elif lower in ["abs differnce", "abs difference", "difference", "abs diff"]:
			column_map[col] = "abs differnce"
		elif lower in ["wins 1", "win 1", "w 1", "wins1", "win1", "w1"]:
			column_map[col] = "wins_1"
		elif lower in ["losses 1", "loss 1", "l 1", "losses1", "loss1", "l1"]:
			column_map[col] = "losses_1"
		elif lower in ["wins 2", "win 2", "w 2", "wins2", "win2", "w2"]:
			column_map[col] = "wins_2"
		elif lower in ["losses 2", "loss 2", "l 2", "losses2", "loss2", "l2"]:
			column_map[col] = "losses_2"

	df = df.rename(columns=column_map)
	required_cols = ["Year ID", "franchid_1", "franchid_2", "abs differnce"]
	missing = [c for c in required_cols if c not in df.columns]
	if missing:
		raise ValueError(f"Missing required columns: {missing}")

	df["Year ID"] = pd.to_numeric(df["Year ID"], errors="coerce")
	df["abs differnce"] = pd.to_numeric(df["abs differnce"], errors="coerce")

	for col in ["wins_1", "losses_1", "wins_2", "losses_2"]:
		if col in df.columns:
			df[col] = pd.to_numeric(df[col], errors="coerce")

	df["franchid_1"] = df["franchid_1"].astype(str).str.strip()
	df["franchid_2"] = df["franchid_2"].astype(str).str.strip()
	df = df.dropna(subset=["Year ID", "franchid_1", "franchid_2", "abs differnce"])
	df["Year ID"] = df["Year ID"].astype(int)
	return df


def build_team_year_records(df: pd.DataFrame) -> pd.DataFrame:
	records = []

	if {"wins_1", "losses_1"}.issubset(df.columns):
		part_1 = df[["Year ID", "franchid_1", "wins_1", "losses_1"]].rename(
			columns={"franchid_1": "team", "wins_1": "wins", "losses_1": "losses"}
		)
		records.append(part_1)

	if {"wins_2", "losses_2"}.issubset(df.columns):
		part_2 = df[["Year ID", "franchid_2", "wins_2", "losses_2"]].rename(
			columns={"franchid_2": "team", "wins_2": "wins", "losses_2": "losses"}
		)
		records.append(part_2)

	if not records:
		return pd.DataFrame()

	team_year = pd.concat(records, ignore_index=True)
	team_year = team_year.dropna(subset=["wins", "losses"])
	team_year = (
		team_year.groupby(["Year ID", "team"], as_index=False)[["wins", "losses"]]
		.first()
	)
	team_year["games"] = team_year["wins"] + team_year["losses"]
	team_year["win_pct"] = team_year["wins"] / team_year["games"]

	team_year["teams_in_year"] = team_year.groupby("Year ID")["team"].transform("count")
	team_year = team_year.sort_values(["Year ID", "win_pct", "wins", "team"], ascending=[True, False, False, True])
	team_year["rank_in_year"] = team_year.groupby("Year ID").cumcount() + 1
	team_year["top_half_cutoff"] = (team_year["teams_in_year"] / 2).apply(lambda x: int(-(-x // 1)))
	team_year["half"] = team_year.apply(
		lambda row: "Top Half" if row["rank_in_year"] <= row["top_half_cutoff"] else "Bottom Half",
		axis=1,
	)
	return team_year


def build_metric_data(filtered: pd.DataFrame, metric_name: str):
	yearly = pd.DataFrame()
	all_teams = sorted(set(filtered["franchid_1"]).union(set(filtered["franchid_2"])))

	team_year = build_team_year_records(filtered)
	team_summary = pd.DataFrame()
	if not team_year.empty:
		team_summary = team_year[["Year ID", "team", "wins", "losses", "win_pct", "half", "rank_in_year"]].copy()

	team_summary_1 = pd.DataFrame()
	team_summary_2 = pd.DataFrame()
	if not team_summary.empty:
		team_summary_1 = team_summary.rename(columns={
			"team": "franchid_1",
			"wins": "wins_1_detail",
			"losses": "losses_1_detail",
			"win_pct": "win_pct_1",
			"half": "half_1",
			"rank_in_year": "rank_1",
		})
		team_summary_2 = team_summary.rename(columns={
			"team": "franchid_2",
			"wins": "wins_2_detail",
			"losses": "losses_2_detail",
			"win_pct": "win_pct_2",
			"half": "half_2",
			"rank_in_year": "rank_2",
		})

	if metric_name == "Abs difference":
		yearly = (
			filtered.groupby(["Year ID", "franchid_1", "franchid_2"], as_index=False)["abs differnce"]
			.sum()
			.rename(columns={"abs differnce": "metric_value"})
		)
		if not team_summary.empty:
			yearly = (
				yearly
				.merge(team_summary_1, on=["Year ID", "franchid_1"], how="left")
				.merge(team_summary_2, on=["Year ID", "franchid_2"], how="left")
			)
		metric_label = "Abs difference"
	else:
		if team_year.empty:
			raise ValueError(
				"Standing half mismatch needs wins/losses columns for both teams. It accepts either W1/L1/W2/L2 or wins_1/losses_1/wins_2/losses_2."
			)

		yearly = (
			filtered[["Year ID", "franchid_1", "franchid_2"]]
			.drop_duplicates()
			.merge(team_summary_1, on=["Year ID", "franchid_1"], how="left")
			.merge(team_summary_2, on=["Year ID", "franchid_2"], how="left")
		)
		yearly["metric_value"] = (yearly["half_1"] != yearly["half_2"]).astype(int)
		metric_label = "Standing half mismatch count"

	if yearly is None or yearly.empty:
		raise ValueError("No yearly data could be built from the filtered dataset.")

	agg = (
		yearly.groupby(["franchid_1", "franchid_2"], as_index=False)["metric_value"]
		.sum()
		.rename(columns={"metric_value": "total_metric_value"})
	)

	if not team_year.empty:
		pair_team_1 = (
			yearly.groupby(["franchid_1", "franchid_2"], as_index=False)[["wins_1_detail", "losses_1_detail"]]
			.sum(min_count=1)
		)
		pair_team_1["team_1_win_pct_total"] = pair_team_1["wins_1_detail"] / (pair_team_1["wins_1_detail"] + pair_team_1["losses_1_detail"])

		pair_team_2 = (
			yearly.groupby(["franchid_1", "franchid_2"], as_index=False)[["wins_2_detail", "losses_2_detail"]]
			.sum(min_count=1)
		)
		pair_team_2["team_2_win_pct_total"] = pair_team_2["wins_2_detail"] / (pair_team_2["wins_2_detail"] + pair_team_2["losses_2_detail"])

		agg = (
			agg
			.merge(pair_team_1[["franchid_1", "franchid_2", "team_1_win_pct_total"]], on=["franchid_1", "franchid_2"], how="left")
			.merge(pair_team_2[["franchid_1", "franchid_2", "team_2_win_pct_total"]], on=["franchid_1", "franchid_2"], how="left")
		)
	else:
		agg["team_1_win_pct_total"] = pd.NA
		agg["team_2_win_pct_total"] = pd.NA

	full_index = pd.MultiIndex.from_product([all_teams, all_teams], names=["franchid_1", "franchid_2"])
	agg = (
		agg.set_index(["franchid_1", "franchid_2"])
		.reindex(full_index)
		.reset_index()
	)
	agg["total_metric_value"] = agg["total_metric_value"].fillna(0)

	return yearly, agg, all_teams, metric_label


csv_path = DEFAULT_CSV_PATH
if not csv_path.exists():
	st.error(f"CSV file not found: {csv_path}")
	st.stop()

try:
	df = load_data(str(csv_path))
except Exception as e:
	st.error(str(e))
	st.stop()

if df.empty:
	st.warning("No usable rows found after cleaning the data.")
	st.stop()

years = sorted(df["Year ID"].unique().tolist())
min_year, max_year = min(years), max(years)

default_start = max(min_year, 2000)
default_end = min(max_year, 2025)
if default_start > default_end:
	default_start, default_end = min_year, max_year

st.sidebar.header("Filters")
year_range = st.sidebar.slider(
	"Year ID range",
	min_value=min_year,
	max_value=max_year,
	value=(default_start, default_end)
)

metric_name = st.sidebar.radio(
	"Metric",
	options=["Abs difference", "Standing half mismatch"],
	index=0,
)

filtered = df[(df["Year ID"] >= year_range[0]) & (df["Year ID"] <= year_range[1])].copy()
if filtered.empty:
	st.warning("No data for the selected year range.")
	st.stop()

try:
	yearly, agg, all_teams, metric_label = build_metric_data(filtered, metric_name)
except Exception as e:
	st.error(str(e))
	st.stop()

selection = alt.selection_point(name="cell_select", fields=["franchid_1", "franchid_2"], on="click", clear="dblclick")

chart = (
	alt.Chart(agg)
	.mark_rect()
	.encode(
		x=alt.X("franchid_1:N", sort=all_teams, title=None, axis=alt.Axis(labelAngle=-45)),
		y=alt.Y("franchid_2:N", sort=all_teams, title=None, axis=alt.Axis(labelOverlap=False)),
		color=alt.Color(
			"total_metric_value:Q",
			scale=alt.Scale(scheme="redblue", reverse=True),
			title=metric_label,
		),
		tooltip=[
			alt.Tooltip("franchid_1:N", title="Team"),
			alt.Tooltip("team_1_win_pct_total:Q", format=".3f", title="Win %"),
			alt.Tooltip("franchid_2:N", title="Team"),
			alt.Tooltip("team_2_win_pct_total:Q", format=".3f", title="Team 2 win %"),
			alt.Tooltip("total_metric_value:Q", format=",.2f", title=metric_label),
		],
		stroke=alt.condition(selection, alt.value("black"), alt.value(None)),
		strokeWidth=alt.condition(selection, alt.value(2), alt.value(0)),
	)
	.add_params(selection)
	.properties(height=max(600, len(all_teams) * 28), width=max(700, len(all_teams) * 28))
)

text = (
	alt.Chart(agg)
	.mark_text(baseline="middle", fontSize=11)
	.encode(
		x=alt.X("franchid_1:N", sort=all_teams),
		y=alt.Y("franchid_2:N", sort=all_teams),
		text=alt.Text("total_metric_value:Q", format=",.0f"),
		color=alt.condition(
			alt.datum.total_metric_value > agg["total_metric_value"].median(),
			alt.value("white"),
			alt.value("black"),
		),
	)
)

selection_state = st.altair_chart(chart + text, use_container_width=True, on_select="rerun", selection_mode="cell_select")



selected_points = selection_state.get("selection", {}).get("cell_select", []) if isinstance(selection_state, dict) else []

if selected_points:
	selected_team_1 = selected_points[0]["franchid_1"]
	selected_team_2 = selected_points[0]["franchid_2"]
	selected_years = yearly[
		(yearly["franchid_1"] == selected_team_1) &
		(yearly["franchid_2"] == selected_team_2)
	].sort_values("Year ID")

	st.subheader(f"Yearly breakdown: {selected_team_1} vs {selected_team_2}")

	if metric_name == "Abs difference":
		display_cols = ["Year ID", "metric_value"]
		display_df = selected_years[display_cols + ["win_pct_1", "win_pct_2"]].rename(columns={
			"metric_value": "Abs difference",
			"win_pct_1": f"{selected_team_1} win %",
			"win_pct_2": f"{selected_team_2} win %",
		})
	else:
		display_cols = [
			"Year ID",
			"metric_value",
			"half_1",
			"win_pct_1",
			"wins_1_detail",
			"losses_1_detail",
			"rank_1",
			"half_2",
			"win_pct_2",
			"wins_2_detail",
			"losses_2_detail",
			"rank_2",
		]
		display_df = selected_years[display_cols].rename(columns={
			"metric_value": "Different halves?",
			"half_1": f"{selected_team_1} half",
			"wins_1_detail": f"{selected_team_1} wins",
			"losses_1_detail": f"{selected_team_1} losses",
			"rank_1": f"{selected_team_1} rank",
			"win_pct_1": f"{selected_team_1} win %",
			"half_2": f"{selected_team_2} half",
			"wins_2_detail": f"{selected_team_2} wins",
			"losses_2_detail": f"{selected_team_2} losses",
			"rank_2": f"{selected_team_2} rank",
			"win_pct_2": f"{selected_team_2} win %",
		})

	st.dataframe(display_df, use_container_width=True)

	breakdown_chart = (
		alt.Chart(selected_years)
		.mark_bar()
		.encode(
			x=alt.X("Year ID:O", title="Year"),
			y=alt.Y("metric_value:Q", title=metric_label),
			tooltip=[alt.Tooltip("Year ID:O"), alt.Tooltip("metric_value:Q", title=metric_label)],
		)
		.properties(height=300)
	)
	st.altair_chart(breakdown_chart, use_container_width=True)
else:
	st.info("Click a square in the heatmap to see the yearly breakdown.")
