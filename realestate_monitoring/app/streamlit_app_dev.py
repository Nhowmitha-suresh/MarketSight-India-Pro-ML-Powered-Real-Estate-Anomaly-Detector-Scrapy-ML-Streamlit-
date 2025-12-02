"""
MarketSight Pro Development Dashboard - Works with both PostgreSQL and SQLite
Great for local testing and demos!
"""
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
import streamlit as st

# Import shared ENGINE from config (has fallback logic built-in)
from config import ENGINE

TARGET_ZIP = os.getenv('TARGET_ZIP', '12345')

# Page config
st.set_page_config(
    layout='wide',
    page_title='MarketSight Pro - Anomaly Finder',
    page_icon='🏠',
    initial_sidebar_state='expanded'
)

# Custom CSS
st.markdown('''
    <style>
        .header-title { color: #1a3a52; font-size: 2.5em; font-weight: 700; margin-bottom: 0.5em; }
        .header-subtitle { color: #666; font-size: 1.1em; margin-bottom: 1.5em; }
        .property-card {
            background: white; border-radius: 8px; padding: 1.5em;
            margin-bottom: 1em; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #17a2b8;
        }
        .property-card.over { border-left-color: #ff7f50; }
        .property-price { font-size: 1.8em; font-weight: 700; color: #1a3a52; }
        .property-address { font-size: 1.1em; color: #2c3e50; margin-top: 0.5em; }
        .anomaly-badge {
            display: inline-block; padding: 0.5em 1em;
            border-radius: 20px; font-weight: 600; font-size: 0.9em; margin-top: 0.5em;
        }
        .badge-under { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .badge-over { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .metric-box {
            background: white; padding: 1.5em; border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center;
        }
        .metric-value { font-size: 2em; font-weight: 700; color: #17a2b8; }
        .metric-label { color: #666; font-size: 0.9em; margin-top: 0.5em; }
    </style>
''', unsafe_allow_html=True)

# Database engine - use the shared ENGINE from config
engine = ENGINE

# Data loading
@st.cache_data(ttl=300)
def load_listings_data(zip_code):
    if not engine:
        return pd.DataFrame()
    try:
        query = text("""
            SELECT l.*, 
                   COALESCE(a.price_per_sqft, 0) as price_per_sqft,
                   COALESCE(a.is_anomaly, 0) as is_anomaly,
                   a.anomaly_type,
                   COALESCE(a.mean_ppsq, 0) as mean_ppsq,
                   COALESCE(a.std_ppsq, 0) as std_ppsq,
                   a.analyzed_at
            FROM listings l 
            LEFT JOIN listing_analysis a ON l.listing_id = a.listing_id 
            WHERE l.zip_code = :zip
            ORDER BY l.scrape_timestamp DESC
        """)
        df = pd.read_sql(query, engine, params={'zip': zip_code})
        return df
    except Exception as e:
        st.error(f'❌ Error loading listings: {e}')
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_group_stats(zip_code, days=7):
    if not engine:
        return pd.DataFrame()
    try:
        query = text("""
            SELECT stat_date, mean_ppsq, std_ppsq, count_listings, property_type
            FROM group_stats 
            WHERE zip_code = :zip 
            ORDER BY stat_date DESC
            LIMIT :limit
        """)
        df = pd.read_sql(query, engine, params={'zip': zip_code, 'limit': days})
        return df.sort_values('stat_date')
    except Exception as e:
        st.error(f'❌ Error loading stats: {e}')
        return pd.DataFrame()

# Helper functions
def calculate_sigma_deviation(price_per_sqft, mean, std):
    if pd.isna(mean) or pd.isna(std) or std == 0:
        return 0
    return abs((price_per_sqft - mean) / std)

def format_price(price):
    return f"${price:,.0f}" if not pd.isna(price) and price > 0 else "N/A"

def format_ppsq(value):
    return f"${value:,.2f}" if not pd.isna(value) and value > 0 else "N/A"

