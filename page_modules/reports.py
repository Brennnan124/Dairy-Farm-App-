# dairy_farm_app/pages/reports.py
import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from utils.data_loader import load_table, to_date
from utils.calculations import calculate_profit_per_cow
from utils.helpers import format_with_commas

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

def reports_page(start_date, end_date, granularity):
    st.title("📊 Reports")
    
    if granularity == "Daily":
        date_range_str = f"Past 24 hours (from {start_date} to {end_date})"
    elif granularity == "Weekly":
        date_range_str = f"Past 7 days (from {start_date} to {end_date})"
    else:
        date_range_str = f"Past 31 days (from {start_date} to {end_date})"
    
    st.write(f"**Report Period:** {date_range_str}")
    
    milk = to_date(load_table("milk_production"), "date")
    fr = to_date(load_table("feeds_received"), "date")
    fu = to_date(load_table("feeds_used"), "date")
    health = to_date(load_table("health_records"), "date")
    ai = to_date(load_table("ai_records"), "ai_date")
    
    if not milk.empty:
        milk = milk[(milk["date"] >= start_date) & (milk["date"] <= end_date)]
    if not fr.empty:
        fr = fr[(fr["date"] >= start_date) & (fr["date"] <= end_date)]
    if not fu.empty:
        fu = fu[(fu["date"] >= start_date) & (fu["date"] <= end_date)]
    if not health.empty:
        health = health[(health["date"] >= start_date) & (health["date"] <= end_date)]
    if not ai.empty:
        ai = ai[(ai["ai_date"] >= start_date) & (ai["ai_date"] <= end_date)]

    price_per_litre = 43
    milk_daily = pd.DataFrame()
    if not milk.empty:
        milk_daily = (milk.groupby("date")["litres_sell"].sum().to_frame("milk_l"))
        milk_daily["revenue"] = milk_daily["milk_l"] * price_per_litre

    cost_daily = pd.DataFrame()
    if not fr.empty:
        cost_daily = fr.groupby("date")["cost"].sum().to_frame("feed_cost")

    health_costs = pd.DataFrame()
    if not health.empty and 'cost' in health.columns:
        health_costs = health.groupby("date")["cost"].sum().to_frame("health_cost")

    ai_costs = pd.DataFrame()
    if not ai.empty and 'cost' in ai.columns:
        ai_costs = ai.groupby("ai_date")["cost"].sum().to_frame("ai_cost")

    daily = pd.DataFrame(index=pd.date_range(start=start_date, end=end_date, freq="D"))
    daily.index.name = "date"
    if not milk_daily.empty:
        daily = daily.join(milk_daily, how="left")
    if not cost_daily.empty:
        daily = daily.join(cost_daily, how="left")
    if not health_costs.empty:
        daily = daily.join(health_costs, how="left")
    if not ai_costs.empty:
        daily = daily.join(ai_costs, how="left")

    pd.set_option('future.no_silent_downcasting', True)
    numeric_cols = ['milk_l', 'revenue', 'feed_cost', 'health_cost', 'ai_cost', 'total_cost', 'profit']
    for col in numeric_cols:
        if col not in daily.columns:
            daily[col] = 0.0
        else:
            daily[col] = pd.to_numeric(daily[col], errors='coerce')
    daily = daily.infer_objects(copy=False).fillna(0.0).reset_index()
    daily["total_cost"] = daily["feed_cost"] + daily["health_cost"] + daily["ai_cost"]
    daily["profit"] = daily["revenue"] - daily["total_cost"]

    def aggregate(df_daily, rule):
        df = df_daily.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").resample(rule).sum().reset_index()
        return df

    agg_map = {"Daily": ("D", daily), "Weekly": ("W", aggregate(daily, "W")), "Monthly": ("ME", aggregate(daily, "ME"))}
    rule_code, df_agg = agg_map[granularity]
    
    col1, col2, col3, col4 = st.columns(4)
    total_revenue = df_agg["revenue"].sum()
    total_feed_cost = df_agg["feed_cost"].sum()
    total_health_cost = df_agg["health_cost"].sum()
    total_ai_cost = df_agg["ai_cost"].sum()
    total_profit = df_agg["profit"].sum()
    
    col1.metric("Total Revenue", f"KES {format_with_commas(total_revenue)}")
    col2.metric("Total Feed Cost", f"KES {format_with_commas(total_feed_cost)}")
    col3.metric("Total Health Cost", f"KES {format_with_commas(total_health_cost)}")
    col4.metric("Total AI Cost", f"KES {format_with_commas(total_ai_cost)}")
    
    st.markdown("---")
    
    col5, col6, col7 = st.columns(3)
    col5.metric("Total Profit/Loss", f"KES {format_with_commas(total_profit)}", 
               delta_color="inverse" if total_profit < 0 else "normal")
    
    if total_feed_cost > 0:
        feed_efficiency = total_revenue / total_feed_cost
        col6.metric("Feed Efficiency Ratio", f"{feed_efficiency:.2f}")
    
    if total_revenue > 0:
        profit_margin = (total_profit / total_revenue) * 100
        col7.metric("Profit Margin", f"{profit_margin:.1f}%")
    
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["Revenue & Costs", "Milk Production", "Profit Analysis"])
    
    with tab1:
        fig_rev_cost = go.Figure()
        fig_rev_cost.add_trace(go.Scatter(x=df_agg["date"], y=df_agg["revenue"], 
                                         name="Revenue", line=dict(color='green')))
        fig_rev_cost.add_trace(go.Scatter(x=df_agg["date"], y=df_agg["total_cost"], 
                                         name="Total Cost", line=dict(color='red')))
        fig_rev_cost.update_layout(title="Revenue vs Costs Over Time",
                                  xaxis_title="Date",
                                  yaxis_title="KES")
        st.plotly_chart(fig_rev_cost, use_container_width=True)
    
    with tab2:
        if not milk.empty:
            milk_by_period = milk.groupby("date")["litres_sell"].sum().reset_index()
            fig_milk = px.line(milk_by_period, x="date", y="litres_sell", 
                              title="Milk Production Over Time",
                              labels={"litres_sell": "Liters", "date": "Date"})
            st.plotly_chart(fig_milk, use_container_width=True)
        else:
            st.info("No milk production data available")
    
    with tab3:
        fig_profit = px.area(df_agg, x="date", y="profit", 
                            title="Profit/Loss Over Time",
                            labels={"profit": "KES", "date": "Date"})
        fig_profit.update_traces(line=dict(color='rgba(0,100,80,0.2)'), 
                                 fillcolor='rgba(0,100,80,0.2)')
        st.plotly_chart(fig_profit, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("Cost Breakdown")
    cost_categories = {
        "Feed": total_feed_cost,
        "Health": total_health_cost,
        "AI": total_ai_cost
    }
    
    cost_df = pd.DataFrame({
        "Category": list(cost_categories.keys()),
        "Amount": list(cost_categories.values())
    })
    
    fig_costs = px.pie(cost_df, values="Amount", names="Category", 
                      title="Cost Distribution")
    st.plotly_chart(fig_costs, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("Profit Analysis per Cow")
    profit_per_cow = calculate_profit_per_cow(start_date, end_date)
    
    if not profit_per_cow.empty:
        st.dataframe(profit_per_cow.style.format({
            "Milk Produced (L)": "{:,.1f}",
            "Revenue (KES)": "KES {:,.0f}",
            "Cost (KES)": "KES {:,.0f}",
            "Profit (KES)": "KES {:,.0f}"
        }))
        
        col8, col9 = st.columns(2)
        with col8:
            top_performers = profit_per_cow.nlargest(5, "Profit (KES)")
            st.write("🏆 Top Performers")
            st.dataframe(top_performers[["Cow", "Profit (KES)"]])
        
        with col9:
            bottom_performers = profit_per_cow.nsmallest(5, "Profit (KES)")
            st.write("📉 Lowest Performers")
            st.dataframe(bottom_performers[["Cow", "Profit (KES)"]])
    else:
        st.info("No data available for profit per cow analysis")
    
    st.markdown("---")
    
    st.subheader("Export Reports")
    
    col10, col11, col12 = st.columns(3)
    
    with col10:
        if st.button("📄 Generate PDF Report"):
            if generate_pdf_report(df_agg, profit_per_cow, start_date, end_date):
                st.success("PDF report generated successfully!")
            else:
                st.error("PDF generation failed. Please check dependencies.")
    
    with col11:
        csv = df_agg.to_csv(index=False)
        st.download_button(
            label="📊 Download CSV Data",
            data=csv,
            file_name=f"dairy_report_{start_date}_{end_date}.csv",
            mime="text/csv"
        )
    
    with col12:
        if not profit_per_cow.empty:
            profit_csv = profit_per_cow.to_csv(index=False)
            st.download_button(
                label="🐄 Download Cow Profit Data",
                data=profit_csv,
                file_name=f"cow_profit_{start_date}_{end_date}.csv",
                mime="text/csv"
            )

def generate_pdf_report(df_agg, profit_per_cow, start_date, end_date):
    if not REPORTLAB_AVAILABLE:
        st.error("ReportLab is not available. PDF generation disabled.")
        return False
    
    try:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2*cm, height-2*cm, f"Dairy Farm Management Report")
        c.setFont("Helvetica", 12)
        c.drawString(2*cm, height-2.5*cm, f"Period: {start_date} to {end_date}")
        c.drawString(2*cm, height-3*cm, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2*cm, height-4*cm, "Summary Metrics:")
        c.setFont("Helvetica", 10)
        
        metrics_y = height-4.5*cm
        metrics = [
            f"Total Revenue: KES {format_with_commas(df_agg['revenue'].sum())}",
            f"Total Costs: KES {format_with_commas(df_agg['total_cost'].sum())}",
            f"Total Profit: KES {format_with_commas(df_agg['profit'].sum())}",
            f"Feed Efficiency: {df_agg['revenue'].sum()/df_agg['feed_cost'].sum():.2f}" if df_agg['feed_cost'].sum() > 0 else "Feed Efficiency: N/A"
        ]
        
        for metric in metrics:
            c.drawString(2*cm, metrics_y, metric)
            metrics_y -= 0.5*cm
        
        if not profit_per_cow.empty:
            c.showPage()
            c.setFont("Helvetica-Bold", 14)
            c.drawString(2*cm, height-2*cm, "Profit per Cow Analysis")
            
            headers = ["Cow", "Milk (L)", "Revenue", "Cost", "Profit"]
            col_widths = [3*cm, 3*cm, 3*cm, 3*cm, 3*cm]
            
            c.setFont("Helvetica-Bold", 10)
            y_pos = height-3*cm
            for i, header in enumerate(headers):
                c.drawString(2*cm + sum(col_widths[:i]), y_pos, header)
            
            c.setFont("Helvetica", 9)
            y_pos -= 0.7*cm
            for _, row in profit_per_cow.iterrows():
                if y_pos < 2*cm:
                    c.showPage()
                    y_pos = height-2*cm
                
                values = [
                    row["Cow"],
                    f"{row['Milk Produced (L)']:,.1f}",
                    f"KES {row['Revenue (KES)']:,.0f}",
                    f"KES {row['Cost (KES)']:,.0f}",
                    f"KES {row['Profit (KES)']:,.0f}"
                ]
                
                for i, value in enumerate(values):
                    c.drawString(2*cm + sum(col_widths[:i]), y_pos, value)
                
                y_pos -= 0.5*cm
        
        c.save()
        buffer.seek(0)
        
        st.download_button(
            label="⬇️ Download PDF Report",
            data=buffer,
            file_name=f"dairy_report_{start_date}_{end_date}.pdf",
            mime="application/pdf"
        )
        
        return True
    
    except Exception as e:
        st.error(f"PDF generation error: {e}")
        return False