"""Synthetic demo stub. The live amber desk is `streamlit run app.py`."""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Wrong entry point — run app.py", page_icon=":material/warning:", layout="wide")
st.error("This file is a synthetic demo, not the delivery desk.")
st.markdown(
    """
Stop this process and start the real UI:

```bash
streamlit run app.py
```

You should see a dark ink background, a gold **NSE** mark, sidebar groups (Markets / Research / Portfolio / Macro), and the browser title **NSE desk · Amber**.
"""
)
st.stop()
