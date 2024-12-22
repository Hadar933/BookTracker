import requests
import streamlit as st
import pandas as pd
from datetime import datetime, date
import os
from plotly_calplot import calplot
import plotly.express as px

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
    return current_streak+1, df['streak'].max()+1


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


def search_book_info(title):
    url = f'https://openlibrary.org/search.json?title={title}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['docs']:
            book_info = data['docs'][0]
            cover_id = book_info.get('cover_i', None)
            return {
                'raw_info': url,
                'url': f'https://openlibrary.org{book_info["key"]}',
                'title': book_info.get('title', ''),
                'author': ', '.join(book_info.get('author_name', [])),
                'cover_url': f'https://covers.openlibrary.org/b/id/{cover_id}-L.jpg' if cover_id else None
            }
    return None


if __name__ == '__main__':
    st.set_page_config(
        page_title=f"Daily Reading Habit Tracker ({YEAR})",
        layout="wide"
    )

    if 'daily_log' not in st.session_state:
        if os.path.exists(DAILY_LOG_FILE):
            st.session_state.daily_log = pd.read_csv(DAILY_LOG_FILE)
        else:
            st.session_state.daily_log = pd.DataFrame(
                columns=['date', 'pages'])
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
        col6.markdown(f":blue[**{daily_stats['avg_pages_per_day']:.2f} ({daily_stats['avg_pages_last_week']:.2f})**]")

        st.plotly_chart(
            calplot(
                data=df_daily_log_grouped,
                x='date',
                y='pages',
                name='Pages',
                gap=1,
                showscale=True,
                colorscale='greens'
            ),
            use_container_width=True
        )

    else:
        st.info("No daily reading log entries yet.")

    # Add Book Form
    st.subheader('Find and Add a New Book')
    with st.form(key='add_book'):
        search_title = st.text_input('Search Title', key='search_title')
        search_button = st.form_submit_button(label='Search')
    if search_button:
        book_info = search_book_info(search_title)
        if book_info:
            st.session_state['raw_info'] = book_info['raw_info']
            st.session_state['url'] = book_info['url']
            st.session_state['title'] = book_info['title']
            st.session_state['author'] = book_info['author']
            st.session_state['cover_url'] = book_info['cover_url']
        else:
            st.warning('Book not found')

    title = st.text_input('Title', key='title')
    author = st.text_input('Author', key='author')

    if st.session_state.get('cover_url'):
        col1, col2 = st.columns(2)
        with col1:
            st.image(st.session_state['cover_url'], width=150)
        with col2:
            st.link_button(
                'Raw Info', url=st.session_state['raw_info'] if 'raw_info' in st.session_state else '')
            st.link_button(
                'Open Library', url=st.session_state['url'] if 'url' in st.session_state else '')
    else:
        st.link_button(
            'Raw Info', url=st.session_state['raw_info'] if 'raw_info' in st.session_state else '')
        st.link_button(
            'Open Library', url=st.session_state['url'] if 'url' in st.session_state else '')
