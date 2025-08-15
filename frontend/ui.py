from __future__ import annotations
import streamlit as st
from typing import List, Dict, Any, Callable

__all__ = ["show_summary", "show_articles"]

def show_summary(summary: Dict[str, Any]) -> None:
    """Render only the summary text (no highlights, no top sources)."""
    st.subheader("Personalized Summary")
    st.write(summary.get("summary", ""))

def show_articles(articles, is_client_safe=None, summaries=None):
    st.subheader("Articles")
    if not articles:
        st.info("No articles to show.")
        return

    for i, article in enumerate(articles):
        title = article.get("title", "No title")
        link = article.get("link", "")
        summary = summaries.get(link) if summaries else ""

        # Title
        st.markdown(f"### {title}")

        # FULL SUMMARY using CSS to prevent truncation
        if summary:
            st.markdown(
                f"""
                <div style='
                    font-size: 16px;
                    line-height: 1.6;
                    margin-top: -10px;
                    margin-bottom: 10px;
                    overflow-wrap: break-word;
                    white-space: normal;
                    display: block;
                '>
                    {summary}
                </div>
                """,
                unsafe_allow_html=True
            )

        # Link
        if link:
            st.markdown(f"[Read more]({link})")

        # Separator
        st.markdown("---")
