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
centers = st.sidebar.multiselect(
    "Centros", options=sorted(df["center"].unique()), default=sorted(df["center"].unique())
)
plans = st.sidebar.multiselect(
    "Planes", options=sorted(df["plan"].unique()), default=sorted(df["plan"].unique())
)

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

# ── 4. Precio FitLife vs Competidor + campañas ──────────────────────────────
st.subheader("🏪 Precio medio FitLife vs Competidor low-cost")

avg_price = fdf.groupby("month")["price_paid"].mean().reset_index(name="fitlife_price")
price_comp = avg_price.merge(
    fctx[["month", "competitor_lowcost_price", "campaign_active", "service_incident"]],
    on="month", how="left",
)

fig4 = go.Figure()
fig4.add_trace(go.Scatter(
    x=price_comp["month"], y=price_comp["fitlife_price"],
    name="FitLife (precio medio)", mode="lines+markers",
    line=dict(color="#4C9BE8", width=2.5)
))
fig4.add_trace(go.Scatter(
    x=price_comp["month"], y=price_comp["competitor_lowcost_price"],
    name="Competidor low-cost", mode="lines+markers",
    line=dict(color="#E84C4C", width=2.5, dash="dash")
))

# Marcar campañas como shapes + annotations (add_vline no acepta strings en eje x categórico)
months_list = price_comp["month"].tolist()
for _, row in price_comp.dropna(subset=["campaign_active"]).iterrows():
    if pd.notna(row["campaign_active"]) and row["campaign_active"] != "":
        idx = months_list.index(row["month"])
        fig4.add_shape(
            type="line", xref="x", yref="paper",
            x0=idx, x1=idx, y0=0, y1=1,
            line=dict(color="green", width=1, dash="dot"),
        )
        fig4.add_annotation(
            x=idx, yref="paper", y=1.05,
            text=str(row["campaign_active"]),
            showarrow=False, font=dict(size=8, color="green"),
            xanchor="left",
        )

fig4.update_layout(xaxis_title="Mes", yaxis_title="Precio ($)", height=400,
                   legend=dict(orientation="h", yanchor="bottom", y=1.02),
                   hovermode="x unified")
st.plotly_chart(fig4, use_container_width=True)

# ── 5. Distribución de margen por canal de adquisición ──────────────────────
st.subheader("📣 Margen mensual por canal de adquisición")

channel_monthly = (
    fdf.groupby(["month", "acquisition_channel"])["margin"].sum().reset_index()
)
fig5 = px.bar(
    channel_monthly, x="month", y="margin", color="acquisition_channel",
    barmode="stack",
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig5.update_layout(xaxis_title="Mes", yaxis_title="Margen ($)", height=380,
                   legend=dict(orientation="h", yanchor="bottom", y=1.02),
                   hovermode="x unified")
st.plotly_chart(fig5, use_container_width=True)

# ── 6. Ocupación media y coste de adquisición ────────────────────────────────
st.subheader("🏋️ Ocupación media & Coste de adquisición mensual")

fig6 = make_subplots(specs=[[{"secondary_y": True}]])
fig6.add_trace(
    go.Scatter(x=fctx["month"], y=fctx["avg_occupancy_rate"] * 100,
               name="Ocupación (%)", mode="lines+markers",
               line=dict(color="#4CE8C8", width=2.5)),
    secondary_y=False,
)
fig6.add_trace(
    go.Scatter(x=fctx["month"], y=fctx["acquisition_cost_avg"],
               name="Coste adquisición ($)", mode="lines+markers",
               line=dict(color="#E8B44C", width=2.5)),
    secondary_y=True,
)
fig6.update_yaxes(title_text="Ocupación (%)", secondary_y=False)
fig6.update_yaxes(title_text="Coste adquisición ($)", secondary_y=True)
fig6.update_layout(hovermode="x unified", height=380,
                   legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig6, use_container_width=True)

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("FitLife Analytics · Datos: fitlife_members.csv + fitlife_context.csv")
