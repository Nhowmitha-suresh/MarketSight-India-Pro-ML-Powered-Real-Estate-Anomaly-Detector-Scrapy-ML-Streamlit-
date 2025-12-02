"""
MarketSight Pro v2.0 Dashboard - ML-Enhanced Real Estate Anomaly Finder
Features: ML Predictions, Opportunities View, Market Risk View, Interactive Charts
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import importlib.util
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
import streamlit as st

# Import shared ENGINE from config
# Ensure project root is on sys.path so `from config import ENGINE` works when Streamlit
# runs with a different working directory. This mirrors running the app from the repo root.
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
try:
    from config import ENGINE
except ModuleNotFoundError:
    # Fallback: load config.py directly from project root
    cfg_path = project_root / 'config.py'
    if cfg_path.exists():
        spec = importlib.util.spec_from_file_location('config', str(cfg_path))
        cfg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cfg)
        ENGINE = getattr(cfg, 'ENGINE', None)
    else:
        raise

TARGET_ZIP = os.getenv('TARGET_ZIP', '12345')

# Page config
st.set_page_config(
    layout='wide',
    page_title='MarketSight Pro v2.0 - ML Analysis',
    page_icon='🏠',
    initial_sidebar_state='expanded'
)

# Custom CSS with enhanced styling
st.markdown('''
    <style>
        .header-title { color: #1a3a52; font-size: 2.8em; font-weight: 700; margin-bottom: 0.3em; }
        .header-subtitle { color: #666; font-size: 1.15em; margin-bottom: 1.5em; }
        .version-badge { color: #17a2b8; font-size: 0.85em; font-weight: 600; }
        
        .property-card {
            background: white; border-radius: 10px; padding: 1.5em;
            margin-bottom: 1em; box-shadow: 0 2px 10px rgba(0,0,0,0.12);
            border-left: 5px solid #17a2b8; transition: all 0.3s ease;
        }
        .property-card:hover { box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
        .property-card.opportunity { border-left-color: #28a745; }
        .property-card.risk { border-left-color: #dc3545; }
        
        .property-price { font-size: 1.9em; font-weight: 700; color: #1a3a52; }
        .property-address { font-size: 1.1em; color: #2c3e50; margin-top: 0.5em; }
        .property-agent { font-size: 0.9em; color: #999; margin-top: 0.3em; }
        
        .anomaly-badge {
            display: inline-block; padding: 0.6em 1.2em;
            border-radius: 25px; font-weight: 600; font-size: 0.9em; margin-top: 0.7em;
            margin-right: 0.5em;
        }
        .badge-opportunity { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .badge-risk { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .badge-ml { background-color: #e7f3ff; color: #004085; border: 1px solid #b8daff; }
        
        .metric-box {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 1.5em; border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;
            border-top: 3px solid #17a2b8;
        }
        .metric-value { font-size: 2.2em; font-weight: 700; color: #1a3a52; }
        .metric-label { color: #666; font-size: 0.95em; margin-top: 0.5em; font-weight: 500; }
        
        .ml-info-box {
            background: #e7f3ff; padding: 1em; border-radius: 8px;
            border-left: 4px solid #004085; margin: 1em 0;
        }
        .ml-info-box p { margin: 0; color: #004085; font-size: 0.9em; }
        
        .deviation-bar {
            width: 100%; height: 8px; background: #e0e0e0;
            border-radius: 4px; margin: 0.5em 0; overflow: hidden;
        }
        .deviation-fill { height: 100%; background: linear-gradient(90deg, #28a745, #ffc107, #dc3545); }
    </style>
''', unsafe_allow_html=True)

engine = ENGINE

# Data loading functions
@st.cache_data(ttl=300)
def load_listings_with_ml(zip_code):
    """Load listings with ML predictions and ML-based anomaly flags"""
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
                   a.predicted_price,
                   a.deviation_percentage,
                   a.dq_status,
                   a.analyzed_at
            FROM listings l 
            LEFT JOIN listing_analysis a ON l.listing_id = a.listing_id 
            WHERE l.zip_code = :zip AND l.dq_status = 'PASS'
            ORDER BY COALESCE(a.deviation_percentage, 0) DESC
        """)
        df = pd.read_sql(query, engine, params={'zip': zip_code})
        return df
    except Exception as e:
        st.error(f'❌ Error loading listings: {e}')
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_group_stats(zip_code, days=7):
    """Load historical group stats"""
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
        return df.sort_values('stat_date') if not df.empty else df
    except Exception as e:
        st.error(f'❌ Error loading stats: {e}')
        return pd.DataFrame()

