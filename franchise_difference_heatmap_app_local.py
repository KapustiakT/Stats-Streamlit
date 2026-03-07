import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Franchise Difference Heatmap", layout="wide")

st.title("Franchise Difference Heatmap")
st.write(
	"Upload a CSV with columns: `Year ID`, `franchid_1`, `franchid_2`, and `abs differnce`. "
	"The chart below is a **heatmap** (sometimes called a matrix heatmap)."
)

uploaded_file = st.file_uploader("win_diff.csv", type="csv")

if uploaded_file is not None:
	df = pd.read_csv(uploaded_file)

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

	# Optional: sort labels for cleaner display
	x_order = sorted(agg["franchid_1"].unique().tolist())
	y_order = sorted(agg["franchid_2"].unique().tolist())

	chart = (
		alt.Chart(agg)
		.mark_rect()
		.encode(
			x=alt.X("franchid_1:N", sort=x_order, title="franchid_1"),
			y=alt.Y("franchid_2:N", sort=y_order, title="franchid_2"),
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
		.properties(height=600)
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
	st.info("Upload your CSV to begin.")

	st.code(
		"""pip install streamlit pandas altair
streamlit run franchise_difference_heatmap_app.py""",
		language="bash"
	)
