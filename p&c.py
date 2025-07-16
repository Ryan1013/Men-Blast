import streamlit as st
import pandas as pd
import itertools
import numpy as np
import io

st.set_page_config(layout="wide")

st.title("🔢 Northamptonshire Steelbacks Qualification Simulator – Vitality Blast 2025")

# -----------------------
# Load Current Table
# -----------------------
@st.cache_data
def load_current_table():
    df = pd.read_csv("current_table.csv")
    return df

current_table = load_current_table()
teams = current_table["Team"].tolist()

st.subheader("📊 Current Table (before simulation)")
st.dataframe(current_table.style.format({"NRR": "{:+.3f}", "PT": "{:.0f}"}), use_container_width=True)

# -----------------------
# Define Remaining Fixtures
# -----------------------
fixtures = [
    ("17 July", "Worcestershire Rapids Men", "Notts Outlaws"),
    ("17 July", "Yorkshire Men", "Lancashire Lightning"),
    ("18 July", "Durham Cricket Men", "Northamptonshire Steelbacks Men"),
    ("18 July", "Leicestershire Foxes Men", "Yorkshire Men"),
    ("18 July", "Derbyshire Falcons Men", "Bears Men"),
    ("18 July", "Notts Outlaws", "Lancashire Lightning"),
]

# -----------------------
# Simulation Inputs
# -----------------------
st.subheader("🧮 Simulate Remaining Matches")

simulation_results = []
for i, (date, team1, team2) in enumerate(fixtures):
    with st.expander(f"📅 {date}: {team1} vs {team2}"):
        result = st.radio(
            f"Match Result ({team1} vs {team2})", 
            ["Not Played", f"{team1} Win (by runs)", f"{team2} Win (by runs)", 
             f"{team1} Win (with balls remaining)", f"{team2} Win (with balls remaining)", "Tie", "No Result"], 
            key=f"result_{i}"
        )

        if "by runs" in result:
            score = st.slider(f"{result} – 1st Innings Total (Batting First)", 50, 300, 150, 1, key=f"score_{i}")
            margin = st.slider("Win Margin (Runs)", 1, 200, 10, 1, key=f"margin_{i}")
            simulation_results.append({
                "team1": team1,
                "team2": team2,
                "result": result,
                "score": score,
                "margin": margin
            })

        elif "balls remaining" in result:
            balls_remaining = st.slider("Balls Remaining", 1, 120, 10, 1, key=f"balls_{i}")
            chasing_runs = st.number_input("Runs Scored by Chasing Team", min_value=1, max_value=400, value=150, step=1, key=f"chasing_runs_{i}")
            simulation_results.append({
                "team1": team1,
                "team2": team2,
                "result": result,
                "balls_remaining": balls_remaining,
                "chasing_runs": chasing_runs
            })

        elif result in ["Tie", "No Result"]:
            simulation_results.append({
                "team1": team1,
                "team2": team2,
                "result": result
            })

# -----------------------
# Simulation Logic
# -----------------------
def cricket_overs_from_balls(balls):
    return round(balls // 6 + (balls % 6) / 10, 1)

def calculate_nrr_table(current_table, sim_results):
    df = current_table.copy()
    df = df.set_index("Team")
    df[["M", "W", "L", "T", "N/R", "PT"]] = df[["M", "W", "L", "T", "N/R", "PT"]].astype(int)

    for sim in sim_results:
        t1, t2 = sim["team1"], sim["team2"]
        if sim["result"] == f"{t1} Win (by runs)":
            runs_for = sim["score"]
            runs_against = sim["score"] - sim["margin"]
            overs = 20.0
            df.loc[t1, "W"] += 1
            df.loc[t2, "L"] += 1
            df.loc[t1, "PT"] += 4
        elif sim["result"] == f"{t2} Win (by runs)":
            runs_for = sim["score"]
            runs_against = sim["score"] - sim["margin"]
            overs = 20.0
            df.loc[t2, "W"] += 1
            df.loc[t1, "L"] += 1
            df.loc[t2, "PT"] += 4
        elif sim["result"] == f"{t1} Win (with balls remaining)":
            overs_used = (120 - sim["balls_remaining"])
            overs = cricket_overs_from_balls(overs_used)
            runs_for = sim["chasing_runs"]
            runs_against = sim["chasing_runs"] - 1
            df.loc[t1, "W"] += 1
            df.loc[t2, "L"] += 1
            df.loc[t1, "PT"] += 4
        elif sim["result"] == f"{t2} Win (with balls remaining)":
            overs_used = (120 - sim["balls_remaining"])
            overs = cricket_overs_from_balls(overs_used)
            runs_for = sim["chasing_runs"]
            runs_against = sim["chasing_runs"] - 1
            df.loc[t2, "W"] += 1
            df.loc[t1, "L"] += 1
            df.loc[t2, "PT"] += 4
        elif sim["result"] == "Tie":
            df.loc[t1, "T"] += 1
            df.loc[t2, "T"] += 1
            df.loc[[t1, t2], "PT"] += 2
            continue
        elif sim["result"] == "No Result":
            df.loc[t1, "N/R"] += 1
            df.loc[t2, "N/R"] += 1
            df.loc[[t1, t2], "PT"] += 2
            continue
        else:
            continue

        df.loc[t1, "M"] += 1
        df.loc[t2, "M"] += 1

        if sim["result"].startswith(t1):
            df.loc[t1, "Runs For"] += runs_for
            df.loc[t1, "Overs For"] += overs
            df.loc[t1, "Runs Against"] += runs_against
            df.loc[t1, "Overs Against"] += 20.0
            df.loc[t2, "Runs For"] += runs_against
            df.loc[t2, "Overs For"] += 20.0
            df.loc[t2, "Runs Against"] += runs_for
            df.loc[t2, "Overs Against"] += overs
        else:
            df.loc[t2, "Runs For"] += runs_for
            df.loc[t2, "Overs For"] += overs
            df.loc[t2, "Runs Against"] += runs_against
            df.loc[t2, "Overs Against"] += 20.0
            df.loc[t1, "Runs For"] += runs_against
            df.loc[t1, "Overs For"] += 20.0
            df.loc[t1, "Runs Against"] += runs_for
            df.loc[t1, "Overs Against"] += overs

    df["NRR"] = ((df["Runs For"] / df["Overs For"]) - (df["Runs Against"] / df["Overs Against"])).round(3)
    df = df.reset_index()
    df = df.sort_values(by=["PT", "NRR"], ascending=[False, False]).reset_index(drop=True)
    return df

# -----------------------
# Run Simulation
# -----------------------
if st.button("🚀 Run Simulation"):
    updated_table = calculate_nrr_table(current_table, simulation_results)
    st.subheader("📈 Updated Table After Simulation")
    st.dataframe(updated_table.style.format({"NRR": "{:+.3f}", "PT": "{:.0f}"}), use_container_width=True)

    steelbacks_index = updated_table[updated_table["Team"] == "Northamptonshire Steelbacks Men"].index
    if len(steelbacks_index) == 0:
        st.warning("❗ Northamptonshire Steelbacks Men not found in table.")
    else:
        rank = steelbacks_index[0] + 1
        if rank <= 4:
            st.markdown(f"✅ **Northamptonshire Steelbacks Men QUALIFY**, finishing **{rank}** 🎉")
        else:
            st.markdown(f"❌ **Northamptonshire Steelbacks Men DO NOT QUALIFY**, finishing **{rank}**")

    # CSV download
    csv = updated_table.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Updated Table as CSV",
        data=csv,
        file_name="updated_simulated_table.csv",
        mime="text/csv"
    )