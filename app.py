"""
Mental Health Navigator: Streamlit wrapper.

The whole site (design, pages and the Jarvis guide) lives in index.html. This file only shows that page inside
Streamlit, so the Streamlit link keeps working. To change the site, edit index.html.

Run with:  streamlit run app.py
(The site also works on its own: open index.html in a browser, or host it on GitHub Pages.)
"""

import os

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Mental Health Navigator", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "index.html"), encoding="utf-8") as handle:
    SITE = handle.read()

# Hide Streamlit's own header, menu, footer and padding, and let the site fill the whole window.
st.markdown(
    """
    <style>
      header, footer, #MainMenu, [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
      .block-container, [data-testid="stMainBlockContainer"] { padding: 0 !important; max-width: 100% !important; }
      iframe { height: 100vh !important; width: 100% !important; border: 0 !important; display: block; }
    </style>
    """,
    unsafe_allow_html=True,
)

components.html(SITE, height=900, scrolling=True)
