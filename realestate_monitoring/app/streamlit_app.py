import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
import streamlit as st

load_dotenv()
DB_URL = os.getenv('DATABASE_URL')
TARGET_ZIP = os.getenv('TARGET_ZIP')

# Page config with custom theme
st.set_page_config(
    layout='wide',
    page_title='MarketSight Pro - Anomaly Finder',
    page_icon='🏠',
    initial_sidebar_state='expanded'
)

# Custom CSS for high-end styling
st.markdown('''
    <style>
        /* Color Palette */
        :root {
            --primary-dark: #1a3a52;
            --accent-teal: #17a2b8;
            --accent-orange: #ff7f50;
            --background-light: #f8f8f8;
            --text-dark: #2c3e50;
        }
        
        /* Main container */
        .main {
            background-color: #f8f8f8;
        }
        
        /* Header styling */
        .header-title {
            color: #1a3a52;
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 0.5em;
            text-align: left;
        }
        
        .header-subtitle {
            color: #666;
            font-size: 1.1em;
            margin-bottom: 1.5em;
        }
        
        /* Card styling */
        .property-card {
            background: white;
            border-radius: 8px;
            padding: 1.5em;
            margin-bottom: 1em;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #17a2b8;
        }
        
        .property-card.over-priced {
            border-left-color: #ff7f50;
        }
        
        .property-price {
            font-size: 1.8em;
            font-weight: 700;
            color: #1a3a52;
        }
        
        .property-address {
            font-size: 1.1em;
            color: #2c3e50;
            margin-top: 0.5em;
        }
        
        .anomaly-badge {
            display: inline-block;
            padding: 0.5em 1em;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9em;
            margin-top: 0.5em;
        }
        
        .badge-under {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .badge-over {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .metric-box {
            background: white;
            padding: 1.5em;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .metric-value {
            font-size: 2em;
            font-weight: 700;
            color: #17a2b8;
        }
        
        .metric-label {
            color: #666;
            font-size: 0.9em;
            margin-top: 0.5em;
        }
        
        /* Filter section */
        .filter-section {
            background: white;
            padding: 1.5em;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 2em;
        }
        
        /* Sidebar styling */
        .sidebar .sidebar-content {
            background-color: #1a3a52;
            color: white;
        }
        
        h1, h2, h3 {
            color: #1a3a52;
        }
        
        /* Button styling */
        .stButton > button {
            background-color: #17a2b8;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 0.6em 1.2em;
            font-weight: 600;
        }
        
        .stButton > button:hover {
            background-color: #138496;
        }
        
        /* Table styling */
        table {
            border-collapse: collapse;
            width: 100%;
        }
        
        th {
            background-color: #1a3a52;
            color: white;
            padding: 1em;
            text-align: left;
            font-weight: 600;
        }
        
        td {
            padding: 0.8em;
            border-bottom: 1px solid #e0e0e0;
        }
        
        tr:hover {
            background-color: #f0f0f0;
        }
    </style>
''', unsafe_allow_html=True)

# Initialize database connection
@st.cache_resource
def get_engine():
    if not DB_URL:
        st.error('DATABASE_URL not configured. Please set up your .env file.')
        return None
    try:
        return create_engine(DB_URL)
    except Exception as e:
        st.error(f'Database connection failed: {e}')
        return None

engine = get_engine()

# Data loading functions
@st.cache_data(ttl=300)
def load_listings_data(zip_code):
    """Load listings with analysis data."""
    try:
        query = text("""
            SELECT l.*, 
                   a.price_per_sqft, 
                   a.is_anomaly, 
                   a.anomaly_type, 
                   a.mean_ppsq,
                   a.std_ppsq,
                   a.analyzed_at 
            FROM listings l 
            LEFT JOIN listing_analysis a ON l.listing_id = a.listing_id 
            WHERE l.zip_code = :zip
            ORDER BY l.scrape_timestamp DESC
        """)
        df = pd.read_sql(query, engine, params={'zip': zip_code})
        return df
    except Exception as e:
        st.error(f'Error loading data: {e}')
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_group_stats(zip_code, days=7):
    """Load group statistics over time."""
    try:
        query = text("""
            SELECT stat_date, mean_ppsq, std_ppsq, count_listings, property_type
            FROM group_stats 
            WHERE zip_code = :zip 
            AND stat_date >= CURRENT_DATE - INTERVAL ':days days'
            ORDER BY stat_date ASC
        """)
        df = pd.read_sql(query, engine, params={'zip': zip_code, 'days': days})
        return df
    except Exception as e:
        st.error(f'Error loading group stats: {e}')
        return pd.DataFrame()

# Helper functions
def calculate_sigma_deviation(price_per_sqft, mean, std):
    """Calculate standard deviation deviation from mean."""
    if pd.isna(mean) or pd.isna(std) or std == 0:
        return 0
    return abs((price_per_sqft - mean) / std)

def format_price(price):
    """Format price as currency."""
    return f"${price:,.0f}" if not pd.isna(price) else "N/A"

def format_ppsq(value):
    """Format price per square foot."""
    return f"${value:,.2f}" if not pd.isna(value) else "N/A"

