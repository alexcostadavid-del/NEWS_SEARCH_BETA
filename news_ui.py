import os, sys, streamlit as st

from news import fetch_news_paginated, rank_and_format

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

st.title("Company News Search 🔍")
company = st.text_input("Company name", value="Microsoft")
limit = st.number_input("Number of articles", min_value=1, max_value=100, value=10)

if st.button("Search"):
    if not SERPAPI_KEY:
        st.error("SERPAPI_KEY not set. Add it in Streamlit Secrets or set an env var.")
    elif not company.strip():
        st.warning("Enter a company name.")
    else:
        with st.spinner("Fetching..."):
            progress_bar = st.progress(0)
            status_text = st.empty()

            def _progress_cb(page_num, total_found):
                try:
                    pct = min(100, int(total_found / limit * 100)) if limit else 100
                except Exception:
                    pct = 0
                progress_bar.progress(pct)
                status_text.text(f"Fetched {total_found} articles (page {page_num})")

            articles = fetch_news_paginated(
                company,
                SERPAPI_KEY,
                limit=limit,
                page_size=min(50, max(10, limit)),
                max_pages=6,
                progress_callback=_progress_cb,
            )
            # finalize progress
            progress_bar.progress(100)
            status_text.text(f"Finished — fetched {len(articles)} articles")

            scored = rank_and_format(articles, company)
            if not scored:
                st.info("Empty Day — no articles found.")
            else:
                if len(scored) < limit:
                    st.info(f"Showing {len(scored)} of requested {limit} articles (fewer results available).")
                for i, (score, art) in enumerate(scored[:limit], 1):
                    st.subheader(f"{i}. {art.get('title','(no title)')}")
                    st.write(f"**Source:** {art.get('source','?')} • **Date:** {art.get('date','?')}")
                    st.write(art.get('snippet',''))
                    st.markdown(f"[Read more]({art.get('link','')})")
                    st.write(f"**Relevance:** {score:.2f}")
                    st.write("---")
