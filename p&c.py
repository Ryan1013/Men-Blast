import streamlit as st
import pandas as pd
import itertools

# ----------------------------
# Helper Functions
# ----------------------------
def cricket_overs_from_balls(balls):
    overs = balls // 6
    balls_remaining = balls % 6
    return float(f"{overs}.{balls_remaining}")

def cricket_balls_from_overs(overs):
    parts = str(overs).split('.')
    if len(parts) == 1:
        return int(parts[0]) * 6
    return int(parts[0]) * 6 + int(parts[1])

def calculate_nrr(runs_for, balls_faced, runs_against, balls_bowled):
    rr_for = runs_for / (balls_faced / 6)
    rr_against = runs_against / (balls_bowled / 6)
    return rr_for - rr_against

# ----------------------------
# Load Current Table
# ----------------------------
current_table = pd.read_csv("current_table.csv")
current_table = current_table.fillna(0)

# ----------------------------
# App UI
# ----------------------------
st.title("Steelbacks Qualification Permutation Simulator")
st.markdown("---")

# Display current standings
st.markdown("### 📊 Current Table")
st.dataframe(current_table.style.format({
    "M": "{:.0f}", "W": "{:.0f}", "L": "{:.0f}", "T": "{:.0f}", "N/R": "{:.0f}", "PT": "{:.0f}", "NRR": "{:.3f}"
}))
st.markdown("---")

# Fixtures to simulate
fixtures = [
    ("17 July", "Worcestershire Rapids Men", "Notts Outlaws"),
    ("17 July", "Yorkshire Men", "Lancashire Lightning"),
    ("18 July", "Durham Cricket Men", "Northamptonshire Steelbacks Men"),
    ("18 July", "Leicestershire Foxes Men", "Yorkshire Men"),
    ("18 July", "Derbyshire Falcons Men", "Bears Men"),
    ("18 July", "Notts Outlaws", "Lancashire Lightning")
]

st.markdown("### 🧮 Predict Remaining Fixtures")
outcomes = []

for date, team1, team2 in fixtures:
    st.subheader(f"{date} - {team1} vs {team2}")
    result = st.selectbox(f"Select result for {team1} vs {team2}",
                          ["Not Played", f"{team1} Win (by runs)", f"{team2} Win (by runs)",
                           f"{team1} Win (with balls remaining)", f"{team2} Win (with balls remaining)",
                           "Tie", "No Result"], key=f"result_{team1}_{team2}")

    match_info = {"team1": team1, "team2": team2, "result": result}

    if "Win (by runs)" in result:
        margin = st.number_input("Win margin (runs)", min_value=1, max_value=200, value=20, key=f"margin_{team1}_{team2}")
        first_innings_runs = st.number_input("Runs scored by batting team (1st innings)", min_value=50, max_value=300, value=160, key=f"first_{team1}_{team2}")
        match_info.update({"margin": margin, "first_innings_runs": first_innings_runs})

    elif "Win (with balls remaining)" in result:
        balls_remain = st.number_input("Balls Remaining", min_value=1, max_value=120, value=12, key=f"balls_{team1}_{team2}")
        chasing_runs = st.number_input("Runs scored by chasing team", min_value=50, max_value=300, value=161, key=f"chase_{team1}_{team2}")
        first_innings_runs = st.number_input("Runs scored by team batting first", min_value=50, max_value=300, value=160, key=f"firstrain_{team1}_{team2}")
        match_info.update({"balls_remaining": balls_remain, "chasing_runs": chasing_runs, "first_innings_runs": first_innings_runs})

    outcomes.append(match_info)

# ----------------------------
# Process Outcomes
# ----------------------------
# Clone original table to simulate
sim_table = current_table.copy()
sim_table.set_index("Team", inplace=True)