# Main app layout
col1, col2 = st.columns([0.8, 0.2])
with col1:
    st.markdown('<div class="header-title">🏠 MarketSight Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-subtitle">Real Estate Anomaly Finder - Discover Market Opportunities</div>', unsafe_allow_html=True)

# Sidebar navigation
with st.sidebar:
    st.image('https://via.placeholder.com/200x100/1a3a52/ffffff?text=MarketSight', use_column_width=True)
    st.markdown('---')
    
    page = st.radio(
        'Navigation',
        options=['📊 Dashboard', '🚨 Anomalies', '📈 Market Trends', '⏰ Alerts'],
        label_visibility='collapsed'
    )
    
    st.markdown('---')
    st.subheader('Filters')
    
    # ZIP code input
    default_zip = TARGET_ZIP or '12345'
    zip_code = st.text_input('ZIP Code', value=default_zip, key='zip_input')
    
    # Anomaly type filter
    anomaly_filter = st.multiselect(
        'Anomaly Type',
        options=['Under-Priced', 'Over-Priced', 'Normal'],
        default=['Under-Priced'],
        key='anomaly_filter'
    )
    
    st.markdown('---')
    st.subheader('Settings')
    refresh_rate = st.selectbox('Data Refresh Rate', options=['5 minutes', '15 minutes', '1 hour'], index=1)
    
    if st.button('🔄 Refresh Data Now'):
        st.cache_data.clear()
        st.rerun()

# Main content area
if not zip_code:
    st.warning('Please enter a ZIP code to get started.')