# Main layout
col1, col2 = st.columns([0.8, 0.2])
with col1:
    st.markdown('<div class="header-title">🏠 MarketSight Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-subtitle">Real Estate Anomaly Finder</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown('---')
    page = st.radio(
        'Navigation',
        options=['📊 Dashboard', '🚨 Anomalies', '📈 Market Trends', '⏰ Alerts'],
        label_visibility='collapsed'
    )
    
    st.markdown('---')
    st.subheader('Filters')
    zip_code = st.text_input('ZIP Code', value=TARGET_ZIP, key='zip_input')
    
    anomaly_filter = st.multiselect(
        'Anomaly Type',
        options=['Under-Priced', 'Over-Priced', 'Normal'],
        default=['Under-Priced'],
    )
    
    st.markdown('---')
    if st.button('🔄 Refresh Data'):
        st.cache_data.clear()
        st.rerun()

# Main content
if not zip_code:
    st.warning('👈 Enter a ZIP code in the sidebar to get started.')
else:
    df = load_listings_data(zip_code)
    
    if df.empty:
        st.info(f'📭 No listings found for ZIP code {zip_code}. Run the scraper to populate data.')
        st.code('scrapy crawl listings -a zip=' + zip_code)
    else:
        # Filter by anomaly type
        anomaly_map = {'Under-Priced': 'under-priced', 'Over-Priced': 'over-priced', 'Normal': None}
        filtered_types = [anomaly_map[a] for a in anomaly_filter]
        
        if 'Normal' in anomaly_filter:
            df_filtered = df[(df['anomaly_type'].isin(filtered_types)) | (df['is_anomaly'] == 0)]
        else:
            df_filtered = df[df['anomaly_type'].isin(filtered_types)]
        
        ptypes = sorted(df['property_type'].dropna().unique().tolist())
        
        if page == '📊 Dashboard':
            st.subheader('Executive Overview')
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f'''<div class="metric-box">
                    <div class="metric-value">{len(df)}</div>
                    <div class="metric-label">Total Listings</div>
                </div>''', unsafe_allow_html=True)
            
            with col2:
                anomaly_count = df[df['is_anomaly'] == True].shape[0]
                st.markdown(f'''<div class="metric-box">
                    <div class="metric-value">{anomaly_count}</div>
                    <div class="metric-label">Anomalies</div>
                </div>''', unsafe_allow_html=True)
            
            with col3:
                if not df['price_per_sqft'].isna().all():
                    avg_ppsq = df['price_per_sqft'].mean()
                    st.markdown(f'''<div class="metric-box">
                        <div class="metric-value">{format_ppsq(avg_ppsq)}</div>
                        <div class="metric-label">Avg $/SqFt</div>
                    </div>''', unsafe_allow_html=True)
            
            with col4:
                if not df['days_on_market'].isna().all():
                    avg_dom = df['days_on_market'].mean()
                    st.markdown(f'''<div class="metric-box">
                        <div class="metric-value">{avg_dom:.0f}</div>
                        <div class="metric-label">Avg DOM</div>
                    </div>''', unsafe_allow_html=True)
            
            st.markdown('---')
            st.subheader('📊 Market Behavior')
            
            dom_data = df.copy()
            dom_data['Listing Type'] = dom_data['is_anomaly'].map({True: 'Anomalies', False: 'Normal'})
            dom_stats = dom_data.groupby('Listing Type')['days_on_market'].agg(['mean', 'count']).reset_index()
            
            fig_dom = px.bar(
                dom_stats,
                x='Listing Type',
                y='mean',
                title='Average Days on Market',
                labels={'mean': 'Days'},
                color_discrete_map={'Anomalies': '#ff7f50', 'Normal': '#17a2b8'}
            )
            fig_dom.update_layout(hovermode='x', plot_bgcolor='rgba(0,0,0,0)', height=400)
            st.plotly_chart(fig_dom, width='stretch')
        
        elif page == '🚨 Anomalies':
            st.subheader('🔍 Anomaly Opportunities')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                selected_ptype = st.selectbox('Property Type', options=['All'] + ptypes)
            with col2:
                sort_by = st.selectbox('Sort By', options=['Price/SqFt', 'Price (Low)', 'Days on Market'])
            with col3:
                show_count = st.number_input('Show', min_value=5, max_value=50, value=10)
            
            if selected_ptype != 'All':
                df_filtered = df_filtered[df_filtered['property_type'] == selected_ptype]
            
            if sort_by == 'Price/SqFt':
                df_filtered = df_filtered.sort_values('price_per_sqft')
            elif sort_by == 'Price (Low)':
                df_filtered = df_filtered.sort_values('price')
            else:
                df_filtered = df_filtered.sort_values('days_on_market')
            
            df_filtered = df_filtered.head(show_count)
            
            st.markdown('---')
            
            if df_filtered.empty:
                st.info('No anomalies match your filters.')
            else:
                for _, row in df_filtered.iterrows():
                    card_class = 'property-card over' if row.get('anomaly_type') == 'over-priced' else 'property-card'
                    badge_class = 'badge-over' if row.get('anomaly_type') == 'over-priced' else 'badge-under'
                    
                    sigma_dev = calculate_sigma_deviation(row['price_per_sqft'], row['mean_ppsq'], row['std_ppsq'])
                    anomaly_label = f"🚨 {sigma_dev:.2f}σ {row.get('anomaly_type', 'NORMAL').upper()}"
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f'''
                            <div class="{card_class}">
                                <div class="property-price">{format_price(row['price'])}</div>
                                <div class="property-address">{row.get('address', 'N/A')}</div>
                                <div class="anomaly-badge {badge_class}">{anomaly_label}</div>
                                <div style="margin-top: 1em; font-size: 0.9em; color: #666;">
                                    {int(row.get('sq_ft', 0)):,} sqft | {int(row.get('beds', 0))} bed / {int(row.get('baths', 0))} bath | {int(row.get('year_built', 0))}
                                </div>
                                <div style="margin-top: 0.5em; font-size: 0.85em; color: #999;">
                                    Market: {format_ppsq(row['mean_ppsq'])} | This: {format_ppsq(row['price_per_sqft'])}
                                </div>
                            </div>
                        ''', unsafe_allow_html=True)
        
        elif page == '📈 Market Trends':
            st.subheader('📈 Market Trends')
            
            col1, col2 = st.columns(2)
            with col1:
                metric = st.selectbox('Metric', ['Mean $/SqFt', 'Std Dev', 'Count'])
            with col2:
                days = st.selectbox('Days', [7, 14, 30, 90], index=2)
            
            stats = load_group_stats(zip_code, days)
            
            if not stats.empty:
                if metric == 'Mean $/SqFt':
                    fig = px.line(stats, x='stat_date', y='mean_ppsq', color='property_type', markers=True,
                                  title='Mean Price/SqFt Over Time')
                elif metric == 'Std Dev':
                    fig = px.line(stats, x='stat_date', y='std_ppsq', color='property_type', markers=True,
                                  title='Price/SqFt Std Dev Over Time')
                else:
                    fig = px.bar(stats, x='stat_date', y='count_listings', color='property_type',
                                 title='Listings Per Day')
                
                fig.update_layout(hovermode='x unified', height=500)
                st.plotly_chart(fig, width='stretch')
            else:
                st.info('No trend data. Run analysis to populate group_stats.')
        
        elif page == '⏰ Alerts':
            st.subheader('⏰ Alert Settings (Coming Soon)')
            st.info('Configure custom alerts for price anomalies, market trends, and opportunities.')
