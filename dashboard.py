import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="FitLife Dashboard", page_icon="💪", layout="wide")

# ── Carga de datos ──────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    members = pd.read_csv("fitlife_members.csv")
    context = pd.read_csv("fitlife_context.csv")
    members["margin"] = members["price_paid"] - members["cost_to_serve"]
    members["month"] = members["month"].astype(str)
    context["month"] = context["month"].astype(str)
    return members, context

df, ctx = load_data()

# ── Sidebar ─────────────────────────────────────────────────────────────────
st.sidebar.title("Filtros")

months_sorted = sorted(df["month"].unique())
month_range = st.sidebar.select_slider(
    "Rango de meses",
    options=months_sorted,
    value=(months_sorted[0], months_sorted[-1]),
)
all_centers = sorted(df["center"].unique())
center_choice = st.sidebar.selectbox(
    "Centro", options=["Todos"] + all_centers
)
centers = all_centers if center_choice == "Todos" else [center_choice]

all_plans = sorted(df["plan"].unique())
plan_choice = st.sidebar.selectbox(
    "Plan", options=["Todos"] + all_plans
)
plans = all_plans if plan_choice == "Todos" else [plan_choice]

mask = (
    (df["month"] >= month_range[0])
    & (df["month"] <= month_range[1])
    & (df["center"].isin(centers))
    & (df["plan"].isin(plans))
)
fdf = df[mask].copy()
ctx_mask = (ctx["month"] >= month_range[0]) & (ctx["month"] <= month_range[1])
fctx = ctx[ctx_mask].copy()

# ── KPIs ────────────────────────────────────────────────────────────────────
st.title("💪 FitLife Analytics Dashboard")

active = fdf[fdf["status"] == "active"]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Socios activos", f"{len(active):,}")
col2.metric("Ingresos totales", f"${fdf['price_paid'].sum():,.0f}")
col3.metric("Margen total", f"${fdf['margin'].sum():,.0f}")
col4.metric(
    "Churn rate medio",
    f"{(fdf['status'] == 'churned').mean() * 100:.1f}%",
)

st.markdown("---")

# ── 1. Evolución mensual de ingresos, costes y margen ───────────────────────
st.subheader("📈 Evolución mensual: Ingresos · Costes · Margen")

monthly = (
    fdf.groupby("month")
    .agg(revenue=("price_paid", "sum"), cost=("cost_to_serve", "sum"), margin=("margin", "sum"))
    .reset_index()
)

fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=monthly["month"], y=monthly["revenue"], name="Ingresos",
                           mode="lines+markers", line=dict(color="#4C9BE8", width=2.5)))
fig1.add_trace(go.Scatter(x=monthly["month"], y=monthly["cost"], name="Costes",
                           mode="lines+markers", line=dict(color="#E8714C", width=2.5)))
fig1.add_trace(go.Scatter(x=monthly["month"], y=monthly["margin"], name="Margen",
                           mode="lines+markers", line=dict(color="#4CE87A", width=2.5),
                           fill="tozeroy", fillcolor="rgba(76,232,122,0.08)"))
fig1.update_layout(
    xaxis_title="Mes", yaxis_title="USD ($)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    hovermode="x unified", height=380,
)
st.plotly_chart(fig1, use_container_width=True)

# ── 2. Evolución mensual de socios activos y churn rate ─────────────────────
st.subheader("👥 Evolución mensual: Socios activos & Tasa de churn")

churn_monthly = (
    fdf.groupby("month")
    .agg(
        total=("member_id", "count"),
        churned=("status", lambda x: (x == "churned").sum()),
        active_count=("status", lambda x: (x == "active").sum()),
    )
    .reset_index()
)
churn_monthly["churn_rate"] = churn_monthly["churned"] / churn_monthly["total"] * 100

fig2 = make_subplots(specs=[[{"secondary_y": True}]])
fig2.add_trace(
    go.Bar(x=churn_monthly["month"], y=churn_monthly["active_count"],
           name="Socios activos", marker_color="#4C9BE8", opacity=0.75),
    secondary_y=False,
)
fig2.add_trace(
    go.Scatter(x=churn_monthly["month"], y=churn_monthly["churn_rate"],
               name="Churn rate (%)", mode="lines+markers",
               line=dict(color="#E8714C", width=2.5)),
    secondary_y=True,
)
fig2.update_yaxes(title_text="Socios activos", secondary_y=False)
fig2.update_yaxes(title_text="Churn rate (%)", secondary_y=True)
fig2.update_layout(hovermode="x unified", height=380,
                   legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig2, use_container_width=True)