else:
    df = load_listings_data(zip_code)
    
    if df.empty:
        st.info(f'📭 No listings found for ZIP code {zip_code}. Run the scraper to populate data.')
    else:
        # Filter by anomaly type
        anomaly_map = {'Under-Priced': 'under-priced', 'Over-Priced': 'over-priced', 'Normal': None}
        filtered_types = [anomaly_map[a] for a in anomaly_filter]
        
        if 'Normal' in anomaly_filter:
            df_filtered = df[(df['anomaly_type'].isin(filtered_types)) | (df['is_anomaly'] == False)]
        else:
            df_filtered = df[df['anomaly_type'].isin(filtered_types)]
        
        # Get property types for filtering
        ptypes = sorted(df['property_type'].dropna().unique().tolist())
        
        if page == '📊 Dashboard':
            st.subheader('Executive Overview')
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f'''
                    <div class="metric-box">
                        <div class="metric-value">{len(df)}</div>
                        <div class="metric-label">Total Listings</div>
                    </div>
                ''', unsafe_allow_html=True)
            
            with col2:
                anomaly_count = df[df['is_anomaly'] == True].shape[0]
                st.markdown(f'''
                    <div class="metric-box">
                        <div class="metric-value">{anomaly_count}</div>
                        <div class="metric-label">Anomalies Found</div>
                    </div>
                ''', unsafe_allow_html=True)
            
            with col3:
                if not df['price_per_sqft'].isna().all():
                    avg_ppsq = df['price_per_sqft'].mean()
                    st.markdown(f'''
                        <div class="metric-box">
                            <div class="metric-value">{format_ppsq(avg_ppsq)}</div>
                            <div class="metric-label">Avg $/SqFt</div>
                        </div>
                    ''', unsafe_allow_html=True)
            
            with col4:
                if not df['days_on_market'].isna().all():
                    avg_dom = df['days_on_market'].mean()
                    st.markdown(f'''
                        <div class="metric-box">
                            <div class="metric-value">{avg_dom:.0f}</div>
                            <div class="metric-label">Avg Days on Market</div>
                        </div>
                    ''', unsafe_allow_html=True)
            
            st.markdown('---')
            
            # Days on market comparison chart
            st.subheader('📊 Market Behavior Analysis')
            dom_data = df.copy()
            dom_data['Listing Type'] = dom_data['is_anomaly'].map({True: 'Anomalies', False: 'Normal Listings'})
            dom_stats = dom_data.groupby('Listing Type')['days_on_market'].agg(['mean', 'median', 'count']).reset_index()
            
            fig_dom = px.bar(
                dom_stats,
                x='Listing Type',
                y='mean',
                title='Average Days on Market: Anomalies vs Normal Listings',
                labels={'mean': 'Average Days on Market'},
                color='Listing Type',
                color_discrete_map={'Anomalies': '#ff7f50', 'Normal Listings': '#17a2b8'}
            )
            fig_dom.update_layout(
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='white',
                font=dict(family='sans-serif', color='#1a3a52'),
                height=400
            )
            st.plotly_chart(fig_dom, use_container_width=True)
        
        elif page == '🚨 Anomalies':
            st.subheader('🔍 Anomaly Opportunities')
            
            # Filter section
            col1, col2, col3 = st.columns(3)
            
            with col1:
                selected_ptype = st.selectbox('Property Type', options=['All'] + ptypes, key='ptype_filter')
            
            with col2:
                sort_by = st.selectbox('Sort By', options=['Price/SqFt Deviation', 'Price (Low→High)', 'Days on Market'], key='sort_filter')
            
            with col3:
                show_count = st.number_input('Show', min_value=5, max_value=100, value=10, step=5)
            
            # Apply property type filter
            if selected_ptype != 'All':
                df_filtered = df_filtered[df_filtered['property_type'] == selected_ptype]
            
            # Apply sorting
            if sort_by == 'Price/SqFt Deviation':
                df_filtered = df_filtered.sort_values('price_per_sqft')
            elif sort_by == 'Price (Low→High)':
                df_filtered = df_filtered.sort_values('price')
            else:
                df_filtered = df_filtered.sort_values('days_on_market')
            
            df_filtered = df_filtered.head(show_count)
            
            st.markdown('---')
            
            if df_filtered.empty:
                st.info('No anomalies match your filters.')
            else:
                # Display as cards
                for idx, (_, row) in enumerate(df_filtered.iterrows()):
                    card_class = 'property-card over-priced' if row.get('anomaly_type') == 'over-priced' else 'property-card'
                    badge_class = 'badge-over' if row.get('anomaly_type') == 'over-priced' else 'badge-under'
                    
                    sigma_dev = calculate_sigma_deviation(row['price_per_sqft'], row['mean_ppsq'], row['std_ppsq'])
                    anomaly_label = f"🚨 {sigma_dev:.2f}σ {row.get('anomaly_type', 'NORMAL').upper()}"
                    
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.markdown(f'''
                            <div class="{card_class}">
                                <div class="property-price">{format_price(row['price'])}</div>
                                <div class="property-address">{row.get('address', 'N/A')}</div>
                                <div class="anomaly-badge {badge_class}">{anomaly_label}</div>
                                <div style="margin-top: 1em; font-size: 0.9em; color: #666;">
                                    <b>📐 {int(row.get('sq_ft', 0)):,}</b> sq ft &nbsp;|&nbsp;
                                    <b>🏠</b> {int(row.get('beds', 0))} bed / {int(row.get('baths', 0))} bath &nbsp;|&nbsp;
                                    <b>📅</b> {int(row.get('year_built', 0))} &nbsp;|&nbsp;
                                    <b>⏳</b> {int(row.get('days_on_market', 0))} days
                                </div>
                                <div style="margin-top: 0.8em; font-size: 0.85em; color: #999;">
                                    Market Avg: {format_ppsq(row['mean_ppsq'])} | This: {format_ppsq(row['price_per_sqft'])}
                                </div>
                            </div>
                        ''', unsafe_allow_html=True)
                    
                    with col2:
                        if row.get('listing_url'):
                            st.markdown(f'[📋 View]({row["listing_url"]})', unsafe_allow_html=True)
                    
                    with col3:
                        st.metric('Deviation', f"{sigma_dev:.2f}σ")
        
        elif page == '📈 Market Trends':
            st.subheader('📈 Market Trends & Analytics')
            
            col1, col2 = st.columns(2)
            
            with col1:
                metric_choice = st.selectbox(
                    'Select Metric',
                    options=['Mean Price/SqFt', 'Std Dev Price/SqFt', 'Listing Count', 'Anomaly Rate'],
                    key='metric_choice'
                )
            
            with col2:
                days_range = st.selectbox(
                    'Time Range',
                    options=['7 Days', '14 Days', '30 Days', '90 Days'],
                    key='days_range'
                )
            
            days_map = {'7 Days': 7, '14 Days': 14, '30 Days': 30, '90 Days': 90}
            days = days_map[days_range]
            
            stats = load_group_stats(zip_code, days)
            
            if not stats.empty:
                st.markdown('---')
                
                if metric_choice == 'Mean Price/SqFt':
                    fig = px.line(
                        stats,
                        x='stat_date',
                        y='mean_ppsq',
                        color='property_type',
                        title=f'Mean Price/SqFt Over Last {days} Days',
                        labels={'mean_ppsq': 'Mean $/SqFt', 'stat_date': 'Date'},
                        markers=True
                    )
                elif metric_choice == 'Std Dev Price/SqFt':
                    fig = px.line(
                        stats,
                        x='stat_date',
                        y='std_ppsq',
                        color='property_type',
                        title=f'Price/SqFt Std Dev Over Last {days} Days',
                        labels={'std_ppsq': 'Std Dev $/SqFt', 'stat_date': 'Date'},
                        markers=True
                    )
                else:  # Listing Count or Anomaly Rate
                    fig = px.bar(
                        stats,
                        x='stat_date',
                        y='count_listings',
                        color='property_type',
                        title=f'Listings per Day Over Last {days} Days',
                        labels={'count_listings': 'Count', 'stat_date': 'Date'}
                    )
                
                fig.update_layout(
                    hovermode='x unified',
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='white',
                    font=dict(family='sans-serif', color='#1a3a52'),
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info('No group statistics available yet. Run the analysis to populate data.')
        
        elif page == '⏰ Alerts':
            st.subheader('⏰ Scheduled Alerts')
            
            st.info('📋 Alert Settings Coming Soon')
            st.write('''
                Configure automated alerts for:
                - New anomalies in your target ZIP codes
                - Price/SqFt threshold breaches
                - Market trend changes
                - Property type specific alerts
            ''')
