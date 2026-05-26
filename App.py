import streamlit as st
import pandas as pd
import plotly.express as px
import random
import pdfplumber
import re

# App Configuration
st.set_page_config(page_title="Lottery Data Forensics", layout="wide")
st.title("📊 Statistical Lottery Analyzer (With PDF Support)")
st.markdown("---")

st.sidebar.header("📁 Data Ingestion")
uploaded_file = st.sidebar.file_uploader("Upload Past Results (CSV, Excel, or PDF)", type=["csv", "xlsx", "pdf"])

# --- PDF PARSING FUNCTION ---
def extract_numbers_from_pdf(file):
    """Extracts rows of numbers from a PDF file."""
    all_rows = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            # Split text by lines
            lines = text.split('\n')
            for line in lines:
                # Find all isolated blocks of digits (numbers between 1 and 99)
                numbers = re.findall(r'\b\d{1,2}\b', line)
                # Most lotteries have 5 to 7 numbers per draw. 
                # Adjust this range if your specific lottery draws more/fewer numbers.
                if 5 <= len(numbers) <= 7:
                    int_numbers = [int(n) for n in numbers]
                    all_rows.append(sorted(int_numbers))
                    
    if not all_rows:
        return None
        
    # Turn the extracted lists into a clean DataFrame
    cols = [f'Num_{i}' for i in range(1, len(all_rows) + 1)]
    df_pdf = pd.DataFrame(all_rows, columns=cols)
    # Insert a dummy date column for alignment with the dashboard layout
    df_pdf.insert(0, 'Draw_Index', range(1, len(df_pdf) + 1))
    return df_pdf

# --- MOCK DATA FALLBACK ---
@st.cache_data
def load_mock_data():
    data = []
    for i in range(1, 21):
        numbers = sorted(random.sample(range(1, 50), 6))
        data.append({"Draw_Date": f"2026-05-{i:02d}", "Numbers": numbers})
    df = pd.DataFrame(data)
    df_expanded = pd.DataFrame(df['Numbers'].to_list(), columns=[f'Num_{i}' for i in range(1, 7)])
    df_expanded.insert(0, 'Draw_Date', df['Draw_Date'])
    return df_expanded

# --- FILE HANDLING LOGIC ---
df = None

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.pdf'):
            df = extract_numbers_from_pdf(uploaded_file)
            if df is None:
                st.sidebar.error("Could not extract structured numbers from this PDF layout. Try a clean CSV/Excel.")
        elif uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        if df is not None:
            st.sidebar.success(f"Successfully processed {uploaded_file.name}!")
    except Exception as e:
        st.sidebar.error(f"Error parsing file: {e}")

# Fallback if no file uploaded or parsing failed
if df is None:
    st.sidebar.info("Showing demonstration mock data (6/49 format). Upload your own file to change.")
    df = load_mock_data()

# Show Raw Data Preview
with st.expander("👀 View Processed Data Matrix"):
    st.dataframe(df, use_container_width=True)

# --- DATA PROCESSING ---
num_cols = [col for col in df.columns if col.startswith('Num_') or 'number' in col.lower()]
if not num_cols:
    num_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()

all_drawn_numbers = df[num_cols].values.flatten()
frequency_series = pd.Series(all_drawn_numbers).value_counts().sort_index()
freq_df = pd.DataFrame({'Number': frequency_series.index, 'Occurrences': frequency_series.values})

# --- VISUALIZATION TABS ---
tab1, tab2, tab3 = st.tabs(["📈 Frequency Analysis", "❄️ Hot & Cold Metrics", "🎲 Smart Ticket Generator"])

with tab1:
    st.subheader("Distribution Map of Drawn Numbers")
    fig = px.bar(
        freq_df, 
        x='Number', 
        y='Occurrences', 
        labels={'Number': 'Lottery Ball ID', 'Occurrences': 'Total Times Drawn'},
        color='Occurrences',
        color_continuous_scale='Viridis'
    )
    fig.update_layout(xaxis=dict(tickmode='linear'))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🔥 Top 5 'Hot' Numbers")
        st.dataframe(freq_df.nlargest(5, 'Occurrences').reset_index(drop=True), use_container_width=True)
    with col2:
        st.markdown("### ❄️ Top 5 'Cold' Numbers")
        st.dataframe(freq_df.nsmallest(5, 'Occurrences').reset_index(drop=True), use_container_width=True)

with tab3:
    st.subheader("Custom Ticket Generation Mechanics")
    strategy = st.selectbox(
        "Choose Selection Strategy:",
        ["Pure Random (Standard)", "Hot Ball Bias (Most Frequent)", "Cold Ball Bias (Overdue Focus)"]
    )
    
    pool = list(freq_df['Number'].unique())
    
    if strategy == "Hot Ball Bias (Most Frequent)" and len(pool) >= 10:
        weights = freq_df['Occurrences'].tolist()
    elif strategy == "Cold Ball Bias (Overdue Focus)" and len(pool) >= 10:
        max_occ = freq_df['Occurrences'].max()
        weights = [max_occ - occ + 1 for occ in freq_df['Occurrences']]
    else:
        weights = None
        
    if st.button("Generate 3 Custom Tickets"):
        tickets = []
        for _ in range(3):
            if weights:
                sampled = freq_df.sample(n=len(num_cols), weights=weights, replace=False)['Number'].tolist()
            else:
                sampled = random.sample(pool, len(num_cols))
            tickets.append(sorted(sampled))
            
        for idx, ticket in enumerate(tickets, 1):
            st.success(f"Ticket Line {idx} :  ` {', '.join(map(str, ticket))} `")
            
st.markdown("---")
st.caption("⚠️ **Forensic Disclaimer:** This tool processes descriptive statistics for historical data tracking. It does not predict future independent events or modify underlying lottery house edge profiles.")
