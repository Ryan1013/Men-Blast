import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO

# Load current standings
current_table = pd.read_csv("current_table_men.csv")

# Set page config
st.set_page_config(page_title="Northamptonshire Qualification Simulator", layout="wide")
st.title("📊 Northamptonshire Steelbacks Men: Qualification Simulator")
st.markdown("Evaluate **Vitality Blast - North Group** qualification scenarios based on remaining fixtures and NRR permutations.")

# Define remaining fixtures
fixtures = [
    {"Date": "17 July", "Match": "Worcestershire Rapids Men vs Notts Outlaws"},
    {"Date": "17 July", "Match": "Yorkshire Men vs Lancashire Lightning"},
    {"Date": "18 July", "Match": "Durham Cricket Men vs Northamptonshire Steelbacks Men"},
    {"Date": "18 July", "Match": "Leicestershire Foxes Men vs Yorkshire Men"},
    {"Date": "18 July", "Match": "Derbyshire Falcons Men vs Bears Men"},
    {"Date": "18 July", "Match": "Notts Outlaws vs Lancashire Lightning"},
]

# Create placeholder for match results
st.subheader("📅 Enter Predicted Results")
fixture_outcomes = {}
for i, fixture in enumerate(fixtures):
    with st.expander(f"{fixture['Date']} - {fixture['Match']}"):
        team1, team2 = fixture["Match"].split(" vs ")
        result_type = st.selectbox(f"Select result for {team1} vs {team2}", [
            "No Result", "Tie", f"{team1} Win", f"{team2} Win"
        ], key=f"result_{i}")

        # Inputs for winning team scenarios
        if "Win" in result_type:
            st.markdown("🔢 Enter score of **batting first** team and win/loss margin (run difference):")
            batting_first_runs = st.number_input("Batting First Runs", min_value=50, max_value=300, value=150, step=1, key=f"bf_runs_{i}")
            margin = st.number_input("Run Margin", min_value=1, max_value=200, value=10, step=1, key=f"margin_{i}")
        else:
            batting_first_runs, margin = None, None

        fixture_outcomes[fixture["Match"]] = {
            "type": result_type,
            "batting_runs": batting_first_runs,
            "margin": margin
        }

# Function to convert overs to balls and vice versa
def cricket_overs_to_balls(overs):
    overs_int = int(overs)
    balls_part = int(round((overs - overs_int) * 10))
    return overs_int * 6 + balls_part

def balls_to_cricket_overs(balls):
    overs = balls // 6
    rem_balls = balls % 6
    return float(f"{int(overs)}.{int(rem_balls)}")

# Function to simulate NRR updates
def simulate(current_table, fixture_outcomes):
    table = current_table.copy()

    for match, outcome in fixture_outcomes.items():
        team1, team2 = match.split(" vs ")
        result_type = outcome["type"]

        for team in [team1, team2]:
            if team not in table['Team'].values:
                table = pd.concat([
                    table,
                    pd.DataFrame([{
                        'Team': team, 'M': 0, 'W': 0, 'L': 0, 'T': 0, 'N/R': 0,
                        'PT': 0, 'NRR': 0.0,
                        'Runs For': 0, 'Overs For': 0.0,
                        'Runs Against': 0, 'Overs Against': 0.0
                    }])
                ], ignore_index=True)

        if result_type == "No Result":
            for team in [team1, team2]:
                table.loc[table['Team'] == team, ['M', 'N/R', 'PT']] += [1, 1, 2]

        elif result_type == "Tie":
            for team in [team1, team2]:
                table.loc[table['Team'] == team, ['M', 'T', 'PT']] += [1, 1, 2]

        else:
            winner = team1 if result_type == f"{team1} Win" else team2
            loser = team2 if winner == team1 else team1
            margin = outcome["margin"]
            runs_for = outcome["batting_runs"]
            runs_against = runs_for - margin

            table.loc[table['Team'] == winner, ['M', 'W', 'PT']] += [1, 1, 4]
            table.loc[table['Team'] == loser, ['M', 'L']] += [1, 1]

            # Update NRR
            winner_runs_for = table.loc[table['Team'] == winner, 'Runs For'].values[0] + runs_for
            loser_runs_for = table.loc[table['Team'] == loser, 'Runs For'].values[0] + runs_against
            winner_runs_against = table.loc[table['Team'] == winner, 'Runs Against'].values[0] + runs_against
            loser_runs_against = table.loc[table['Team'] == loser, 'Runs Against'].values[0] + runs_for

            balls = cricket_overs_to_balls(20.0)

            table.loc[table['Team'] == winner, 'Runs For'] = winner_runs_for
            table.loc[table['Team'] == winner, 'Overs For'] += 20.0
            table.loc[table['Team'] == winner, 'Runs Against'] = winner_runs_against
            table.loc[table['Team'] == winner, 'Overs Against'] += 20.0

            table.loc[table['Team'] == loser, 'Runs For'] = loser_runs_for
            table.loc[table['Team'] == loser, 'Overs For'] += 20.0
            table.loc[table['Team'] == loser, 'Runs Against'] = loser_runs_against
            table.loc[table['Team'] == loser, 'Overs Against'] += 20.0

    # Recompute NRR
    for idx, row in table.iterrows():
        try:
            rf = row['Runs For']
            of = row['Overs For']
            ra = row['Runs Against']
            oa = row['Overs Against']
            balls_f = cricket_overs_to_balls(of)
            balls_a = cricket_overs_to_balls(oa)
            rrf = rf / (balls_f / 6) if balls_f else 0
            rra = ra / (balls_a / 6) if balls_a else 0
            nrr = round(rrf - rra, 3)
            table.at[idx, 'NRR'] = nrr
        except:
            table.at[idx, 'NRR'] = 0.0

    table = table.sort_values(by=['PT', 'NRR'], ascending=[False, False]).reset_index(drop=True)
    table.index += 1
    return table

# Button to simulate and display results
if st.button("Simulate Qualification Table"):
    simulated = simulate(current_table, fixture_outcomes)
    st.success("✅ Simulation complete!")
    st.dataframe(simulated)

    # Qualification result for Northamptonshire
    steelbacks_index = simulated[simulated['Team'] == 'Northamptonshire Steelbacks Men'].index
    if len(steelbacks_index) == 0:
        st.warning("⚠️ Northamptonshire Steelbacks Men not found in simulation.")
    else:
        rank = steelbacks_index[0] + 1
        if rank <= 4:
            st.markdown(f"✅ **Northamptonshire Steelbacks Men QUALIFY** in position **{rank}** 🎉")
        else:
            st.markdown(f"❌ **Northamptonshire Steelbacks Men DO NOT QUALIFY**, finishing **{rank}**")

    # Download option
    csv_download = simulated.to_csv(index=False)
    st.download_button(
        label="📥 Download Simulated Table as CSV",
        data=csv_download,
        file_name="simulated_nrr_table.csv",
        mime="text/csv"
    )