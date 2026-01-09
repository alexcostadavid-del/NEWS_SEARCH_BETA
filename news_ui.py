import os, sys, streamlit as st

from news import fetch_news, rank_and_format

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
            articles = fetch_news(company, SERPAPI_KEY, page=1, page_size=min(50, limit*2))
            scored = rank_and_format(articles, company)
            if not scored:
                st.info("Empty Day — no articles found.")
            else:
                for i, (score, art) in enumerate(scored[:limit], 1):
                    st.subheader(f"{i}. {art.get('title','(no title)')}")
                    st.write(f"**Source:** {art.get('source','?')} • **Date:** {art.get('date','?')}")
                    st.write(art.get('snippet',''))
                    st.markdown(f"[Read more]({art.get('link','')})")
                    st.write(f"**Relevance:** {score:.2f}")
                    st.write("---")