# ── 3. Margen mensual por plan ───────────────────────────────────────────────
st.subheader("🏷️ Evolución mensual del margen por plan")

margin_plan = (
    fdf.groupby(["month", "plan"])["margin"].sum().reset_index()
)
fig3 = px.line(
    margin_plan, x="month", y="margin", color="plan",
    markers=True,
    color_discrete_map={"basic": "#4C9BE8", "premium": "#B44CE8", "family": "#4CE87A"},
)
fig3.update_layout(xaxis_title="Mes", yaxis_title="Margen ($)", height=380,
                   legend=dict(orientation="h", yanchor="bottom", y=1.02),
                   hovermode="x unified")
st.plotly_chart(fig3, use_container_width=True)

# ── 4. LTV mensual (por plan) ────────────────────────────────────────────────
st.subheader("💰 LTV mensual por plan")
st.caption("LTV = margen mensual medio por socio × tenure medio (meses)")

ltv_monthly = (
    fdf.groupby(["month", "plan"])
    .agg(avg_margin=("margin", "mean"), avg_tenure=("tenure_months", "mean"))
    .reset_index()
)
ltv_monthly["ltv"] = ltv_monthly["avg_margin"] * ltv_monthly["avg_tenure"]

fig4 = px.line(
    ltv_monthly, x="month", y="ltv", color="plan",
    markers=True,
    color_discrete_map={"basic": "#4C9BE8", "premium": "#B44CE8", "family": "#4CE87A"},
    labels={"ltv": "LTV ($)", "month": "Mes"},
)
fig4.update_layout(height=380, hovermode="x unified",
                   legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig4, use_container_width=True)

# ── 5. CAC mensual vs LTV medio ──────────────────────────────────────────────
st.subheader("📊 Evolución mensual: CAC vs LTV medio")
st.caption("Ratio LTV/CAC > 3 indica rentabilidad sostenible")

ltv_total = (
    fdf.groupby("month")
    .apply(lambda g: (g["margin"] * g["tenure_months"]).mean(), include_groups=False)
    .reset_index(name="ltv_avg")
)
cac_monthly = fctx[["month", "acquisition_cost_avg"]].copy()
ltv_cac = ltv_total.merge(cac_monthly, on="month", how="left")
ltv_cac["ltv_cac_ratio"] = ltv_cac["ltv_avg"] / ltv_cac["acquisition_cost_avg"]

fig5 = make_subplots(specs=[[{"secondary_y": True}]])
fig5.add_trace(
    go.Bar(x=ltv_cac["month"], y=ltv_cac["ltv_avg"],
           name="LTV medio ($)", marker_color="#4CE87A", opacity=0.8),
    secondary_y=False,
)
fig5.add_trace(
    go.Scatter(x=ltv_cac["month"], y=ltv_cac["acquisition_cost_avg"],
               name="CAC ($)", mode="lines+markers",
               line=dict(color="#E8714C", width=2.5)),
    secondary_y=False,
)
fig5.add_trace(
    go.Scatter(x=ltv_cac["month"], y=ltv_cac["ltv_cac_ratio"],
               name="Ratio LTV/CAC", mode="lines+markers",
               line=dict(color="#B44CE8", width=2, dash="dot")),
    secondary_y=True,
)
# Línea de referencia ratio = 3
fig5.add_hline(y=3, line_dash="dash", line_color="gray",
               annotation_text="Ratio 3x (objetivo)", annotation_position="bottom right",
               secondary_y=True)
fig5.update_yaxes(title_text="USD ($)", secondary_y=False)
fig5.update_yaxes(title_text="Ratio LTV/CAC", secondary_y=True)
fig5.update_layout(hovermode="x unified", height=420,
                   legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig5, use_container_width=True)

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("FitLife Analytics · Datos: fitlife_members.csv + fitlife_context.csv")
