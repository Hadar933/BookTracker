import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import os
import calendar

DAILY_LOG_FILE = 'daily_reading_log.csv'
YEAR = datetime.now().year


def log_daily_reading(daily_log, log_date, pages):
    updated_log = pd.concat([daily_log, pd.DataFrame(
        {'date': [log_date], 'pages': [pages]})], ignore_index=True)
    updated_log.to_csv(DAILY_LOG_FILE, index=False)
    return updated_log


def calculate_streak(df, daily_goal):
    df = df.sort_values('date').reset_index(drop=True)
    df['date'] = pd.to_datetime(df['date']).dt.date
    df['streak'] = ((df['pages'] >= daily_goal) & (
        df['date'].diff().dt.days == 1)).cumsum()
    current_streak = df['streak'].iloc[-1] if df['pages'].iloc[-1] >= daily_goal else 0
    return current_streak, df['streak'].max()


def get_daily_stats(daily_log):
    if daily_log.empty:
        return None
    daily_log['date'] = pd.to_datetime(daily_log['date']).dt.date
    grouped_log = daily_log.groupby('date', as_index=False).sum()
    return {
        'total_pages': grouped_log['pages'].sum(),
        'avg_pages_per_day': grouped_log['pages'].mean(),
        'avg_pages_last_week': grouped_log['pages'].tail(7).mean(),
        'grouped_log': grouped_log
    }


def create_heatmap_view(df):
    # Ensure df is the grouped_log (already aggregated)
    df['date'] = pd.to_datetime(df['date'])
    df['day_of_year'] = df['date'].dt.dayofyear
    df['week'] = df['date'].dt.isocalendar().week
    df['day_of_week'] = df['date'].dt.weekday

    # Create a full-year date range
    start_date = pd.to_datetime(f"{YEAR}-01-01")
    end_date = pd.to_datetime(f"{YEAR}-12-31")
    all_days = pd.DataFrame(pd.date_range(
        start=start_date, end=end_date, freq='D'), columns=['date'])
    all_days['day_of_year'] = all_days['date'].dt.dayofyear
    all_days['week'] = all_days['date'].dt.isocalendar().week
    all_days['day_of_week'] = all_days['date'].dt.weekday
    all_days['pages'] = 0  # Default to 0 pages

    # Merge with your aggregated log data (grouped_log)
    merged = pd.merge(all_days, df[['date', 'day_of_year', 'week', 'day_of_week', 'pages']],
                      on=['day_of_year', 'week', 'day_of_week'], how='left', suffixes=('_left', '_right'))
    merged['pages'] = merged['pages_right'].fillna(merged['pages_left'])
    merged['pages'] = merged['pages'].fillna(0)

    # Carry over the original date from `all_days`
    merged['date'] = merged['date_left']

    # Create the heatmap using Plotly
    fig = go.Figure(data=go.Heatmap(
        z=merged['pages'],
        x=merged['week'],
        y=merged['day_of_week'],
        colorscale='Greens',
        showscale=True,
        hovertemplate='Date: %{text}<br>Pages: %{z}<extra></extra>',
        text=merged['date'].dt.strftime('%Y-%m-%d'),
        xgap=3, ygap=3
    ))

    fig.update_layout(
        xaxis_nticks=52,
        yaxis_nticks=7,
        yaxis=dict(tickmode='array', tickvals=[0, 1, 2, 3, 4, 5, 6],
                   ticktext=list(calendar.day_abbr)),
        xaxis=dict(title='Week of Year'),
        title="Daily Reading Heatmap",)

    return fig


def create_daily_pages_chart(df_daily_log_grouped):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=df_daily_log_grouped['date'],
            y=df_daily_log_grouped['pages'],
            name='Daily Pages', marker_color='rgba(65, 105, 225, 0.7)',
            text=df_daily_log_grouped['pages'],
            textposition='inside',
            textfont=dict(color='white')
        )
    )
    fig.update_layout(
        xaxis_title='Date',
        yaxis_title='Daily Pages',
        hovermode='x unified',
        title='Daily Pages Read',
    )
    fig.update_traces(
        hovertemplate='Pages: %{y}<extra></extra>', selector=dict(type='bar'))
    fig.update_traces(
        hovertemplate='Cumulative Pages: %{y}<extra></extra>', selector=dict(type='scatter'))

    return fig


st.set_page_config(
    page_title=f"Daily Reading Habit Tracker ({YEAR})",
    layout="wide"
)

if 'daily_log' not in st.session_state:
    if os.path.exists(DAILY_LOG_FILE):
        st.session_state.daily_log = pd.read_csv(DAILY_LOG_FILE)
    else:
        st.session_state.daily_log = pd.DataFrame(columns=['date', 'pages'])
    if not st.session_state.daily_log.empty:
        st.session_state.daily_log['date'] = pd.to_datetime(
            st.session_state.daily_log['date']).dt.date

st.title(f"📅 Daily Reading Habit Tracker for {YEAR}")

with st.form(key='daily_log_form'):
    log_date = st.date_input("Date", value=datetime.now().date())
    pages_read = st.number_input(
        "Pages Read", min_value=0, max_value=30, value=1)
    if st.form_submit_button("Log Reading"):
        if log_date <= date.today():
            st.session_state.daily_log = log_daily_reading(
                st.session_state.daily_log, log_date, pages_read)
            st.success("Reading logged successfully!")
            st.rerun()
        else:
            st.error("You cannot log reading for a future date.")

if not st.session_state.daily_log.empty:
    daily_stats = get_daily_stats(st.session_state.daily_log)
    df_daily_log_grouped = daily_stats['grouped_log']
    daily_goal = 10
    current_streak, max_streak = calculate_streak(
        df_daily_log_grouped, daily_goal
    )

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.markdown("**📚 Pages Goal:**")
    col2.markdown("**🔥 Current Streak:**")
    col3.markdown("**📈 Total Pages:**")
    col4.markdown("**🏆 Longest Streak:**")
    col5.markdown("**✅ Days Met Goal:**")
    col6.markdown("**📅 Avg (7 Days):**")

    col1.markdown(f":blue[**{daily_goal} pages/day**]")
    col2.markdown(f":red[**{current_streak} days**]")
    col3.markdown(f":blue[**{daily_stats['total_pages']}**]")
    col4.markdown(f":orange[**{max_streak} days**]")
    col5.markdown(f":green[**{(df_daily_log_grouped['pages']
                  >= daily_goal).sum()} / {len(df_daily_log_grouped)}**]")
    col6.markdown(f":blue[**{daily_stats['avg_pages_per_day']
                  :.2f} ({daily_stats['avg_pages_last_week']:.2f})**]")

    # st.plotly_chart(
    #     create_daily_pages_chart(df_daily_log_grouped),
    #     use_container_width=True
    # )
    st.plotly_chart(
        create_heatmap_view(df_daily_log_grouped),
        use_container_width=True
    )


else:
    st.info("No daily reading log entries yet.")
