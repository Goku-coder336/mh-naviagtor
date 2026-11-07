"""
NHS Mental Health Navigator
Free, open source navigation for people waiting for NHS mental health support.
Built by Gokul Rajan, github.com/Goku-coder336/mh-navigator

The whole website lives in index.html (the same file GitHub Pages serves).
This app shows that file full screen, so the Streamlit link and the
GitHub Pages link show the same site.

Run with:  streamlit run app.py
"""

from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Mental Health Navigator",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit's own header, menu and padding so only the website shows,
# and let the website fill the whole browser window.
st.markdown(
    """
    <style>
      header[data-testid="stHeader"], [data-testid="stToolbar"],
      [data-testid="stDecoration"], [data-testid="stStatusWidget"],
      #MainMenu, footer { display: none !important; }
      .block-container, [data-testid="stMainBlockContainer"] {
        padding: 0 !important; max-width: 100% !important;
      }
      [data-testid="stAppViewContainer"], .main, section.main { padding: 0 !important; }
      [data-testid="stVerticalBlock"] { gap: 0 !important; }
      iframe { display: block; width: 100% !important; height: 100vh !important; border: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

SITE = Path(__file__).parent / "index.html"

if not SITE.exists():
    st.error(
        "index.html was not found next to app.py. Upload index.html to the "
        "top folder of the repository, next to this file."
    )
    st.stop()

if hasattr(st, "iframe"):
    st.iframe(SITE, height=900)
else:  # older Streamlit versions
    import streamlit.components.v1 as components
    components.html(SITE.read_text(encoding="utf-8"), height=900, scrolling=True)
