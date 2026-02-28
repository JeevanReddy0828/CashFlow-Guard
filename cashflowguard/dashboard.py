"""
CashFlowGuard Dashboard - Enhanced with Outreach & Tracking
Run with: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import sys

# Add project to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Page config
st.set_page_config(
    page_title="CashFlowGuard Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
    }
    .action-button {
        background: #4CAF50;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        border: none;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data(data_dir):
    """Load CSV files directly"""
    data_path = Path(data_dir)
    customers = pd.read_csv(data_path / "customers.csv")
    invoices = pd.read_csv(data_path / "invoices.csv")
    payments = pd.read_csv(data_path / "payments.csv")
    
    # Parse all dates immediately
    invoices["due_date"] = pd.to_datetime(invoices["due_date"], errors='coerce')
    invoices["issue_date"] = pd.to_datetime(invoices["issue_date"], errors='coerce')
    payments["payment_date"] = pd.to_datetime(payments["payment_date"], errors='coerce')
    
    return customers, invoices, payments

def format_currency(value):
    """Format as currency"""
    if pd.isna(value):
        return "$0"
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"${value/1_000:.1f}K"
    else:
        return f"${value:.2f}"

def calculate_dso(invoices, payments):
    """Calculate Days Sales Outstanding"""
    open_ar = invoices[invoices["status"] == "open"]["invoice_amount"].sum()
    recent_date = invoices["issue_date"].max()
    ninety_days_ago = recent_date - pd.Timedelta(days=90)
    recent_revenue = invoices[
        invoices["issue_date"] >= ninety_days_ago
    ]["invoice_amount"].sum()
    
    if recent_revenue > 0:
        daily_revenue = recent_revenue / 90
        dso = open_ar / daily_revenue if daily_revenue > 0 else 0
    else:
        dso = 0
    
    return dso

def get_aging_bucket(days):
    """Categorize by aging bucket"""
    if days <= 0:
        return "Current"
    elif days <= 30:
        return "1-30 days"
    elif days <= 60:
        return "31-60 days"
    elif days <= 90:
        return "61-90 days"
    else:
        return "90+ days"

def load_outreach_features():
    """Try to load outreach features if available"""
    try:
        from cashflowguard.collections.message_generator import MessageGenerator
        from cashflowguard.collections.collections_scheduler import CollectionsScheduler
        from cashflowguard.core.action_logger import ActionLogger
        return MessageGenerator, CollectionsScheduler, ActionLogger, True
    except ImportError:
        return None, None, None, False

def main():
    # Load outreach features
    MessageGenerator, CollectionsScheduler, ActionLogger, outreach_available = load_outreach_features()
    
    # Sidebar
    st.sidebar.markdown("# 💰 CashFlowGuard")
    st.sidebar.markdown("### Invoice Collections Management")
    
    # Data source selection
    data_source = st.sidebar.selectbox(
        "Select Data Source",
        ["UCI Real Data", "Realistic B2B", "Sample Data"],
        index=0
    )
    
    data_dirs = {
        "UCI Real Data": "E:/CashFlowGuard/data/uci",
        "Realistic B2B": "data/real",
        "Sample Data": "data/sample"
    }
    
    data_dir = data_dirs[data_source]
    
    # Feature flags
    if outreach_available:
        st.sidebar.success("✅ Outreach & Scheduling Enabled")
    else:
        st.sidebar.info("ℹ️ Install outreach modules for full features")
    
    # Load data
    try:
        with st.spinner("Loading data..."):
            customers, invoices, payments = load_data(data_dir)
        st.sidebar.success(f"✅ Loaded {len(invoices):,} invoices")
        st.sidebar.info(f"📊 {len(customers):,} customers")
        st.sidebar.info(f"💳 {len(payments):,} payments")
    except Exception as e:
        st.error(f"❌ Error loading data from {data_dir}")
        st.error(f"Details: {e}")
        st.info("💡 Make sure the data directory exists and contains customers.csv, invoices.csv, payments.csv")
        st.stop()
    
    # Main header
    st.markdown('<div class="main-header">📊 CashFlowGuard Dashboard</div>', unsafe_allow_html=True)
    st.markdown(f"**Data Source:** {data_source} | **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Calculate metrics
    open_invoices = invoices[invoices["status"] == "open"].copy()
    total_ar = open_invoices["invoice_amount"].sum()
    
    now = pd.Timestamp.now()
    overdue = open_invoices[open_invoices["due_date"] < now]
    overdue_ar = overdue["invoice_amount"].sum()
    overdue_pct = (overdue_ar / total_ar * 100) if total_ar > 0 else 0
    
    # DSO
    dso = calculate_dso(invoices, payments)
    
    # Collection rate
    paid_invoices = invoices[invoices["status"] == "paid"]
    collection_rate = (len(paid_invoices) / len(invoices) * 100) if len(invoices) > 0 else 0
    
    # Top metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total AR", format_currency(total_ar))
    
    with col2:
        st.metric(
            "Overdue AR", 
            format_currency(overdue_ar),
            delta=f"{overdue_pct:.1f}%",
            delta_color="inverse"
        )
    
    with col3:
        st.metric("DSO", f"{dso:.0f} days")
    
    with col4:
        st.metric("Collection Rate", f"{collection_rate:.1f}%")
    
    with col5:
        st.metric("Open Invoices", f"{len(open_invoices):,}")
    
    st.markdown("---")
    
    # Enhanced tabs with outreach
    if outreach_available:
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📈 Overview",
            "📋 Invoices", 
            "📊 Analytics",
            "💳 Customers",
            "📧 Outreach",
            "📅 Schedule"
        ])
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Overview",
            "📋 Invoices",
            "📊 Analytics",
            "💳 Customers"
        ])
    
    with tab1:
        # Overview Tab (existing code)
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("AR Aging Distribution")
            
            open_invoices["days_overdue"] = (now - open_invoices["due_date"]).dt.days.clip(lower=0)
            open_invoices["aging_bucket"] = open_invoices["days_overdue"].apply(get_aging_bucket)
            
            aging_summary = open_invoices.groupby("aging_bucket").agg({
                "invoice_amount": "sum",
                "invoice_id": "count"
            }).reset_index()
            aging_summary.columns = ["Aging Bucket", "Amount", "Count"]
            
            bucket_order = ["Current", "1-30 days", "31-60 days", "61-90 days", "90+ days"]
            aging_summary["Aging Bucket"] = pd.Categorical(
                aging_summary["Aging Bucket"], 
                categories=bucket_order, 
                ordered=True
            )
            aging_summary = aging_summary.sort_values("Aging Bucket")
            
            fig_aging = px.bar(
                aging_summary,
                x="Aging Bucket",
                y="Amount",
                title="Accounts Receivable by Age",
                color="Amount",
                color_continuous_scale="RdYlGn_r",
                text="Count"
            )
            fig_aging.update_traces(texttemplate='%{text} invoices', textposition='outside')
            fig_aging.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_aging, use_container_width=True)
            
            aging_summary["Percentage"] = (aging_summary["Amount"] / aging_summary["Amount"].sum() * 100)
            st.dataframe(
                aging_summary.style.format({
                    "Amount": "${:,.0f}",
                    "Percentage": "{:.1f}%"
                }),
                hide_index=True,
                use_container_width=True
            )
        
        with col2:
            st.subheader("Monthly Payment Collections")
            
            if not payments.empty:
                payments_copy = payments.copy()
                payments_copy["month"] = payments_copy["payment_date"].dt.to_period("M").dt.to_timestamp()
                monthly_payments = payments_copy.groupby("month")["amount"].sum().reset_index()
                
                fig_payments = px.area(
                    monthly_payments,
                    x="month",
                    y="amount",
                    title="Payment Trends Over Time",
                    labels={"amount": "Amount Collected ($)", "month": "Month"}
                )
                fig_payments.update_layout(height=400)
                st.plotly_chart(fig_payments, use_container_width=True)
            else:
                st.info("No payment data available")
            
            st.subheader("Key Performance Indicators")
            
            kpi_data = {
                "Metric": [
                    "Average Invoice",
                    "Overdue Rate",
                    "Total Customers",
                    "Avg Days Overdue"
                ],
                "Value": [
                    format_currency(open_invoices["invoice_amount"].mean()),
                    f"{overdue_pct:.1f}%",
                    f"{len(customers):,}",
                    f"{open_invoices['days_overdue'].mean():.0f} days"
                ]
            }
            st.dataframe(pd.DataFrame(kpi_data), hide_index=True, use_container_width=True)
    
    with tab2:
        # Invoices Tab (existing code)
        st.subheader("🔍 Invoice Explorer")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.multiselect(
                "Status",
                options=invoices["status"].unique().tolist(),
                default=["open"]
            )
        
        with col2:
            customer_search = st.text_input("Search Customer ID", "")
        
        with col3:
            min_amount = st.number_input("Min Amount ($)", min_value=0, value=0, step=1000)
        
        filtered_invoices = invoices[invoices["status"].isin(status_filter)]
        
        if customer_search:
            filtered_invoices = filtered_invoices[
                filtered_invoices["customer_id"].str.contains(customer_search, case=False, na=False)
            ]
        
        filtered_invoices = filtered_invoices[filtered_invoices["invoice_amount"] >= min_amount]
        filtered_invoices = filtered_invoices.sort_values("due_date", ascending=False)
        
        st.info(f"📊 Showing {len(filtered_invoices):,} of {len(invoices):,} total invoices")
        
        display_cols = ["invoice_id", "customer_id", "invoice_amount", "issue_date", "due_date", "status"]
        st.dataframe(
            filtered_invoices[display_cols].style.format({
                "invoice_amount": "${:,.2f}",
                "issue_date": lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "",
                "due_date": lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else ""
            }),
            hide_index=True,
            use_container_width=True,
            height=500
        )
        
        csv = filtered_invoices.to_csv(index=False)
        st.download_button(
            "📥 Download Filtered Invoices (CSV)",
            csv,
            "filtered_invoices.csv",
            "text/csv"
        )
    
    with tab3:
        # Analytics Tab (existing code - keeping it brief)
        st.subheader("📊 Advanced Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Top 10 Customers by Outstanding AR")
            customer_ar = open_invoices.groupby("customer_id")["invoice_amount"].sum().nlargest(10).reset_index()
            customer_ar.columns = ["Customer ID", "Outstanding AR"]
            
            fig_customers = px.bar(
                customer_ar,
                x="Customer ID",
                y="Outstanding AR",
                title="Customer AR Concentration",
                color="Outstanding AR",
                color_continuous_scale="Blues"
            )
            fig_customers.update_layout(showlegend=False)
            st.plotly_chart(fig_customers, use_container_width=True)
        
        with col2:
            st.markdown("#### Invoice Status Distribution")
            status_dist = invoices["status"].value_counts().reset_index()
            status_dist.columns = ["Status", "Count"]
            
            fig_status = px.pie(
                status_dist,
                values="Count",
                names="Status",
                title="All Invoices by Status",
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            st.plotly_chart(fig_status, use_container_width=True)
    
    with tab4:
        # Customers Tab (simplified)
        st.subheader("💳 Customer Analysis")
        
        customer_invoice_summary = invoices.groupby("customer_id").agg({
            "invoice_id": "count",
            "invoice_amount": ["sum", "mean", "max"]
        }).reset_index()
        
        customer_invoice_summary.columns = [
            "Customer ID", 
            "Total Invoices", 
            "Total Amount", 
            "Avg Invoice", 
            "Max Invoice"
        ]
        
        open_ar_by_customer = open_invoices.groupby("customer_id")["invoice_amount"].sum().reset_index()
        open_ar_by_customer.columns = ["Customer ID", "Open AR"]
        
        customer_invoice_summary = customer_invoice_summary.merge(
            open_ar_by_customer,
            on="Customer ID",
            how="left"
        )
        customer_invoice_summary["Open AR"] = customer_invoice_summary["Open AR"].fillna(0)
        customer_invoice_summary = customer_invoice_summary.sort_values("Total Amount", ascending=False)
        
        st.markdown("#### Top 50 Customers by Total Invoice Value")
        
        st.dataframe(
            customer_invoice_summary.head(50).style.format({
                "Total Invoices": "{:,}",
                "Total Amount": "${:,.2f}",
                "Avg Invoice": "${:,.2f}",
                "Max Invoice": "${:,.2f}",
                "Open AR": "${:,.2f}"
            }).background_gradient(subset=["Open AR"], cmap="Reds"),
            hide_index=True,
            use_container_width=True,
            height=400
        )
    
    # NEW: Outreach Tab
    if outreach_available:
        with tab5:
            st.subheader("📧 Collections Outreach")
            
            st.markdown("#### Generate Personalized Messages")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                top_n = st.number_input("Top N Invoices", min_value=1, max_value=100, value=10)
            
            with col2:
                action_type = st.selectbox(
                    "Message Type",
                    ["friendly_reminder", "second_notice", "call_request", "payment_plan", "escalate"]
                )
            
            with col3:
                company_name = st.text_input("Company Name", "Your Company")
            
            if st.button("🎯 Generate Messages", type="primary"):
                try:
                    msg_gen = MessageGenerator(company_name=company_name)
                    
                    # Get top risky invoices
                    target_invoices = open_invoices.nlargest(top_n, "days_overdue")
                    
                    messages = []
                    for _, invoice in target_invoices.iterrows():
                        customer = customers[customers["customer_id"] == invoice["customer_id"]]
                        if len(customer) == 0:
                            continue
                        customer = customer.iloc[0]
                        
                        email = msg_gen.generate_email(
                            customer_name=customer.get("name", invoice["customer_id"]),
                            invoice_id=invoice["invoice_id"],
                            invoice_amount=invoice["invoice_amount"],
                            due_date=invoice["due_date"],
                            days_overdue=int(invoice["days_overdue"]),
                            action_type=action_type,
                            risk_level="medium"
                        )
                        
                        messages.append({
                            "Invoice ID": invoice["invoice_id"],
                            "Customer": customer.get("name", "")[:30],
                            "Amount": invoice["invoice_amount"],
                            "Days Overdue": int(invoice["days_overdue"]),
                            "Subject": email["subject"],
                            "Email Body": email["body"]
                        })
                    
                    if messages:
                        st.success(f"✅ Generated {len(messages)} messages!")
                        
                        # Show preview
                        st.markdown("#### Preview (First 3)")
                        for i, msg in enumerate(messages[:3]):
                            with st.expander(f"📧 {msg['Invoice ID']} - {msg['Customer']}"):
                                st.markdown(f"**Subject:** {msg['Subject']}")
                                st.text_area("Email Body", msg["Email Body"], height=200, key=f"email_{i}")
                        
                        # Download option
                        df = pd.DataFrame(messages)
                        csv = df.to_csv(index=False)
                        st.download_button(
                            "📥 Download All Messages (CSV)",
                            csv,
                            "outreach_messages.csv",
                            "text/csv"
                        )
                    else:
                        st.warning("No messages generated")
                        
                except Exception as e:
                    st.error(f"Error generating messages: {e}")
        
        # NEW: Schedule Tab
        with tab6:
            st.subheader("📅 Collections Schedule")
            
            try:
                scheduler = CollectionsScheduler()
                
                st.markdown("#### Follow-Up Cadences by Risk Level")
                cadences = scheduler.get_cadence_summary()
                st.dataframe(cadences, use_container_width=True, hide_index=True)
                
                st.markdown("#### Generate This Week's Plan")
                
                if st.button("🗓️ Create Weekly Schedule", type="primary"):
                    with st.spinner("Generating schedule..."):
                        # Generate schedules
                        all_schedules = []
                        for _, invoice in open_invoices.iterrows():
                            schedule = scheduler.generate_schedule(
                                invoice_id=invoice["invoice_id"],
                                customer_id=invoice["customer_id"],
                                risk_level="medium",
                                days_overdue=int(invoice["days_overdue"]),
                                max_attempts=5
                            )
                            all_schedules.extend(schedule)
                        
                        if all_schedules:
                            schedule_df = pd.DataFrame(all_schedules)
                            weekly = scheduler.get_this_weeks_actions(schedule_df)
                            
                            st.success(f"✅ Generated schedule for {len(open_invoices)} invoices")
                            st.info(f"📅 Actions this week: {len(weekly)}")
                            
                            if not weekly.empty:
                                st.markdown("#### This Week's Actions")
                                st.dataframe(
                                    weekly[[
                                        "invoice_id", "customer_id", "scheduled_date", 
                                        "action_type", "attempt_number"
                                    ]].head(20),
                                    use_container_width=True,
                                    hide_index=True
                                )
                                
                                # Download
                                csv = schedule_df.to_csv(index=False)
                                st.download_button(
                                    "📥 Download Full Schedule (CSV)",
                                    csv,
                                    "collections_schedule.csv",
                                    "text/csv"
                                )
                        
            except Exception as e:
                st.error(f"Error with scheduler: {e}")
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style='text-align: center; color: gray; padding: 1rem;'>
        <p><strong>CashFlowGuard</strong> - Invoice Collections & Cash Flow Management</p>
        <p>📊 {len(invoices):,} invoices | 👥 {len(customers):,} customers | 💰 {format_currency(total_ar)} AR</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()