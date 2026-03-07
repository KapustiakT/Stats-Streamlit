import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path

st.set_page_config(page_title="Franchise Difference Heatmap", layout="wide")

st.title("Franchise Difference Heatmap")
st.write(
	"This chart is a **heatmap** of the absoulte value of MLB Teams win differences by year. "
	"Higher differnce means those teams tend to have very differnt records"
)

APP_DIR = Path(__file__).parent
DEFAULT_CSV_PATH = APP_DIR / "win_diff.csv"
DEFAULT_CSV_PATH = "win_diff.csv"

csv_path = st.sidebar.text_input("CSV file path", value=DEFAULT_CSV_PATH)

if csv_path:
	path_obj = Path(csv_path)
	if not path_obj.exists():
		st.error(f"CSV file not found: {csv_path}")
		st.stop()

	df = pd.read_csv(DEFAULT_CSV_PATH)

	# Standardize column names a bit so the app is more forgiving
	df.columns = [c.strip() for c in df.columns]
	column_map = {}
	for col in df.columns:
		lower = col.lower().replace("_", " ").strip()
		if lower in ["year id", "yearid", "year"]:
			column_map[col] = "Year ID"
		elif lower in ["franchid 1", "franchid1", "franchid_1"]:
			column_map[col] = "franchid_1"
		elif lower in ["franchid 2", "franchid2", "franchid_2"]:
			column_map[col] = "franchid_2"
		elif lower in ["abs differnce", "abs difference", "difference", "abs diff"]:
			column_map[col] = "abs differnce"

	df = df.rename(columns=column_map)

	required_cols = ["Year ID", "franchid_1", "franchid_2", "abs differnce"]
	missing = [c for c in required_cols if c not in df.columns]

	if missing:
		st.error(f"Missing required columns: {missing}")
		st.stop()

	# Clean types
	df["Year ID"] = pd.to_numeric(df["Year ID"], errors="coerce")
	df["abs differnce"] = pd.to_numeric(df["abs differnce"], errors="coerce")
	df = df.dropna(subset=["Year ID", "franchid_1", "franchid_2", "abs differnce"])

	if df.empty:
		st.warning("No usable rows found after cleaning the data.")
		st.stop()

	years = sorted(df["Year ID"].astype(int).unique().tolist())
	min_year, max_year = min(years), max(years)

	st.sidebar.header("Filters")
	year_range = st.sidebar.slider(
		"Year ID range",
		min_value=min_year,
		max_value=max_year,
		value=(min_year, max_year)
	)

	filtered = df[(df["Year ID"] >= year_range[0]) & (df["Year ID"] <= year_range[1])].copy()

	if filtered.empty:
		st.warning("No data for the selected year range.")
		st.stop()

	# Aggregate abs difference for each pair
	agg = (
		filtered.groupby(["franchid_1", "franchid_2"], as_index=False)["abs differnce"]
		.sum()
		.rename(columns={"abs differnce": "total_abs_difference"})
	)

	# Build a complete matrix so every team shows on both axes
	all_teams = sorted(set(filtered["franchid_1"].astype(str)).union(set(filtered["franchid_2"].astype(str))))
	full_index = pd.MultiIndex.from_product([all_teams, all_teams], names=["franchid_1", "franchid_2"])
	agg = (
		agg.assign(
			franchid_1=agg["franchid_1"].astype(str),
			franchid_2=agg["franchid_2"].astype(str)
		)
		.set_index(["franchid_1", "franchid_2"])
		.reindex(full_index, fill_value=0)
		.reset_index()
	)

	x_order = all_teams
	y_order = all_teams

	chart = (
		alt.Chart(agg)
		.mark_rect()
		.encode(
			x=alt.X("franchid_1:N", sort=x_order, title="franchid_1", axis=alt.Axis(labelAngle=-45)),
			y=alt.Y("franchid_2:N", sort=y_order, title="franchid_2", axis=alt.Axis(labelOverlap=False)),
			color=alt.Color(
				"total_abs_difference:Q",
				scale=alt.Scale(scheme="redblue", reverse=True),
				title="Sum of abs differnce"
			),
			tooltip=[
				alt.Tooltip("franchid_1:N"),
				alt.Tooltip("franchid_2:N"),
				alt.Tooltip("total_abs_difference:Q", format=",.2f")
			]
		)
		.properties(height=max(600, len(all_teams) * 28), width=max(700, len(all_teams) * 28))
	)

	text = (
		alt.Chart(agg)
		.mark_text(baseline="middle", fontSize=11)
		.encode(
			x=alt.X("franchid_1:N", sort=x_order),
			y=alt.Y("franchid_2:N", sort=y_order),
			text=alt.Text("total_abs_difference:Q", format=",.0f"),
			color=alt.condition(
				alt.datum.total_abs_difference > agg["total_abs_difference"].median(),
				alt.value("white"),
				alt.value("black")
			)
		)
	)

	st.altair_chart(chart + text, use_container_width=True)

	st.subheader("Aggregated data")
	st.dataframe(agg.sort_values("total_abs_difference", ascending=False), use_container_width=True)
else:
	st.info("Enter a CSV file path to begin.")

	st.code(
		"""pip install streamlit pandas altair
python -m streamlit run franchise_difference_heatmap_app.py""",
		language="bash"
	)
