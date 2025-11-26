import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os

# ---------------------------------------------
# PAGE SETTINGS
# ---------------------------------------------
st.set_page_config(page_title="Serverless FinOps Dashboard", layout="wide")
st.title("📊 RetailNova Serverless FinOps Dashboard")
st.write("Analyze serverless cost, performance & optimization opportunities.")

# ---------------------------------------------
# CSV AUTO-LOAD
# ---------------------------------------------
FILE_NAME = "Serverless_Data.csv"

if not os.path.exists(FILE_NAME):
    st.error(f"CSV file '{FILE_NAME}' not found. Place it beside app.py.")
    st.stop()

# *** Critical Fix: Parse CSV Correctly ***
raw = open(FILE_NAME, "r").read().splitlines()
parsed = [line[1:-1].split(",") if line.startswith('"') else line.split(",") for line in raw]
df = pd.DataFrame(parsed[1:], columns=parsed[0])

# numeric conversion
for c in ["InvocationsPerMonth","AvgDurationMs","MemoryMB","ColdStartRate",
          "ProvisionedConcurrency","GBSeconds","DataTransferGB","CostUSD"]:
    df[c] = pd.to_numeric(df[c],errors="coerce")

# ---------------------------------------------
# FILTERS
# ---------------------------------------------
st.sidebar.header("Filters")

envs = df["Environment"].unique().tolist()
env_sel = st.sidebar.multiselect("Environment",envs,default=envs)

cost_sel = st.sidebar.slider("Monthly Cost (USD)",
                             float(df.CostUSD.min()), float(df.CostUSD.max()),
                             (float(df.CostUSD.min()), float(df.CostUSD.max())))

# 🔥 filtered dataset applied everywhere below
data = df[(df.Environment.isin(env_sel)) & (df.CostUSD.between(cost_sel[0], cost_sel[1]))].copy()

data["CostShare%"] = data.CostUSD / data.CostUSD.sum() * 100
data["Invocation%"] = data.InvocationsPerMonth / data.InvocationsPerMonth.sum() * 100

# ---------------------------------------------
# METRICS SUMMARY
# ---------------------------------------------
c1,c2,c3,c4,c5 = st.columns(5)

c1.metric("💰 Total Cost", f"${data.CostUSD.sum():,.2f}")
c2.metric("⚡ Monthly Invocations", f"{int(data.InvocationsPerMonth.sum()):,}")
c3.metric("⏱ Avg Duration", f"{data.AvgDurationMs.mean():.1f} ms")
c4.metric("💾 Avg Memory", f"{data.MemoryMB.mean():.0f} MB")
c5.metric("🧩 Total Functions", f"{len(data):,}")   # ← This is the new metric


# ---------------------------------------------
# TABS (ALL 5 REQUIRED EXERCISES)
# ---------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1️⃣ Cost Concentration",
    "2️⃣ Memory Right-Sizing",
    "3️⃣ Provisioned Concurrency Optimization",
    "4️⃣ Low-Value Workloads Detection",
    "5️⃣ Cost Forecasting Model",
    "6️⃣ Containerization Recommendations"
])

# =========================================================
# 🟦 1. COST CONCENTRATION (Pareto)
# =========================================================
with tab1:
    import datetime
    today = datetime.date.today()

    st.write(f"📅 **Analysis Generated On:** {today.strftime('%B %d, %Y')}")
    st.subheader("🔥 Functions Driving ~80% of Spend")

    # 🔥 Uses filtered dataset (data)
    df80 = data.sort_values("CostUSD", ascending=False)
    df80["Cum%"] = df80.CostUSD.cumsum() / df80.CostUSD.sum() * 100

    st.dataframe(df80[df80["Cum%"] <= 80])

    fig = px.bar(df80.head(10),
                 x="FunctionName",
                 y="CostUSD",
                 color="Environment")
    st.plotly_chart(fig, use_container_width=True)


# =========================================================
# 2️⃣ MEMORY RIGHT-SIZING
# =========================================================
with tab2:
    st.header("Exercise 2: Memory Right-Sizing 🔧")

    mem_t = st.slider("High Memory ≥ (MB)",512,4096,2048)
    dur_t = st.slider("Low Duration ≤ (ms)",50,2000,600)

    rs = data[(data.MemoryMB>=mem_t) & (data.AvgDurationMs<=dur_t)]
    st.subheader("📌 Candidates with high memory + low duration")
    st.dataframe(rs)

    st.plotly_chart(px.scatter(data,x="MemoryMB",y="AvgDurationMs",size="CostUSD",
                               color="Environment",hover_name="FunctionName"),use_container_width=True)

# =========================================================
# 3️⃣ PROVISIONED CONCURRENCY
# =========================================================
with tab3:
    st.header("Exercise 3: Provisioned Concurrency Optimization ⚙")

    cold = st.slider("Cold Start Rate ≤ (%)",0,50,5)
    pc = data[(data.ProvisionedConcurrency>0) & (data.ColdStartRate<=cold)]

    st.subheader("🔻 Functions where PC can be reduced/removed")
    st.dataframe(pc)

    st.plotly_chart(px.scatter(data,x="ProvisionedConcurrency",y="ColdStartRate",
                               size="CostUSD",color="Environment",hover_name="FunctionName"),
                    use_container_width=True)

# =========================================================
# 4️⃣ LOW-VALUE WORKLOADS
# =========================================================
with tab4:
    st.header("Exercise 4: Low-Value Workload Detection 🔍")

    low = data[(data["Invocation%"]<1) & (data.CostUSD>data.CostUSD.median())]
    st.subheader("⚠ Low usage (<1%) but high cost workloads")
    st.dataframe(low)

    st.plotly_chart(px.scatter(data,x="Invocation%",y="CostUSD",
                               color="Environment",size="CostUSD",hover_name="FunctionName"),
                    use_container_width=True)

# =========================================================
# 5️⃣ COST FORECASTING MODEL
# =========================================================
with tab5:
    st.header("Exercise 5: Cost Forecasting 📈")

    X = data.InvocationsPerMonth * data.AvgDurationMs * data.MemoryMB
    Y = data.CostUSD

    beta = np.polyfit(X,Y,1)
    C1,C0 = beta ; C2 = 0.0005

    st.write(f"**Cost ≈ {C1:.8e} × (inv×duration×memory) + {C2}×DataTransferGB + {C0:.2f}**")

    inv = st.number_input("Invocations",1000,5000000,200000)
    dur = st.number_input("Duration (ms)",10,3000,250)
    mem = st.number_input("Memory (MB)",128,4096,1024)
    data_gb = st.number_input("Data Transfer (GB)",0,5000,50)

    predicted = C1*(inv*dur*mem) + C2*data_gb + C0
    st.success(f"Predicted Monthly Cost → **${predicted:,.2f}**")

# =========================================================
# 6️⃣ CONTAINERIZATION CANDIDATES
# =========================================================
with tab6:
    st.header("Exercise 6: Container-Suitable Workloads 🐳")

    cont = data[(data.AvgDurationMs>=3000) & (data.MemoryMB>=2048) &
                (data.InvocationsPerMonth<data.InvocationsPerMonth.median())]

    st.subheader("Recommended for ECS/Fargate/K8s instead of Lambda")
    st.dataframe(cont)

    st.plotly_chart(px.scatter(data,x="AvgDurationMs",y="MemoryMB",size="CostUSD",
                               color="Environment",hover_name="FunctionName"),
                    use_container_width=True)