for outcome in outcomes:
    if outcome['result'] == "Not Played":
        continue

    t1 = outcome['team1']
    t2 = outcome['team2']

    for t in [t1, t2]:
        if t not in sim_table.index:
            sim_table.loc[t] = [0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 20.0, 0, 20.0]  # Fill defaults

    sim_table.loc[t1, "M"] += 1
    sim_table.loc[t2, "M"] += 1

    if "by runs" in outcome["result"]:
        winner = t1 if t1 in outcome['result'] else t2
        loser = t2 if winner == t1 else t1

        first_innings_runs = outcome["first_innings_runs"]
        win_margin = outcome["margin"]

        loser_score = first_innings_runs
        winner_score = first_innings_runs + win_margin

        sim_table.loc[winner, "W"] += 1
        sim_table.loc[loser, "L"] += 1
        sim_table.loc[winner, "PT"] += 4

        # Run Rate updates
        sim_table.loc[winner, "Runs For"] += winner_score
        sim_table.loc[winner, "Overs For"] += 20.0
        sim_table.loc[winner, "Runs Against"] += loser_score
        sim_table.loc[winner, "Overs Against"] += 20.0

        sim_table.loc[loser, "Runs For"] += loser_score
        sim_table.loc[loser, "Overs For"] += 20.0
        sim_table.loc[loser, "Runs Against"] += winner_score
        sim_table.loc[loser, "Overs Against"] += 20.0

    elif "with balls remaining" in outcome["result"]:
        winner = t1 if t1 in outcome['result'] else t2
        loser = t2 if winner == t1 else t1

        chasing_runs = outcome["chasing_runs"]
        first_innings_runs = outcome["first_innings_runs"]
        balls_remain = outcome["balls_remaining"]
        balls_faced = 120 - balls_remain
        overs_used = cricket_overs_from_balls(balls_faced)

        sim_table.loc[winner, "W"] += 1
        sim_table.loc[loser, "L"] += 1
        sim_table.loc[winner, "PT"] += 4

        # NRR updates
        sim_table.loc[winner, "Runs For"] += chasing_runs
        sim_table.loc[winner, "Overs For"] += overs_used
        sim_table.loc[winner, "Runs Against"] += first_innings_runs
        sim_table.loc[winner, "Overs Against"] += 20.0

        sim_table.loc[loser, "Runs For"] += first_innings_runs
        sim_table.loc[loser, "Overs For"] += 20.0
        sim_table.loc[loser, "Runs Against"] += chasing_runs
        sim_table.loc[loser, "Overs Against"] += overs_used

    elif outcome['result'] == "Tie":
        sim_table.loc[t1, "T"] += 1
        sim_table.loc[t2, "T"] += 1
        sim_table.loc[t1, "PT"] += 2
        sim_table.loc[t2, "PT"] += 2

    elif outcome['result'] == "No Result":
        sim_table.loc[t1, "N/R"] += 1
        sim_table.loc[t2, "N/R"] += 1
        sim_table.loc[t1, "PT"] += 2
        sim_table.loc[t2, "PT"] += 2

# ----------------------------
# Final Display
# ----------------------------
sim_table["NRR"] = sim_table.apply(lambda row:
    calculate_nrr(row['Runs For'], cricket_balls_from_overs(row['Overs For']),
                  row['Runs Against'], cricket_balls_from_overs(row['Overs Against'])), axis=1)

final_display = sim_table.reset_index()
final_display = final_display.sort_values(by=["PT", "NRR"], ascending=[False, False]).reset_index(drop=True)
final_display.index += 1

st.markdown("### 🔮 Projected Table")
st.dataframe(final_display.style.format({
    "M": "{:.0f}", "W": "{:.0f}", "L": "{:.0f}", "T": "{:.0f}", "N/R": "{:.0f}", "PT": "{:.0f}", "NRR": "{:.3f}"
}))

# Steelbacks Qualification Check
steelbacks_index = final_display.index[final_display['Team'] == "Northamptonshire Steelbacks Men"].tolist()
if not steelbacks_index:
    st.markdown("❌ Steelbacks not found in updated table")
else:
    rank = steelbacks_index[0] + 1
    if rank <= 4:
        st.markdown(f"✅ **Northamptonshire Steelbacks Men QUALIFY** in position **{rank}** 🎉")
    else:
        st.markdown(f"❌ **Northamptonshire Steelbacks Men DO NOT QUALIFY**, finishing **{rank}**")

# Download Option
csv = final_display.to_csv(index=False).encode('utf-8')
st.download_button("📥 Download Projected Table", data=csv, file_name='projected_table.csv', mime='text/csv')