"""
Luminary Insurance Weekly Profit Trending Dashboard
Portfolio version - reads from CSV data file
"""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import os

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIGURATION & STYLING
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Luminary Profit Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main .block-container {
        padding: 1.5rem 2rem;
        max-width: 1400px;
    }
    
    .dashboard-title {
        font-size: 2.25rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.25rem;
    }
    
    .dashboard-subtitle {
        color: #6b7280;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #374151;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #3b82f6;
        margin-bottom: 1rem;
        margin-top: 1.5rem;
    }
    
    .profit-equation {
        background: #f8fafc;
        padding: 1.25rem;
        border-radius: 8px;
        border-left: 4px solid #8b5cf6;
        font-family: monospace;
        font-size: 0.85rem;
        line-height: 1.7;
        color: #1e293b;
    }
    
    .metric-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_REALIZATION_RATE = 0.60
TENURED_DAILY_SALARY = 14.42 * 8  # $115.36 per day
TRAINING_DAILY_SALARY = 28.85 * 8  # $230.80 per day
DEFAULT_NON_SALES_SALARY = 14500
MIN_PRESENT_AGENTS_THRESHOLD = 25  # Minimum present agents to consider a valid working day

# Path to data file - works both locally and on Streamlit Cloud
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weekly_metrics_data.csv')

