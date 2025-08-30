import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from utils.data_loader import load_table, to_date
from utils.calculations import calculate_profit_per_cow, calculate_feed_cost_used
from utils.helpers import format_with_commas

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# Add statsmodels import with error handling
try:
    import statsmodels.api as sm
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

def reports_page(start_date, end_date, granularity):
    st.title("📊 Reports")
    
    if granularity == "Daily":
        date_range_str = f"Past 24 hours (from {start_date} to {end_date})"
    elif granularity == "Weekly":
        date_range_str = f"Past 7 days (from {start_date} to {end_date})"
    else:
        date_range_str = f"Past 31 days (from {start_date} to {end_date})"
    
    st.write(f"**Report Period:** {date_range_str}")
    
    # Load all relevant data
    milk_totals = to_date(load_table("milk_totals"), "date")  # Total production for profit calculation
    milk = to_date(load_table("milk_production"), "date")     # Individual cow records
    fr = to_date(load_table("feeds_received"), "date")        # Feeds received
    fu = to_date(load_table("feeds_used"), "date")            # Feeds used
    health = to_date(load_table("health_records"), "date")    # Health records
    ai = to_date(load_table("ai_records"), "ai_date")         # AI records
    employees = load_table("employees")                       # Employees
    
    # Filter data by date range
    if not milk_totals.empty:
        milk_totals = milk_totals[(milk_totals["date"] >= start_date) & (milk_totals["date"] <= end_date)]
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
    if not employees.empty:
        employees["start_date"] = pd.to_datetime(employees["start_date"], errors='coerce')
        employees["end_date"] = pd.to_datetime(employees["end_date"], errors='coerce')
        
        # Calculate monthly salaries (paid on 1st of each month)
        salary_costs = calculate_monthly_salaries(employees, start_date, end_date)
    else:
        salary_costs = pd.DataFrame(columns=["salary_cost"])

    price_per_litre = 43
    milk_daily = pd.DataFrame()
    
    # Use milk_totals for profit calculation (as requested)
    if not milk_totals.empty:
        milk_daily = (milk_totals.groupby("date")["total_litres"].sum().to_frame("milk_l"))
        milk_daily["revenue"] = milk_daily["milk_l"] * price_per_litre
    elif not milk.empty:
        # Fallback to individual records if totals not available
        milk_daily = (milk.groupby("date")["litres_sell"].sum().to_frame("milk_l"))
        milk_daily["revenue"] = milk_daily["milk_l"] * price_per_litre

    # Calculate feed cost used (based on actual consumption, not purchases)
    feed_cost_used = calculate_feed_cost_used(start_date, end_date)
    if not feed_cost_used.empty:
        cost_daily = feed_cost_used.groupby("date")["cost"].sum().to_frame("feed_cost")
    else:
        cost_daily = pd.DataFrame(columns=["feed_cost"])

    # Calculate total feed purchased in KES (not kg)
    if not fr.empty:
        feed_purchased_daily = fr.groupby("date")["cost"].sum().to_frame("feed_purchased_cost")
        total_feed_purchased = fr["cost"].sum()
    else:
        feed_purchased_daily = pd.DataFrame(columns=["feed_purchased_cost"])
        total_feed_purchased = 0

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
    if not feed_purchased_daily.empty:
        daily = daily.join(feed_purchased_daily, how="left")
    if not health_costs.empty:
        daily = daily.join(health_costs, how="left")
    if not ai_costs.empty:
        daily = daily.join(ai_costs, how="left")
    if not salary_costs.empty:
        daily = daily.join(salary_costs, how="left")

    pd.set_option('future.no_silent_downcasting', True)
    numeric_cols = ['milk_l', 'revenue', 'feed_cost', 'feed_purchased_cost', 'health_cost', 'ai_cost', 'salary_cost', 'total_cost', 'profit']
    for col in numeric_cols:
        if col not in daily.columns:
            daily[col] = 0.0
        else:
            daily[col] = pd.to_numeric(daily[col], errors='coerce')
    daily = daily.infer_objects(copy=False).fillna(0.0).reset_index()
    daily["total_cost"] = daily["feed_cost"] + daily["health_cost"] + daily["ai_cost"] + daily["salary_cost"]
    daily["profit"] = daily["revenue"] - daily["total_cost"]

    def aggregate(df_daily, rule):
        df = df_daily.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").resample(rule).sum().reset_index()
        return df

    agg_map = {"Daily": ("D", daily), "Weekly": ("W", aggregate(daily, "W")), "Monthly": ("ME", aggregate(daily, "ME"))}
    rule_code, df_agg = agg_map[granularity]
    
    # Calculate totals
    total_revenue = df_agg["revenue"].sum()
    total_feed_cost = df_agg["feed_cost"].sum()
    total_feed_purchased = df_agg["feed_purchased_cost"].sum() if "feed_purchased_cost" in df_agg.columns else 0
    total_health_cost = df_agg["health_cost"].sum()
    total_ai_cost = df_agg["ai_cost"].sum()
    total_salary_cost = df_agg["salary_cost"].sum()
    total_cost = df_agg["total_cost"].sum()
    total_profit = df_agg["profit"].sum()
    
    # Display metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Revenue", f"KES {format_with_commas(total_revenue)}")
    col2.metric("Total Feed Cost", f"KES {format_with_commas(total_feed_cost)}")
    col3.metric("Total Health Cost", f"KES {format_with_commas(total_health_cost)}")
    col4.metric("Total AI Cost", f"KES {format_with_commas(total_ai_cost)}")
    col5.metric("Total Salary Cost", f"KES {format_with_commas(total_salary_cost)}")
    
    st.markdown("---")
    
    col6, col7, col8, col9 = st.columns(4)
    col6.metric("Total Cost", f"KES {format_with_commas(total_cost)}")
    col7.metric("Total Feed Purchased", f"KES {format_with_commas(total_feed_purchased)}")
    col8.metric("Total Profit/Loss", f"KES {format_with_commas(total_profit)}", 
               delta_color="inverse" if total_profit < 0 else "normal")
    
    if total_feed_cost > 0:
        feed_efficiency = total_revenue / total_feed_cost
        col9.metric("Feed Efficiency Ratio", f"{feed_efficiency:.2f}")
    
    if total_revenue > 0:
        profit_margin = (total_profit / total_revenue) * 100
        st.metric("Profit Margin", f"{profit_margin:.1f}%")
    
    # Add validation check
    if total_feed_cost > 0 and total_revenue > 0:
        calculated_feed_cost_per_liter = total_feed_cost / (total_revenue / price_per_litre)
        calculated_efficiency = price_per_litre / calculated_feed_cost_per_liter
        
        st.write("#### Data Validation")
        st.info(f"""
        - Calculated Feed Cost/L: KES {calculated_feed_cost_per_liter:.2f}
        - Calculated Efficiency: {calculated_efficiency:.2f}
        - Milk Price: KES {price_per_litre}/L
        """)
        
        if abs(calculated_efficiency - feed_efficiency) > 0.1:
            st.error("Inconsistency detected between feed cost and efficiency calculations!")
    
    st.markdown("---")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Revenue & Costs", "Milk Production", "Feed Insights", "Profit Analysis"])
    
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
        # Use milk_totals for production chart if available
        if not milk_totals.empty:
            milk_by_period = milk_totals.groupby("date")["total_litres"].sum().reset_index()
            fig_milk = px.line(milk_by_period, x="date", y="total_litres", 
                              title="Milk Production Over Time (Total Litres)",
                              labels={"total_litres": "Total Liters", "date": "Date"})
            st.plotly_chart(fig_milk, use_container_width=True)
        elif not milk.empty:
            # Fallback to individual records if totals not available
            milk_by_period = milk.groupby("date")["litres_sell"].sum().reset_index()
            fig_milk = px.line(milk_by_period, x="date", y="litres_sell", 
                              title="Milk Production Over Time (Litres Sold)",
                              labels={"litres_sell": "Liters Sold", "date": "Date"})
            st.plotly_chart(fig_milk, use_container_width=True)
        else:
            st.info("No milk production data available")
    
    with tab3:
        st.subheader("Feed Insights and Analysis")
        
        # 1. Feed Cost Per Liter Analysis (CORRECTED)
        st.write("#### Feed Cost Per Liter")
        if not milk_totals.empty and not fu.empty and not fr.empty:
            # Calculate average cost per kg for each feed type
            fr['cost_per_kg'] = fr['cost'] / fr['quantity']
            avg_cost_per_feed = fr.groupby('feed_type')['cost_per_kg'].mean().reset_index()
            
            # Merge with feeds_used to calculate actual cost of used feed
            fu_with_cost = fu.merge(avg_cost_per_feed, on='feed_type', how='left')
            fu_with_cost['actual_cost'] = fu_with_cost['quantity'] * fu_with_cost['cost_per_kg']
            total_feed_used_cost = fu_with_cost['actual_cost'].sum()
            
            # Now calculate feed cost per liter
            total_milk_produced = milk_totals['total_litres'].sum()
            
            if total_milk_produced > 0:
                feed_cost_per_liter = total_feed_used_cost / total_milk_produced
                st.metric("Average Feed Cost Per Liter", f"KES {feed_cost_per_liter:.2f}")
                
                # Add explanation
                if feed_cost_per_liter > price_per_litre:  # If cost exceeds selling price
                    st.warning(f"⚠️ Feed cost (KES {feed_cost_per_liter:.2f}/L) exceeds milk price (KES {price_per_litre}/L)!")
                    st.info("This suggests either: 1) High feed costs, 2) Low milk production, or 3) Data entry errors")
                elif feed_cost_per_liter > price_per_litre * 0.6:  # If cost is more than 60% of selling price
                    st.warning(f"⚠️ High feed cost: {feed_cost_per_liter/price_per_litre*100:.1f}% of milk price")
                else:
                    st.success(f"✓ Feed cost is {feed_cost_per_liter/price_per_litre*100:.1f}% of milk price")
                
                # Trend over time
                milk_daily_totals = milk_totals.groupby("date")["total_litres"].sum().reset_index()
                feed_daily_cost = fu_with_cost.groupby("date")["actual_cost"].sum().reset_index()
                
                merged_daily = milk_daily_totals.merge(feed_daily_cost, on="date", how="left").fillna(0)
                merged_daily["feed_cost_per_liter"] = merged_daily.apply(
                    lambda row: row["actual_cost"] / row["total_litres"] if row["total_litres"] > 0 else 0, axis=1
                )
                
                fig_cost_per_liter = px.line(merged_daily, x="date", y="feed_cost_per_liter",
                                           title="Feed Cost Per Liter Over Time (Corrected Calculation)",
                                           labels={"feed_cost_per_liter": "Cost Per Liter (KES)", "date": "Date"})
                st.plotly_chart(fig_cost_per_liter, use_container_width=True)
            else:
                st.info("No milk production data available for feed cost per liter calculation")
        else:
            st.info("Need milk production, feed usage, and feed receipt data for feed cost analysis")
        
        # 2. Feed Efficiency Ratio Explanation
        st.write("#### Feed Efficiency Ratio")
        if total_feed_cost > 0 and total_revenue > 0:
            feed_efficiency = total_revenue / total_feed_cost
            st.metric("Feed Efficiency Ratio", f"{feed_efficiency:.2f}")
            
            # Add interpretation
            if feed_efficiency < 1.5:
                st.error("Low efficiency: Feed costs are too high relative to milk revenue")
                st.info("Each KES 1 spent on feed generates only KES {:.2f} in milk revenue".format(feed_efficiency))
            elif feed_efficiency < 2.5:
                st.warning("Moderate efficiency: Room for improvement in feed utilization")
                st.info("Each KES 1 spent on feed generates KES {:.2f} in milk revenue".format(feed_efficiency))
            else:
                st.success("Good efficiency: Feed is being converted to milk effectively")
                st.info("Each KES 1 spent on feed generates KES {:.2f} in milk revenue".format(feed_efficiency))
            
            st.info("""
            **Interpretation Guide:**
            - < 1.5: Poor efficiency (losing money on feed)
            - 1.5-2.5: Moderate efficiency 
            - > 2.5: Good efficiency (each KES 1 of feed generates > KES 2.5 of milk revenue)
            """)
        
        # 3. Feed Consumption Patterns
        st.write("#### Feed Consumption Patterns")
        if not fu.empty:
            # Consumption by category
            consumption_by_category = fu.groupby("category")["quantity"].sum().reset_index()
            fig_category = px.pie(consumption_by_category, values="quantity", names="category",
                                 title="Feed Consumption by Cow Category")
            st.plotly_chart(fig_category, use_container_width=True)
            
            # Consumption trends over time
            consumption_trend = fu.groupby("date")["quantity"].sum().reset_index()
            fig_trend = px.line(consumption_trend, x="date", y="quantity",
                               title="Feed Consumption Over Time",
                               labels={"quantity": "Quantity (kg)", "date": "Date"})
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No feed usage data available")
        
        # 4. Feed Cost Breakdown
        st.write("#### Feed Cost Breakdown")
        if not fr.empty:
            cost_by_feed_type = fr.groupby("feed_type")["cost"].sum().reset_index()
            fig_feed_cost = px.pie(cost_by_feed_type, values="cost", names="feed_type",
                                  title="Feed Cost Distribution by Type")
            st.plotly_chart(fig_feed_cost, use_container_width=True)
            
            # Average cost per kg for each feed type
            fr_with_avg = fr.copy()
            fr_with_avg["cost_per_kg"] = fr_with_avg["cost"] / fr_with_avg["quantity"]
            avg_cost_by_type = fr_with_avg.groupby("feed_type")["cost_per_kg"].mean().reset_index()
            
            fig_avg_cost = px.bar(avg_cost_by_type, x="feed_type", y="cost_per_kg",
                                 title="Average Cost Per Kg by Feed Type",
                                 labels={"feed_type": "Feed Type", "cost_per_kg": "Cost Per Kg (KES)"})
            st.plotly_chart(fig_avg_cost, use_container_width=True)
        else:
            st.info("No feed receipt data available")
        
        # 5. Feed-to-Production Correlation
        st.write("#### Feed-to-Production Correlation")
        if not fu.empty and not milk_totals.empty:
            # Aggregate data by date
            feed_by_date = fu.groupby("date")["quantity"].sum().reset_index()
            milk_by_date = milk_totals.groupby("date")["total_litres"].sum().reset_index()
            
            merged_data = feed_by_date.merge(milk_by_date, on="date", how="inner")
            
            # Check if statsmodels is available for trendline
            if HAS_STATSMODELS:
                fig_correlation = px.scatter(merged_data, x="quantity", y="total_litres",
                                           title="Feed Consumption vs Milk Production",
                                           labels={"quantity": "Feed Consumed (kg)", "total_litres": "Milk Produced (L)"},
                                           trendline="ols")
            else:
                fig_correlation = px.scatter(merged_data, x="quantity", y="total_litres",
                                           title="Feed Consumption vs Milk Production",
                                           labels={"quantity": "Feed Consumed (kg)", "total_litres": "Milk Produced (L)"})
                st.info("Install 'statsmodels' package to see trendlines")
            
            st.plotly_chart(fig_correlation, use_container_width=True)
            
            # Calculate correlation coefficient
            correlation = merged_data["quantity"].corr(merged_data["total_litres"])
            st.metric("Correlation Coefficient", f"{correlation:.2f}")
            
            # Interpretation
            if correlation > 0.7:
                st.success("Strong positive correlation: Feed consumption strongly predicts milk production")
            elif correlation > 0.3:
                st.info("Moderate positive correlation: Feed consumption somewhat predicts milk production")
            elif correlation > -0.3:
                st.warning("Weak correlation: Little relationship between feed and production")
            else:
                st.error("Negative correlation: More feed associated with less milk (data issue?)")
        else:
            st.info("Need both feed usage and milk production data for correlation analysis")
    
    with tab4:
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
        "AI": total_ai_cost,
        "Salaries": total_salary_cost
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

