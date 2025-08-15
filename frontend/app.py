# frontend/app.py
import sys, os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
from settings import DEFAULT_USER_ID
from safety import is_client_safe
from topics import suggest_topics
from auth_client import register, login
import ui
import requests
from api_client import get_news as api_get_news, track_search, get_personal_topics, summarize_batch

st.set_page_config(page_title="Personalized News Aggregator", layout="wide")
st.title("Personalized News Aggregator")
st.caption("✅ frontend ready")

# Session state defaults
st.session_state.setdefault("query", "")
st.session_state.setdefault("related_topics", [])
st.session_state.setdefault("page", 1)
st.session_state.setdefault("page_size", 3)
st.session_state.setdefault("last_query", "")
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("token", None)
st.session_state.setdefault("auth_mode", "Login")
st.session_state.setdefault("location_enabled", False)
st.session_state.setdefault("country_name", "United States")
st.session_state.setdefault("region", "us")
st.session_state.setdefault("lang", "en")
st.session_state.setdefault("effective_region", "us")
st.session_state.setdefault("effective_lang", "en")

def _maybe_reset_pagination(current_q):
    if current_q != st.session_state.get("last_query", ""):
        st.session_state["page"] = 1
        st.session_state["last_query"] = current_q

# ---------------------------
# Auth UI
# ---------------------------
if not st.session_state["user_id"] or not st.session_state["token"]:
    st.subheader("Welcome — please sign in")

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        with st.form("login_form"):
            login_email = st.text_input("Email", key="login_email")
            login_pwd = st.text_input("Password", type="password", key="login_pwd")
            submitted_login = st.form_submit_button("Log in", use_container_width=True)

        if submitted_login:
            data, status, err = login(login_email, login_pwd)
            if err:
                st.error(f"Login failed ({status}): {err}")
            else:
                st.success("Login successful")
                st.session_state.update(user_id=data["user_id"], token=data["token"])
                st.rerun()

    with tab_register:
        with st.form("register_form"):
            reg_email = st.text_input("Email", key="register_email")
            reg_pwd = st.text_input("Password (min 6 chars)", type="password", key="register_pwd")
            submitted_register = st.form_submit_button("Create account", use_container_width=True)

        if submitted_register:
            data, status, err = register(reg_email, reg_pwd)
            if err:
                st.error(f"Registration failed ({status}): {err}")
            else:
                st.success("Registration successful — you’re now logged in")
                st.session_state.update(user_id=data["user_id"], token=data["token"])
                st.rerun()

    st.stop()

# ---------------------------
# Sidebar
# ---------------------------
with st.sidebar:
    st.header("Account")
    st.write(f"User ID: `{st.session_state['user_id']}`")
    if st.button("Log out", type="secondary", use_container_width=True):
        st.session_state.update(user_id=None, token=None, related_topics=[], query="")
        st.rerun()

    st.divider()
    st.header("Topics you might like")

    topics_to_show = st.session_state["related_topics"]
    if not topics_to_show:
        try:
            topics_to_show = get_personal_topics(
                user_id=st.session_state["user_id"], k=3, token=st.session_state["token"]
            )
        except Exception:
            topics_to_show = []

    if topics_to_show:
        for i, topic in enumerate(topics_to_show[:3]):
            if st.button(topic, key=f"topic_btn_{i}", use_container_width=True):
                st.session_state.update(query=topic, page=1)
                st.rerun()
    else:
        st.caption("Search to see suggestions.")

    st.divider()
    st.header("Location filter")
    COUNTRY_META = {
        "United States": ("us", "en"),
        "Germany": ("de", "de"),
        "United Kingdom": ("gb", "en"),
        "France": ("fr", "fr"),
        "Spain": ("es", "es"),
        "India": ("in", "en"),
    }

    loc_cb = st.checkbox(
        "Filter by my country",
        value=st.session_state.get("location_enabled", False),
        key="location_enabled_cb",
    )
    if st.session_state.get("location_enabled") != loc_cb:
        st.session_state["location_enabled"] = loc_cb

    def _on_country_change():
        country = st.session_state["country_select_sb"]
        reg, lng = COUNTRY_META.get(country, ("us", "en"))
        st.session_state.update(country_name=country, region=reg, lang=lng)
        if country != "United States":
            st.session_state["location_enabled"] = True

    country_names = list(COUNTRY_META.keys())
    idx = country_names.index(st.session_state.get("country_name", "United States"))
    st.selectbox(
        "Country", country_names, index=idx, key="country_select_sb", on_change=_on_country_change
    )

    use_location = st.session_state.get("location_enabled", False) or (
        st.session_state.get("country_name") != "United States"
    )
    reg = st.session_state.get("region", "us")
    lng = st.session_state.get("lang", "en")
    st.session_state["effective_region"] = reg if use_location else "us"
    st.session_state["effective_lang"] = lng if use_location else "en"

# ---------------------------
# Main Content
# ---------------------------
query = st.text_input("Enter a topic to search for news", value=st.session_state["query"], key="query_input")
_maybe_reset_pagination(query)

if query:
    try:
        data = api_get_news(
            query=query,
            user_id=st.session_state["user_id"] or DEFAULT_USER_ID,
            token=st.session_state.get("token"),
            page=st.session_state.get("page", 1),
            page_size=st.session_state.get("page_size", 10),
            region=st.session_state.get("effective_region", "us"),
            lang=st.session_state.get("effective_lang", "en"),
        )

        try:
            track_search(
                user_id=st.session_state["user_id"],
                query=query,
                token=st.session_state.get("token")
            )
        except Exception:
            pass

    except requests.HTTPError as e:
        st.error(f"Request failed: {e}")
        st.stop()

    summary = data.get("summary", {})
    articles = data.get("articles", [])
    st.session_state["related_topics"] = suggest_topics(articles, query, k=3)

    safe_articles = []
    for a in articles:
        title = a.get("title", "")
        snippet = a.get("snippet", "")
        try:
            if is_client_safe(f"{title}\n{snippet}"):
                safe_articles.append(a)
        except Exception:
            safe_articles.append(a)

    page_size = int(st.session_state["page_size"])
    total = len(safe_articles)
    total_pages = max(1, (total + page_size - 1) // page_size)
    cur_page = int(st.session_state["page"])
    cur_page = max(1, min(cur_page, total_pages))
    st.session_state["page"] = cur_page

    start = (cur_page - 1) * page_size
    end = start + page_size
    page_slice = safe_articles[start:end][:3]

    try:
        improved = summarize_batch(page_slice, token=st.session_state.get("token"))
        for a in page_slice:
            s = improved.get(a.get("link"))
            if s:
                a["ai_summary"] = s
    except Exception:
        pass

    ui.show_summary(summary)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("\u2190 Prev", disabled=(cur_page <= 1)):
            st.session_state["page"] = max(1, cur_page - 1)
            st.rerun()
    with c2:
        st.markdown(
            f"<div style='text-align:center;'>Page <b>{cur_page}</b> of <b>{total_pages}</b> — {total} articles</div>",
            unsafe_allow_html=True
        )
    with c3:
        if st.button("Next →", disabled=(cur_page >= total_pages)):
            st.session_state["page"] = min(total_pages, cur_page + 1)
            st.rerun()

    summaries = {}
    try:
        summaries = summarize_batch(
            page_slice,
            user_id=st.session_state["user_id"],
            token=st.session_state.get("token")
        )
    except Exception:
        summaries = {a["link"]: a.get("snippet", "") for a in page_slice}

    ui.show_articles(page_slice, is_client_safe, summaries=summaries)
else:
    st.info("Type a topic above to begin.")
    st.session_state["related_topics"] = []
