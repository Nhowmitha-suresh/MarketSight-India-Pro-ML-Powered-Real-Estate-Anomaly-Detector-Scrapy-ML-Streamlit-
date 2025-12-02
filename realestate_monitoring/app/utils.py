"""
Utility functions for the MarketSight Pro Streamlit app.
"""
import pandas as pd
import numpy as np

def calculate_sigma_deviation(price_per_sqft, mean, std):
    """Calculate how many standard deviations away from mean."""
    if pd.isna(mean) or pd.isna(std) or std == 0:
        return 0
    return abs((price_per_sqft - mean) / std)

def format_price(price):
    """Format price as currency."""
    return f"${price:,.0f}" if not pd.isna(price) else "N/A"

def format_ppsq(value):
    """Format price per square foot."""
    return f"${value:,.2f}" if not pd.isna(value) else "N/A"

def get_anomaly_emoji(anomaly_type):
    """Return emoji for anomaly type."""
    if anomaly_type == 'under-priced':
        return '🟢'
    elif anomaly_type == 'over-priced':
        return '🔴'
    else:
        return '⚪'

def get_property_icon(property_type):
    """Return emoji for property type."""
    icons = {
        'House': '🏠',
        'Condo': '🏢',
        'Townhouse': '🏘️',
        'Apartment': '🏗️',
        'Land': '🌳',
    }
    return icons.get(property_type, '🏠')

def classify_opportunity(sigma_dev):
    """Classify opportunity level based on sigma deviation."""
    if sigma_dev > 2.5:
        return '🔥 Exceptional'
    elif sigma_dev > 2.0:
        return '⚡ Excellent'
    elif sigma_dev > 1.5:
        return '✨ Good'
    else:
        return '✓ Fair'

def get_color_for_deviation(sigma_dev):
    """Return color code for sigma deviation visualization."""
    if sigma_dev > 2.5:
        return '#d32f2f'  # Dark red
    elif sigma_dev > 2.0:
        return '#f57c00'  # Dark orange
    elif sigma_dev > 1.5:
        return '#fbc02d'  # Amber
    else:
        return '#388e3c'  # Green