def calculate_monthly_salaries(employees, start_date, end_date):
    """
    Calculate monthly salaries paid on the 1st of each month
    """
    # Create a date range for the 1st of each month in the period
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    # Generate all 1st of month dates in the range
    monthly_dates = pd.date_range(
        start=start_dt.replace(day=1),
        end=end_dt.replace(day=1),
        freq='MS'
    )
    
    # Create a DataFrame to store salary costs
    salary_costs = pd.DataFrame(index=monthly_dates, columns=["salary_cost"])
    salary_costs.index.name = "date"
    salary_costs["salary_cost"] = 0.0
    
    # For each month, add salaries for employees active on the 1st of that month
    for month_start in monthly_dates:
        total_monthly_salary = 0
        
        for _, emp in employees.iterrows():
            emp_start = pd.to_datetime(emp["start_date"])
            emp_end = pd.to_datetime(emp["end_date"]) if pd.notna(emp["end_date"]) else pd.Timestamp.max
            
            # Check if employee was active on the 1st of this month
            if emp_start <= month_start <= emp_end:
                total_monthly_salary += emp["salary"]
        
        salary_costs.loc[month_start, "salary_cost"] = total_monthly_salary
    
    return salary_costs

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
            f"Feed Efficiency: {df_agg['revenue'].sum()/df_agg['feed_cost'].sum():.2f}" if df_agg['feed_cost'].sum() > 0 else "Feed Efficiency: N/A",
            f"Total Salary Cost: KES {format_with_commas(df_agg['salary_cost'].sum())}"
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