# Helper functions
def format_price(price, format_type='absolute'):
    """Format price based on user preference"""
    if pd.isna(price) or price <= 0:
        return "N/A"
    if format_type == 'scaled':
        if price >= 10000000:
            return f"₹{price/10000000:.2f} Cr"
        elif price >= 100000:
            return f"₹{price/100000:.2f} L"
    return f"₹{price:,.0f}"

def format_ppsq(value, format_type='absolute'):
    """Format price per sqft"""
    if pd.isna(value) or value <= 0:
        return "N/A"
    if format_type == 'scaled':
        return f"₹{value/1000:.2f}K" if value >= 1000 else f"₹{value:,.0f}"
    return f"₹{value:,.2f}"

def calculate_sigma_deviation(price_per_sqft, mean, std):
    """Calculate statistical sigma deviation"""
    if pd.isna(mean) or pd.isna(std) or std == 0:
        return 0
    return abs((price_per_sqft - mean) / std)

# Main layout
col1, col2 = st.columns([0.7, 0.3])
with col1:
    st.markdown('<div class="header-title">🏠 MarketSight Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-subtitle">ML-Powered Real Estate Anomaly Finder</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="version-badge">v2.0 with Random Forest Analysis</div>', unsafe_allow_html=True)

# Sidebar controls
with st.sidebar:
    st.markdown('---')
    
    # View selector
    view_type = st.radio(
        'Select View:',
        options=['📊 Dashboard', '🚀 Opportunities', '⚠️ Market Risks', '📈 Market Trends', '💡 ML Analysis'],
        label_visibility='collapsed'
    )
    
    st.markdown('---')
    st.subheader('🔧 Controls')
    
    # ZIP code
    zip_code = st.text_input('ZIP Code', value=TARGET_ZIP, key='zip_input')
    
    # Currency format
    currency_format = st.radio(
        'Currency Format:',
        options=['₹ Absolute', '₹ Scaled (Cr/Lakhs)'],
        horizontal=True
    )
    format_type = 'scaled' if 'Scaled' in currency_format else 'absolute'
    
    st.markdown('---')
    
    # Filters
    st.subheader('🔍 Filters')

    # Load listings snapshot for filter values (cached)
    listings_snapshot = load_listings_with_ml(zip_code)

    property_types = st.multiselect(
        'Property Type',
        options=['All'] + list(listings_snapshot.get('property_type', pd.Series()).dropna().unique()),
        default=['All']
    )

    # Hierarchical City -> Locality selectors
    cities = ['All'] + sorted(list(listings_snapshot.get('city', pd.Series()).dropna().unique()))
    selected_city = st.selectbox('City', options=cities, index=0)

    if selected_city and selected_city != 'All':
        localities = ['All'] + sorted(list(listings_snapshot.loc[listings_snapshot.get('city') == selected_city].get('locality', pd.Series()).dropna().unique()))
    else:
        localities = ['All'] + sorted(list(listings_snapshot.get('locality', pd.Series()).dropna().unique()))

    selected_locality = st.selectbox('Locality', options=localities, index=0)
    
    if view_type == '🚀 Opportunities':
        deviation_range = st.slider('Max Underpricing (%)', -50, -5, -15)
    elif view_type == '⚠️ Market Risks':
        deviation_range = st.slider('Min Overpricing (%)', 5, 50, 15)
    else:
        deviation_range = None
    
    st.markdown('---')
    if st.button('🔄 Refresh Data', use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Main content
if not zip_code:
    st.warning('👈 Enter a ZIP code in the sidebar to get started.')
else:
    df = load_listings_with_ml(zip_code)
    
    if df.empty:
        st.info(f'📭 No listings found for ZIP {zip_code}. Run the scraper or seed demo to populate data.')
        st.code('python seed_demo.py 12345 ; python -m analysis.analyze_ml')
    else:
        # Filter by property type
        if 'All' not in property_types and property_types:
            df = df[df['property_type'].isin(property_types)]

        # Filter by selected city/locality from sidebar
        try:
            if 'selected_city' in locals() and selected_city and selected_city != 'All':
                df = df[df.get('city') == selected_city]
            if 'selected_locality' in locals() and selected_locality and selected_locality != 'All':
                df = df[df.get('locality') == selected_locality]
        except Exception:
            # Defensive: if city/locality columns missing, ignore
            pass
        
        if view_type == '📊 Dashboard':
            st.subheader('📊 Executive Overview')
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f'''<div class="metric-box">
                    <div class="metric-value">{len(df)}</div>
                    <div class="metric-label">Total Listings</div>
                </div>''', unsafe_allow_html=True)
            
            with col2:
                anom_count = df[df['is_anomaly'] == True].shape[0]
                st.markdown(f'''<div class="metric-box">
                    <div class="metric-value">{anom_count}</div>
                    <div class="metric-label">ML Anomalies</div>
                </div>''', unsafe_allow_html=True)
            
            with col3:
                opp_count = df[(df['anomaly_type'] == 'under-priced') & (df['is_anomaly'] == True)].shape[0]
                st.markdown(f'''<div class="metric-box">
                    <div class="metric-value" style="color: #28a745;">{opp_count}</div>
                    <div class="metric-label">Opportunities</div>
                </div>''', unsafe_allow_html=True)
            
            with col4:
                risk_count = df[(df['anomaly_type'] == 'over-priced') & (df['is_anomaly'] == True)].shape[0]
                st.markdown(f'''<div class="metric-box">
                    <div class="metric-value" style="color: #dc3545;">{risk_count}</div>
                    <div class="metric-label">Risks</div>
                </div>''', unsafe_allow_html=True)
            
            st.markdown('---')
            st.subheader('📊 Price vs Sqft Analysis (ML Predictions)')
            
            # Create scatter plot with ML anomalies highlighted
            plot_df = df[df['predicted_price'].notna()].copy()
            if not plot_df.empty:
                plot_df['Color'] = plot_df.apply(
                    lambda r: 'Opportunity (Under)' if r['anomaly_type'] == 'under-priced'
                    else 'Risk (Over)' if r['anomaly_type'] == 'over-priced'
                    else 'Normal',
                    axis=1
                )
                
                fig = px.scatter(
                    plot_df,
                    x='sq_ft', y='price',
                    color='Color',
                    hover_data=['address', 'beds', 'baths', 'predicted_price', 'deviation_percentage'],
                    title='ML-Based Price Anomalies',
                    labels={'sq_ft': 'Square Feet', 'price': 'Price'},
                    color_discrete_map={
                        'Opportunity (Under)': '#28a745',
                        'Risk (Over)': '#dc3545',
                        'Normal': '#17a2b8'
                    }
                )
                fig.update_layout(height=500, hovermode='closest')
                st.plotly_chart(fig, use_container_width=True)
            
            # Market behavior metrics
            st.markdown('---')
            st.subheader('📊 Market Behavior')
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Days on market by anomaly status
                dom_data = df.copy()
                dom_data['Listing Type'] = dom_data['is_anomaly'].map({True: 'Anomalies', False: 'Normal'})
                dom_stats = dom_data.groupby('Listing Type')['days_on_market'].agg(['mean', 'count']).reset_index()
                
                if not dom_stats.empty:
                    fig_dom = px.bar(
                        dom_stats,
                        x='Listing Type',
                        y='mean',
                        title='Average Days on Market by Status',
                        labels={'mean': 'Days'},
                        color_discrete_map={'Anomalies': '#ff7f50', 'Normal': '#17a2b8'}
                    )
                    fig_dom.update_layout(height=400)
                    st.plotly_chart(fig_dom, use_container_width=True)
            
            with col2:
                # Deviation distribution
                dev_data = df[df['deviation_percentage'].notna()].copy()
                if not dev_data.empty:
                    fig_dev = px.histogram(
                        dev_data,
                        x='deviation_percentage',
                        nbins=20,
                        title='Distribution of ML Deviations (%)',
                        labels={'deviation_percentage': 'Deviation %'}
                    )
                    fig_dev.update_layout(height=400)
                    st.plotly_chart(fig_dev, use_container_width=True)

            # Actionable anomalies table (clickable View Source)
            st.markdown('---')
            st.subheader('🔎 Actionable Anomalies')
            anomalies_df = df[df.get('is_anomaly') == True].copy()
            if anomalies_df.empty:
                st.info('No anomalies detected in the current filter set.')
            else:
                # Prepare display table
                table = pd.DataFrame()
                table['Address'] = anomalies_df.get('address')
                table['BHK'] = anomalies_df.get('beds')
                table['Actual Price'] = anomalies_df.get('price').apply(lambda p: format_price(p, format_type))
                table['Predicted Price'] = anomalies_df.get('predicted_price').apply(lambda p: format_price(p, format_type) if pd.notna(p) else 'N/A')
                table['Deviation %'] = anomalies_df.get('deviation_percentage').apply(lambda d: f"{d:.1f}%" if pd.notna(d) else 'N/A')
                # Create clickable link for source
                def make_link(url):
                    if not url or pd.isna(url):
                        return 'N/A'
                    return f"<a href=\"{url}\" target=\"_blank\">View Source</a>"
                table['View Source'] = anomalies_df.get('listing_url').apply(make_link)

                # Render as HTML table to allow links
                st.markdown(table.to_html(escape=False, index=False), unsafe_allow_html=True)
        
        elif view_type == '🚀 Opportunities':
            st.subheader('🚀 Investment Opportunities (Under-Priced by ML)')
            st.markdown('''<div class="ml-info-box"><p>
            🤖 ML Model identifies listings priced significantly BELOW the predicted fair value.
            These represent potential investment opportunities.
            </p></div>''', unsafe_allow_html=True)
            
            df_opp = df[(df['anomaly_type'] == 'under-priced') & (df['is_anomaly'] == True)].copy()
            df_opp = df_opp.sort_values('deviation_percentage')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                show_count = st.number_input('Show top', min_value=3, max_value=50, value=10)
            with col2:
                min_beds = st.number_input('Min Beds', min_value=0, max_value=10, value=0)
            with col3:
                max_price = st.number_input(f'Max Price ({currency_format})', min_value=0, value=1000000)
            
            df_opp = df_opp[(df_opp['beds'] >= min_beds) & (df_opp['price'] <= max_price)]
            df_opp = df_opp.head(show_count)
            
            if df_opp.empty:
                st.info('No opportunities match your filters.')
            else:
                st.markdown(f'**Found {len(df_opp)} opportunities:**')
                for _, row in df_opp.iterrows():
                    savings = row['predicted_price'] - row['price'] if (row['predicted_price'] and row['price']) else 0
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f'''
                            <div class="property-card opportunity">
                                <div class="property-price">{format_price(row['price'], format_type)}</div>
                                <div class="property-address">{row.get('address', 'N/A')}</div>
                                <div class="property-agent">🏢 {row.get('agent_name', 'N/A')}</div>
                                <div style="margin-top: 0.8em; font-size: 0.9em;">
                                    {int(row.get('sq_ft', 0)):,} sqft | {int(row.get('beds', 0))} bed / {int(row.get('baths', 0))} bath | {int(row.get('year_built', 0))}
                                </div>
                                <div class="anomaly-badge badge-opportunity">✓ Under-Priced</div>
                                <div class="anomaly-badge badge-ml">ML: {row.get('deviation_percentage', 0):.1f}% below fair value</div>
                                <div style="margin-top: 0.8em; padding-top: 0.8em; border-top: 1px solid #e0e0e0; font-size: 0.85em; color: #28a745; font-weight: 600;">
                                    💰 Estimated savings: {format_price(savings, format_type)}
                                </div>
                            </div>
                        ''', unsafe_allow_html=True)
        
        elif view_type == '⚠️ Market Risks':
            st.subheader('⚠️ Market Risks (Over-Priced by ML)')
            st.markdown('''<div class="ml-info-box"><p>
            🤖 ML Model flags listings priced significantly ABOVE the predicted fair value.
            These may represent market risks for buyers or indicate pricing errors.
            </p></div>''', unsafe_allow_html=True)
            
            df_risk = df[(df['anomaly_type'] == 'over-priced') & (df['is_anomaly'] == True)].copy()
            df_risk = df_risk.sort_values('deviation_percentage', ascending=False)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                show_count = st.number_input('Show top', min_value=3, max_value=50, value=10, key='risk_count')
            with col2:
                min_beds = st.number_input('Min Beds', min_value=0, max_value=10, value=0, key='risk_beds')
            with col3:
                min_price = st.number_input(f'Min Price ({currency_format})', min_value=0, value=0, key='risk_price')
            
            df_risk = df_risk[(df_risk['beds'] >= min_beds) & (df_risk['price'] >= min_price)]
            df_risk = df_risk.head(show_count)
            
            if df_risk.empty:
                st.info('No high-risk listings match your filters.')
            else:
                st.markdown(f'**Found {len(df_risk)} risk properties:**')
                for _, row in df_risk.iterrows():
                    overpriced = row['price'] - row['predicted_price'] if (row['predicted_price'] and row['price']) else 0
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f'''
                            <div class="property-card risk">
                                <div class="property-price">{format_price(row['price'], format_type)}</div>
                                <div class="property-address">{row.get('address', 'N/A')}</div>
                                <div class="property-agent">🏢 {row.get('agent_name', 'N/A')}</div>
                                <div style="margin-top: 0.8em; font-size: 0.9em;">
                                    {int(row.get('sq_ft', 0)):,} sqft | {int(row.get('beds', 0))} bed / {int(row.get('baths', 0))} bath | {int(row.get('year_built', 0))}
                                </div>
                                <div class="anomaly-badge badge-risk">⚠️ Over-Priced</div>
                                <div class="anomaly-badge badge-ml">ML: {row.get('deviation_percentage', 0):.1f}% above fair value</div>
                                <div style="margin-top: 0.8em; padding-top: 0.8em; border-top: 1px solid #e0e0e0; font-size: 0.85em; color: #dc3545; font-weight: 600;">
                                    ⛔ Overcharge risk: {format_price(overpriced, format_type)}
                                </div>
                            </div>
                        ''', unsafe_allow_html=True)
        
        elif view_type == '📈 Market Trends':
            st.subheader('📈 Market Trends Over Time')
            
            stats = load_group_stats(zip_code, 30)
            if not stats.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    metric = st.selectbox('Metric', ['Mean Price/SqFt', 'Std Dev', 'Count'], key='trend_metric')
                with col2:
                    days = st.selectbox('Time Period', [7, 14, 30, 90], index=2, key='trend_days')
                
                stats = load_group_stats(zip_code, days)
                
                if not stats.empty:
                    if metric == 'Mean Price/SqFt':
                        fig = px.line(stats, x='stat_date', y='mean_ppsq', color='property_type', markers=True,
                                      title='Mean Price/SqFt Trend')
                    elif metric == 'Std Dev':
                        fig = px.line(stats, x='stat_date', y='std_ppsq', color='property_type', markers=True,
                                      title='Price Variance Trend')
                    else:
                        fig = px.bar(stats, x='stat_date', y='count_listings', color='property_type',
                                     title='Listing Volume Trend')
                    
                    fig.update_layout(height=500, hovermode='x unified')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info('No historical trend data available. Run analysis to populate group_stats.')
        
        elif view_type == '💡 ML Analysis':
            st.subheader('💡 Machine Learning Model Details')
            
            st.markdown('''
            ### 🤖 Random Forest Pricing Model
            
            **Training Data:** Listings from past 90 days with DQ_PASS status
            
            **Features Used:**
            - Square Feet (sq_ft)
            - Number of Bedrooms (beds)
            - Number of Bathrooms (baths)
            - Year Built (year_built)
            
            **Prediction Output:**
            - Predicted Fair Market Price
            - Deviation % = (Actual - Predicted) / Predicted × 100%
            
            **Anomaly Classification:**
            - 🚀 **Opportunity** (Under-Priced): Deviation < -15%
            - ⚠️ **Risk** (Over-Priced): Deviation > +15%
            - ✓ **Normal**: -15% ≤ Deviation ≤ +15%
            
            ### 📊 Data Quality (DQ) Status
            Listings are marked DQ_PASS only if:
            - ✓ Square feet ≥ 500 sqft
            - ✓ Price > ₹0
            - ✓ Address is provided
            
            ### 📈 How to Use These Insights
            1. **Opportunities View**: Find under-priced properties for investment
            2. **Market Risks View**: Identify potentially overpriced listings
            3. **Scatter Plot**: Visualize price anomalies in the market
            4. **Market Trends**: Track price movements over time
            ''')
            
            # Show model statistics
            if not df.empty:
                st.subheader('Model Statistics')
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    ml_coverage = (df['predicted_price'].notna().sum() / len(df) * 100) if len(df) > 0 else 0
                    st.metric('ML Coverage', f'{ml_coverage:.1f}%')
                
                with col2:
                    if df['deviation_percentage'].notna().sum() > 0:
                        avg_dev = df['deviation_percentage'].mean()
                        st.metric('Avg Deviation', f'{avg_dev:+.2f}%')
                
                with col3:
                    if df['predicted_price'].notna().sum() > 0:
                        pred_range = (df['predicted_price'].max() - df['predicted_price'].min()) / df['predicted_price'].mean() * 100
                        st.metric('Prediction Range', f'{pred_range:.1f}%')
                
                with col4:
                    anom_pct = (df['is_anomaly'].sum() / len(df) * 100) if len(df) > 0 else 0
                    st.metric('Anomaly Rate', f'{anom_pct:.1f}%')

st.markdown('---')
st.markdown('''
<div style="text-align: center; color: #999; font-size: 0.85em; margin-top: 2em;">
    MarketSight Pro v2.0 | ML-Powered Real Estate Analysis | Data refreshes every 5 minutes
</div>
''', unsafe_allow_html=True)