# Fallback if the above doesn't work (e.g., on Streamlit Cloud)
if not os.path.exists(DATA_FILE):
    DATA_FILE = 'weekly_metrics_data.csv'


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def fetch_weekly_metrics():
    """
    Load weekly metrics from CSV file.
    Returns a DataFrame with weekly aggregated data.
    """
    
    try:
        df = pd.read_csv(DATA_FILE)
        # Normalize column names to uppercase
        df.columns = [c.upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PROFIT CALCULATION
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_weekly_profit(row, params):
    """Calculate weekly profit based on the provided formula."""
    
    num_agents = row['NUM_AGENTS']
    attendance = row['ATTENDANCE_RATE']
    effective_agents = num_agents * attendance
    
    leads_per_agent = row['LEADS_PER_AGENT']
    close_rate = row['CLOSE_RATE']
    avg_premium = row['AVG_ANNUAL_PREMIUM']
    tenured_agents = row['TENURED_AGENTS']
    training_agents = row['TRAINING_AGENTS']
    total_leads = row['TOTAL_LEADS']
    total_sales = row['TOTAL_SALES']
    business_days = row['BUSINESS_DAYS']
    cost_per_call = row['COST_PER_CALL']
    avg_commission_rate = row['AVG_COMMISSION_RATE']
    overhead_cost_from_data = row['OVERHEAD_COST_FROM_DATA']
    
    realization = params['realization_rate']
    tenured_salary = params['tenured_daily_salary']
    training_salary = params['training_daily_salary']
    non_sales_salary = params['non_sales_salary']
    
    # REVENUE
    # Use total_leads directly (already filtered to active agents)
    # Revenue = total_leads * close_rate * avg_premium * avg_commission_rate * realization
    weekly_revenue = (
        total_leads * 
        close_rate * 
        avg_premium * 
        avg_commission_rate * 
        realization
    )
    
    # Total annual premium sold this week
    total_premium_sold = total_sales * avg_premium
    
    # COSTS
    # Sales Salary
    tenured_salary_cost = tenured_agents * tenured_salary * business_days
    training_salary_cost = training_agents * training_salary * business_days
    sales_salary_cost = tenured_salary_cost + training_salary_cost
    
    # Sales Commissions (20% for tenured, 5% for training on total premium sold)
    # Approximate split based on agent ratio
    if num_agents > 0:
        tenured_ratio = tenured_agents / num_agents
        training_ratio = training_agents / num_agents
    else:
        tenured_ratio = 0
        training_ratio = 0
    
    tenured_commission = total_premium_sold * tenured_ratio * 0.20
    training_commission = total_premium_sold * training_ratio * 0.05
    sales_commission_cost = tenured_commission + training_commission
    
    # Non-Sales Salary
    non_sales_salary_cost = non_sales_salary * business_days
    
    # Marketing (lead cost)
    marketing_cost = total_leads * cost_per_call
    
    # Overhead (from data - already weekly sum)
    overhead_cost = overhead_cost_from_data
    
    total_costs = sales_salary_cost + sales_commission_cost + non_sales_salary_cost + marketing_cost + overhead_cost
    
    # PROFIT
    profit = weekly_revenue - total_costs
    daily_profit = profit / business_days if business_days > 0 else 0
    
    return {
        'WEEKLY_REVENUE': weekly_revenue,
        'SALES_SALARY_COST': sales_salary_cost,
        'SALES_COMMISSION_COST': sales_commission_cost,
        'NON_SALES_SALARY_COST': non_sales_salary_cost,
        'MARKETING_COST': marketing_cost,
        'OVERHEAD_COST': overhead_cost,
        'TOTAL_COSTS': total_costs,
        'WEEKLY_PROFIT': profit,
        'DAILY_PROFIT': daily_profit,
        'PROFIT_PER_AGENT': profit / num_agents if num_agents > 0 else 0
    }


def apply_profit_calculations(df, params):
    """Apply profit calculations to all rows in the dataframe."""
    results = df.apply(lambda row: calculate_weekly_profit(row, params), axis=1)
    results_df = pd.DataFrame(results.tolist())
    return pd.concat([df.reset_index(drop=True), results_df], axis=1)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTION FOR CENTERED Y-AXIS CHARTS
# ═══════════════════════════════════════════════════════════════════════════════

def create_centered_line_chart(df, x_col, y_col, color, height=150, padding_pct=0.15):
    """
    Create an Altair line chart with y-axis centered around the data range.
    
    Args:
        df: DataFrame with the data
        x_col: Column name for x-axis (typically datetime)
        y_col: Column name for y-axis (the metric)
        color: Hex color for the line
        height: Chart height in pixels
        padding_pct: Percentage padding above and below min/max (default 15%)
    
    Returns:
        Altair chart object
    """
    y_min = df[y_col].min()
    y_max = df[y_col].max()
    y_range = y_max - y_min
    
    # Add padding to create floor and ceiling
    if y_range > 0:
        padding = y_range * padding_pct
        domain_min = max(0, y_min - padding)  # Don't go below 0 for most metrics
        domain_max = y_max + padding
    else:
        # Handle case where all values are the same
        domain_min = y_min * 0.9 if y_min > 0 else y_min - 1
        domain_max = y_max * 1.1 if y_max > 0 else y_max + 1
    
    chart = alt.Chart(df).mark_line(strokeWidth=2).encode(
        x=alt.X(f'{x_col}:T', title=None, axis=alt.Axis(labels=False)),
        y=alt.Y(f'{y_col}:Q', 
                title=None, 
                scale=alt.Scale(domain=[domain_min, domain_max]))
    ).properties(height=height).configure_mark(
        color=color
    ).configure_axis(
        grid=True,
        gridColor='#f0f0f0'
    )
    
    return chart


def create_centered_line_chart_with_points(df, x_col, y_col, color, height=150, padding_pct=0.15):
    """
    Create an Altair line chart with points and y-axis centered around the data range.
    """
    y_min = df[y_col].min()
    y_max = df[y_col].max()
    y_range = y_max - y_min
    
    # Add padding to create floor and ceiling
    if y_range > 0:
        padding = y_range * padding_pct
        domain_min = max(0, y_min - padding)
        domain_max = y_max + padding
    else:
        domain_min = y_min * 0.9 if y_min > 0 else y_min - 1
        domain_max = y_max * 1.1 if y_max > 0 else y_max + 1
    
    base = alt.Chart(df).encode(
        x=alt.X(f'{x_col}:T', title=None, axis=alt.Axis(labels=False)),
        y=alt.Y(f'{y_col}:Q', 
                title=None, 
                scale=alt.Scale(domain=[domain_min, domain_max]))
    )
    
    line = base.mark_line(strokeWidth=2, color=color)
    points = base.mark_circle(size=30, color=color)
    
    chart = (line + points).properties(height=height)
    
    return chart


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # Header
    st.markdown('<div class="dashboard-title">📊 Luminary Profit Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-subtitle">Weekly Agent Performance & Profitability Analysis</div>', unsafe_allow_html=True)
    
    # Sidebar - Parameters
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("💰 Revenue Parameters")
        
        realization_rate = st.slider(
            "Realization Rate (π)",
            min_value=0, max_value=100,
            value=int(DEFAULT_REALIZATION_RATE * 100),
            step=1,
            format="%d%%"
        ) / 100.0
        
        st.divider()
        st.caption(f"ℹ️ Only days with ≥{MIN_PRESENT_AGENTS_THRESHOLD} present agents are counted as valid working days.")
        st.caption("ℹ️ Overhead is sourced from historical data. For the most recent 2 months, the average from months 3-4 ago is used due to delayed cost recording.")
    
    params = {
        'realization_rate': realization_rate,
        'tenured_daily_salary': TENURED_DAILY_SALARY,
        'training_daily_salary': TRAINING_DAILY_SALARY,
        'non_sales_salary': DEFAULT_NON_SALES_SALARY
    }
    
    # Load data from CSV
    with st.spinner("Loading data..."):
        df = fetch_weekly_metrics()
        if df is None or df.empty:
            st.error("No data available. Please check the data file.")
            st.stop()
    
    # Apply profit calculations
    df = apply_profit_calculations(df, params)
    
    # Ensure WEEK_START is datetime
    df['WEEK_START'] = pd.to_datetime(df['WEEK_START'])
    
    # Drop earliest week (may be incomplete)
    if len(df) > 1:
        df = df.iloc[1:].reset_index(drop=True)
    
    # Get latest week for KPIs
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    # ═══════════════════════════════════════════════════════════════════════════
    # KPI CARDS
    # ═══════════════════════════════════════════════════════════════════════════
    
    st.markdown('<div class="section-header">📈 Key Performance Indicators (Latest Week)</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        delta = latest['WEEKLY_PROFIT'] - prev['WEEKLY_PROFIT']
        st.metric(
            label="Weekly Profit",
            value=f"${latest['WEEKLY_PROFIT']:,.0f}",
            delta=f"${delta:,.0f}"
        )
    
    with col2:
        delta = latest['NUM_AGENTS'] - prev['NUM_AGENTS']
        st.metric(
            label="Active Agents",
            value=f"{latest['NUM_AGENTS']:.0f}",
            delta=f"{delta:+.0f}"
        )
    
    with col3:
        delta = (latest['ATTENDANCE_RATE'] - prev['ATTENDANCE_RATE']) * 100
        st.metric(
            label="Attendance Rate",
            value=f"{latest['ATTENDANCE_RATE']:.2%}",
            delta=f"{delta:+.2f}%"
        )
    
    with col4:
        delta = (latest['CLOSE_RATE'] - prev['CLOSE_RATE']) * 100
        st.metric(
            label="Close Rate",
            value=f"{latest['CLOSE_RATE']:.2%}",
            delta=f"{delta:+.2f}%"
        )
    
    with col5:
        delta = latest['AVG_ANNUAL_PREMIUM'] - prev['AVG_ANNUAL_PREMIUM']
        st.metric(
            label="Avg Premium",
            value=f"${latest['AVG_ANNUAL_PREMIUM']:,.0f}",
            delta=f"${delta:+,.0f}"
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROFIT TRENDING
    # ═══════════════════════════════════════════════════════════════════════════
    
    st.markdown('<div class="section-header">💹 Profit Trending</div>', unsafe_allow_html=True)
    
    # Prepare chart data
    chart_df = df[['WEEK_START', 'WEEKLY_PROFIT']].copy()
    chart_df['WEEKLY_PROFIT'] = chart_df['WEEKLY_PROFIT'].round(0)
    
    st.subheader("Weekly Profit")
    profit_chart = alt.Chart(chart_df).mark_bar(size=20).encode(
        x=alt.X('WEEK_START:T', title='Week'),
        y=alt.Y('WEEKLY_PROFIT:Q', title='Profit ($)', axis=alt.Axis(format=',.0f')),
        color=alt.condition(
            alt.datum.WEEKLY_PROFIT > 0,
            alt.value('#22c55e'),
            alt.value('#ef4444')
        )
    ).properties(height=300)
    st.altair_chart(profit_chart, use_container_width=True)
    
    # Cost Breakdown
    st.subheader("Cost Breakdown Over Time")
    cost_df = df[['WEEK_START', 'SALES_SALARY_COST', 'SALES_COMMISSION_COST', 'NON_SALES_SALARY_COST', 'MARKETING_COST', 'OVERHEAD_COST']].copy()
    cost_df['SALES_SALARY_COST'] = cost_df['SALES_SALARY_COST'].round(0)
    cost_df['SALES_COMMISSION_COST'] = cost_df['SALES_COMMISSION_COST'].round(0)
    cost_df['NON_SALES_SALARY_COST'] = cost_df['NON_SALES_SALARY_COST'].round(0)
    cost_df['MARKETING_COST'] = cost_df['MARKETING_COST'].round(0)
    cost_df['OVERHEAD_COST'] = cost_df['OVERHEAD_COST'].round(0)
    cost_melted = cost_df.melt(id_vars=['WEEK_START'], 
                               value_vars=['SALES_SALARY_COST', 'SALES_COMMISSION_COST', 'NON_SALES_SALARY_COST', 'MARKETING_COST', 'OVERHEAD_COST'],
                               var_name='Cost Type', value_name='Amount')
    cost_melted['Cost Type'] = cost_melted['Cost Type'].map({
        'SALES_SALARY_COST': 'Sales Salary',
        'SALES_COMMISSION_COST': 'Sales Commissions',
        'NON_SALES_SALARY_COST': 'Non-Sales Salary',
        'MARKETING_COST': 'Marketing',
        'OVERHEAD_COST': 'Overhead'
    })
    cost_chart = alt.Chart(cost_melted).mark_bar(size=20).encode(
        x=alt.X('WEEK_START:T', title='Week'),
        y=alt.Y('Amount:Q', title='Cost ($)', axis=alt.Axis(format=',.0f')),
        color=alt.Color('Cost Type:N', scale=alt.Scale(
            domain=['Sales Salary', 'Sales Commissions', 'Non-Sales Salary', 'Marketing', 'Overhead'],
            range=['#ef4444', '#f97316', '#eab308', '#22c55e', '#6b7280']
        )),
        order=alt.Order('Cost Type:N')
    ).properties(height=300)
    st.altair_chart(cost_chart, use_container_width=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INDIVIDUAL METRICS (with centered y-axis)
    # ═══════════════════════════════════════════════════════════════════════════
    
    st.markdown('<div class="section-header">📊 Metric Time Series</div>', unsafe_allow_html=True)
    
    # Row 1: Agent metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.caption("Number of Agents")
        agents_df = df[['WEEK_START', 'NUM_AGENTS']].copy()
        agents_df['NUM_AGENTS'] = agents_df['NUM_AGENTS'].round(0)
        chart = create_centered_line_chart_with_points(agents_df, 'WEEK_START', 'NUM_AGENTS', '#3b82f6', height=150)
        st.altair_chart(chart, use_container_width=True)
    
    with col2:
        st.caption("Tenured Agents")
        tenured_df = df[['WEEK_START', 'TENURED_AGENTS']].copy()
        chart = create_centered_line_chart_with_points(tenured_df, 'WEEK_START', 'TENURED_AGENTS', '#3b82f6', height=150)
        st.altair_chart(chart, use_container_width=True)
    
    with col3:
        st.caption("Training Agents")
        training_df = df[['WEEK_START', 'TRAINING_AGENTS']].copy()
        chart = create_centered_line_chart_with_points(training_df, 'WEEK_START', 'TRAINING_AGENTS', '#93c5fd', height=150)
        st.altair_chart(chart, use_container_width=True)
    
    with col4:
        st.caption("Attendance Rate")
        att_df = df[['WEEK_START', 'ATTENDANCE_RATE']].copy()
        chart = create_centered_line_chart_with_points(att_df, 'WEEK_START', 'ATTENDANCE_RATE', '#8b5cf6', height=150)
        st.altair_chart(chart, use_container_width=True)
    
    # Row 2: Performance metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.caption("Leads per Agent")
        leads_df = df[['WEEK_START', 'LEADS_PER_AGENT']].copy()
        leads_df['LEADS_PER_AGENT'] = leads_df['LEADS_PER_AGENT'].round(2)
        chart = create_centered_line_chart_with_points(leads_df, 'WEEK_START', 'LEADS_PER_AGENT', '#f59e0b', height=150)
        st.altair_chart(chart, use_container_width=True)
    
    with col2:
        st.caption("Close Rate")
        close_df = df[['WEEK_START', 'CLOSE_RATE']].copy()
        chart = create_centered_line_chart_with_points(close_df, 'WEEK_START', 'CLOSE_RATE', '#22c55e', height=150)
        st.altair_chart(chart, use_container_width=True)
    
    with col3:
        st.caption("Avg Annual Premium")
        prem_df = df[['WEEK_START', 'AVG_ANNUAL_PREMIUM']].copy()
        prem_df['AVG_ANNUAL_PREMIUM'] = prem_df['AVG_ANNUAL_PREMIUM'].round(0)
        chart = create_centered_line_chart_with_points(prem_df, 'WEEK_START', 'AVG_ANNUAL_PREMIUM', '#ef4444', height=150)
        st.altair_chart(chart, use_container_width=True)
    
    with col4:
        st.caption("Cost Per Call")
        cpc_df = df[['WEEK_START', 'COST_PER_CALL']].copy()
        cpc_df['COST_PER_CALL'] = cpc_df['COST_PER_CALL'].round(0)
        chart = create_centered_line_chart_with_points(cpc_df, 'WEEK_START', 'COST_PER_CALL', '#f59e0b', height=150)
        st.altair_chart(chart, use_container_width=True)
    
    # Row 3: Volume metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.caption("Total Leads")
        total_leads_df = df[['WEEK_START', 'TOTAL_LEADS']].copy()
        chart = create_centered_line_chart_with_points(total_leads_df, 'WEEK_START', 'TOTAL_LEADS', '#06b6d4', height=150)
        st.altair_chart(chart, use_container_width=True)
    
    with col2:
        st.caption("Total Sales")
        total_sales_df = df[['WEEK_START', 'TOTAL_SALES']].copy()
        chart = create_centered_line_chart_with_points(total_sales_df, 'WEEK_START', 'TOTAL_SALES', '#22c55e', height=150)
        st.altair_chart(chart, use_container_width=True)
    
    with col3:
        st.caption("Avg Commission Rate")
        comm_df = df[['WEEK_START', 'AVG_COMMISSION_RATE']].copy()
        chart = create_centered_line_chart_with_points(comm_df, 'WEEK_START', 'AVG_COMMISSION_RATE', '#a855f7', height=150)
        st.altair_chart(chart, use_container_width=True)
    
    with col4:
        st.caption("Underwriting Mix")
        uw_df = df[['WEEK_START', 'PREFERRED_PCT', 'STANDARD_PCT', 'GRADED_PCT', 'GI_PCT']].copy()
        uw_melted = uw_df.melt(id_vars=['WEEK_START'],
                               value_vars=['PREFERRED_PCT', 'STANDARD_PCT', 'GRADED_PCT', 'GI_PCT'],
                               var_name='Class', value_name='Percentage')
        uw_melted['Class'] = uw_melted['Class'].map({
            'PREFERRED_PCT': 'Preferred',
            'STANDARD_PCT': 'Standard',
            'GRADED_PCT': 'Graded',
            'GI_PCT': 'GI'
        })
        uw_chart = alt.Chart(uw_melted).mark_area().encode(
            x=alt.X('WEEK_START:T', title=None, axis=alt.Axis(labels=False)),
            y=alt.Y('Percentage:Q', stack='normalize', title=None, axis=alt.Axis(format='%')),
            color=alt.Color('Class:N', scale=alt.Scale(
                domain=['Preferred', 'Standard', 'Graded', 'GI'],
                range=['#22c55e', '#3b82f6', '#f59e0b', '#ef4444']
            ), legend=alt.Legend(orient='bottom', direction='horizontal', titleAnchor='middle'))
        ).properties(height=150)
        st.altair_chart(uw_chart, use_container_width=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROFIT EQUATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    st.markdown('<div class="section-header">📐 Profit Calculation Formula</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="profit-equation">
        <strong>REVENUE CALCULATION</strong><br><br>
        Revenue = N × λ × α × β × κ × π<br><br>
        Where:<br>
        &nbsp;&nbsp;N = Number of agents × Attendance rate<br>
        &nbsp;&nbsp;λ = Leads per agent<br>
        &nbsp;&nbsp;α = Close rate<br>
        &nbsp;&nbsp;β = Average annual premium<br>
        &nbsp;&nbsp;κ = Weekly avg commission rate (from underwriting mix)<br>
        &nbsp;&nbsp;π = Realization rate
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="profit-equation">
        <strong>COST CALCULATION</strong><br><br>
        Costs = Sales Salary + Sales Commissions + Non-Sales Salary + Marketing + Overhead<br><br>
        Where:<br>
        &nbsp;&nbsp;Sales Salary = (Tenured × ${TENURED_DAILY_SALARY:,.2f}) + (Training × ${TRAINING_DAILY_SALARY:,.2f})<br>
        &nbsp;&nbsp;Sales Commissions = (Tenured Premium × 20%) + (Training Premium × 5%)<br>
        &nbsp;&nbsp;Non-Sales Salary = ${DEFAULT_NON_SALES_SALARY:,}/day<br>
        &nbsp;&nbsp;Marketing = Total Leads × CPC (from data)<br>
        &nbsp;&nbsp;Overhead = Weekly sum from historical data<br>
        &nbsp;&nbsp;&nbsp;&nbsp;<em>Note: Recent 2 months use avg from months 3-4 ago</em><br><br>
        <strong>Profit = Revenue - Costs</strong><br><br>
        <em>Note: Only days with ≥{MIN_PRESENT_AGENTS_THRESHOLD} present agents count as valid business days.</em>
        </div>
        """, unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DATA TABLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    with st.expander("📋 View Raw Data"):
        display_cols = [
            'WEEK_START', 'NUM_AGENTS', 'TENURED_AGENTS', 'TRAINING_AGENTS',
            'ATTENDANCE_RATE', 'BUSINESS_DAYS', 'LEADS_PER_AGENT', 'CLOSE_RATE', 'AVG_ANNUAL_PREMIUM',
            'WEEKLY_REVENUE', 'SALES_SALARY_COST', 'SALES_COMMISSION_COST', 
            'NON_SALES_SALARY_COST', 'MARKETING_COST', 'OVERHEAD_COST',
            'TOTAL_COSTS', 'WEEKLY_PROFIT'
        ]
        
        display_df = df[display_cols].copy()
        display_df.columns = [
            'Week', 'Agents', 'Tenured', 'Training', 'Attendance', 'Biz Days',
            'Leads/Agent', 'Close Rate', 'Avg Premium',
            'Revenue', 'Sales Salary', 'Sales Commission',
            'Non-Sales Salary', 'Marketing', 'Overhead',
            'Total Costs', 'Profit'
        ]
        
        # Format for display
        format_df = display_df.copy()
        format_df['Attendance'] = format_df['Attendance'].apply(lambda x: f"{x:.2%}")
        format_df['Close Rate'] = format_df['Close Rate'].apply(lambda x: f"{x:.2%}")
        format_df['Leads/Agent'] = format_df['Leads/Agent'].apply(lambda x: f"{x:.2f}")
        format_df['Avg Premium'] = format_df['Avg Premium'].apply(lambda x: f"${x:,.0f}")
        format_df['Revenue'] = format_df['Revenue'].apply(lambda x: f"${x:,.0f}")
        format_df['Sales Salary'] = format_df['Sales Salary'].apply(lambda x: f"${x:,.0f}")
        format_df['Sales Commission'] = format_df['Sales Commission'].apply(lambda x: f"${x:,.0f}")
        format_df['Non-Sales Salary'] = format_df['Non-Sales Salary'].apply(lambda x: f"${x:,.0f}")
        format_df['Marketing'] = format_df['Marketing'].apply(lambda x: f"${x:,.0f}")
        format_df['Overhead'] = format_df['Overhead'].apply(lambda x: f"${x:,.0f}")
        format_df['Total Costs'] = format_df['Total Costs'].apply(lambda x: f"${x:,.0f}")
        format_df['Profit'] = format_df['Profit'].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(format_df, use_container_width=True, hide_index=True)
        
        # Download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name="profit_trending_data.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()
