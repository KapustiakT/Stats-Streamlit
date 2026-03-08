import pandas as pd

df = pd.read_csv("Teams.csv")

df = df[['franchID', 'W', 'L', 'yearID']]

df1 = df.rename(columns={'franchID': 'franchid_1', 'W': 'W1', 'L': 'L1'})
df2 = df.rename(columns={'franchID': 'franchid_2', 'W': 'W2', 'L': 'L2'})

merged = df1.merge(df2, on='yearID')

merged['abs_difference'] = (merged['W1'] - merged['W2']).abs()

result = merged[['yearID', 'franchid_1', 'franchid_2', 'abs_difference', 'W1', 'W2', 'L1', 'L2']]
result.to_csv("win_diff.csv", index=False)