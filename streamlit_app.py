"""
Streamlit Web UI for AI Recruitment Screening Assistant.
Connects to the FastAPI backend to manage jobs, trigger screening, rank candidates, and record HR decisions.
"""

import os
import requests
import pandas as pd
import streamlit as st



st.set_page_config(
    page_title="AI Recruitment Assistant",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")



st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0.2rem; }
    .sub-title { font-size: 1rem; color: #64748B; margin-bottom: 1.5rem; }
    .metric-card { background-color: #F8FAFC; border-radius: 8px; padding: 15px; border-left: 4px solid #3B82F6; }
    .badge-qualified { background-color: #DCFCE7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-unqualified { background-color: #FEE2E2; color: #991B1B; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-shortlist { background-color: #DBEAFE; color: #1E40AF; padding: 4px 8px; border-radius: 4px; }
    .badge-reject { background-color: #F1F5F9; color: #475569; padding: 4px 8px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """Checks if FastAPI backend is reachable."""
    try:
        r = requests.get(f"{API_BASE_URL}/", timeout=2)
        return r.status_code == 200
    except Exception:
        return False




with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3850/3850285.png", width=65)
    st.title("Recruitment AI")
    st.caption("v2.0 • Screening & Ranking")

    api_online = check_api_health()
    if api_online:
        st.success("🟢 Backend API: Online")
    else:
        st.error("🔴 Backend API: Offline")
        st.warning(f"تأكد من تشغيل خادم FastAPI:\n\n`uvicorn src.api:app --reload --port 8000`")

    st.markdown("---")
    menu = st.radio(
        "Navigation / التنقل",
        ["📊 Candidates & Ranking", "⚙️ Job Requirements", "📥 Screen & Upload CVs"]
    )
    st.markdown("---")
    st.info("💡 Developed for automated HR CV screening using LLM & Semantic Similarity.")




if menu == "📊 Candidates & Ranking":
    st.markdown('<div class="main-title">Candidates Screening & Ranking Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Review qualified candidates, inspect AI evidence, and make hiring decisions.</div>', unsafe_allow_html=True)

    if not api_online:
        st.error("Cannot connect to FastAPI backend. Please run `uvicorn src.api:app --reload --port 8000`.")
        st.stop()



    try:
        stats_resp = requests.get(f"{API_BASE_URL}/api/stats").json()
    except Exception as e:
        stats_resp = {"total_screened": 0, "qualified": 0, "non_qualified": 0, "statuses": {}}

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Screened", stats_resp.get("total_screened", 0))
    with col2:
        st.metric("Qualified (Met Must-Haves)", stats_resp.get("qualified", 0))
    with col3:
        st.metric("Missing Must-Haves", stats_resp.get("non_qualified", 0))
    with col4:
        st.metric("Shortlisted by HR", stats_resp.get("statuses", {}).get("Shortlist", 0))

    st.markdown("---")




    f_col1, f_col2, f_col3 = st.columns([2, 2, 1])
    with f_col1:
        filter_type = st.selectbox(
            "Filter Candidates List:",
            ["all", "shortlist", "qualified", "non_qualified"],
            format_func=lambda x: {
                "all": "All Candidates (الكل)",
                "shortlist": "Top Shortlist Only (أفضل المرشحين)",
                "qualified": "Qualified Only (المؤهلون للشروط الإلزامية)",
                "non_qualified": "Missing Must-Haves (غير مستوفي الشروط الإلزامية)"
            }[x]
        )
    with f_col2:
        status_filter = st.selectbox(
            "HR Decision Status:",
            ["All", "New", "Shortlist", "Review Later", "Reject"]
        )
    with f_col3:
        top_n = st.number_input("Shortlist Top N:", min_value=1, max_value=50, value=20)




    params = {"filter_type": filter_type, "top_n": top_n}
    if status_filter != "All":
        params["status"] = status_filter

    candidates_data = requests.get(f"{API_BASE_URL}/api/candidates", params=params).json()
    candidates = candidates_data.get("candidates", [])

    if not candidates:
        st.warning("No candidates found matching the selected criteria.")
    else:
        st.write(f"Showing **{len(candidates)}** candidate(s):")

        for cand in candidates:
            cand_id = cand.get("id")
            name = cand.get("candidate_name", "Unknown")
            email = cand.get("sender_email", "")
            eval_info = cand.get("evaluation", {})
            score = eval_info.get("score_percentage", 0.0)
            is_qualified = eval_info.get("is_qualified", False)
            hr_status = cand.get("hr_status", "New")
            missing_must = eval_info.get("missing_must_haves", [])

            qual_badge = "✅ Qualified" if is_qualified else f"⚠️ Missing {len(missing_must)} Must-Have(s)"

            with st.expander(f"👤 {name} — Score: {score}% | {qual_badge} | Status: [{hr_status}]"):
                c_top1, c_top2 = st.columns([3, 1])
                with c_top1:
                    st.write(f"**Email:** `{email}` | **File:** `{cand.get('cv_filename')}`")
                    if missing_must:
                        st.error(f"❌ **Missing Must-Have Requirements:**")
                        for m in missing_must:
                            st.write(f"- **{m.get('category').title()}**: {m.get('requirement')}")

                with c_top2:
                    st.metric("Overall Match Score", f"{score}%")

                st.markdown("#### Candidate Extracted Qualifications")
                quals = cand.get("candidate_qualifications", {})
                q_col1, q_col2, q_col3 = st.columns(3)
                with q_col1:
                    st.write("**Skills:**", ", ".join(quals.get("skills", [])) or "None detected")
                with q_col2:
                    st.write("**Experience:**", ", ".join(quals.get("experience", [])) or "None detected")
                with q_col3:
                    st.write("**Education:**", ", ".join(quals.get("education", [])) or "None detected")

                st.markdown("#### Requirements Evaluation & AI Evidence")
                all_evals = eval_info.get("all_results", [])
                if all_evals:
                    eval_df = pd.DataFrame([
                        {
                            "Category": e.get("category", "").title(),
                            "Requirement": e.get("requirement", ""),
                            "Result": e.get("result", ""),
                            "Similarity": e.get("similarity_score", 0.0),
                            "AI Evidence": e.get("evidence", "")
                        } for e in all_evals
                    ])
                    st.dataframe(eval_df, use_container_width=True)



                st.markdown("#### HR Review & Decision")
                dec_col1, dec_col2, dec_col3, dec_col4 = st.columns([1.5, 1, 1, 1])
                with dec_col1:
                    notes_input = st.text_input("HR Notes:", value=cand.get("hr_notes", ""), key=f"notes_{cand_id}")

                with dec_col2:
                    if st.button("⭐ Shortlist", key=f"btn_short_{cand_id}"):
                        requests.patch(f"{API_BASE_URL}/api/candidates/{cand_id}/status", json={"status": "Shortlist", "notes": notes_input})
                        st.success("Candidate Shortlisted!")
                        st.experimental_rerun()

                with dec_col3:
                    if st.button("⏳ Review Later", key=f"btn_rev_{cand_id}"):
                        requests.patch(f"{API_BASE_URL}/api/candidates/{cand_id}/status", json={"status": "Review Later", "notes": notes_input})
                        st.info("Marked for Review Later")
                        st.experimental_rerun()

                with dec_col4:
                    if st.button("❌ Reject", key=f"btn_rej_{cand_id}"):
                        requests.patch(f"{API_BASE_URL}/api/candidates/{cand_id}/status", json={"status": "Reject", "notes": notes_input})
                        st.warning("Candidate Rejected")
                        st.experimental_rerun()




elif menu == "⚙️ Job Requirements":
    st.markdown('<div class="main-title">Job Requirements Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Configure essential (Must-Have) and optional (Nice-to-Have) criteria.</div>', unsafe_allow_html=True)

    if not api_online:
        st.error("FastAPI Backend is offline.")
        st.stop()

    job_data = requests.get(f"{API_BASE_URL}/api/job").json()
    job_title = st.text_input("Job Title:", value=job_data.get("title", "AI Developer"))

    tab_must, tab_nice, tab_ai = st.tabs(["🔴 Must-Have (إلزامي)", "🟢 Nice-to-Have (مفضل)", "🤖 AI Requirement Extractor"])

    must = job_data.get("must_have", {})
    nice = job_data.get("nice_to_have", {})

    with tab_must:
        st.subheader("Must-Have Criteria (Any missing requirement will disqualify candidate)")
        must_skills = st.text_area("Must-Have Skills (comma-separated):", ", ".join(must.get("skills", [])))
        must_exp = st.text_area("Must-Have Experience (comma-separated):", ", ".join(must.get("experience", [])))
        must_edu = st.text_area("Must-Have Education (comma-separated):", ", ".join(must.get("education", [])))
        must_lang = st.text_area("Must-Have Languages (comma-separated):", ", ".join(must.get("languages", [])))

    with tab_nice:
        st.subheader("Nice-to-Have Criteria (Boosts candidate match score)")
        nice_skills = st.text_area("Nice-to-Have Skills (comma-separated):", ", ".join(nice.get("skills", [])))
        nice_exp = st.text_area("Nice-to-Have Experience (comma-separated):", ", ".join(nice.get("experience", [])))
        nice_certs = st.text_area("Certifications (comma-separated):", ", ".join(nice.get("certifications", [])))

    with tab_ai:
        st.subheader("Extract Requirements from Raw Job Description using AI")
        raw_jd = st.text_area("Paste full Job Description text here:", height=150)
        if st.button("🚀 Parse with AI (Ollama)"):
            with st.spinner("AI is analyzing Job Description..."):
                resp = requests.post(f"{API_BASE_URL}/api/job/extract", json={"job_description_text": raw_jd})
                if resp.status_code == 200:
                    st.success("Extracted successfully!")
                    st.json(resp.json().get("extracted_requirements", {}))
                else:
                    st.error("Failed to extract requirements.")

    st.markdown("---")
    if st.button("💾 Save Job Requirements", type="primary"):
        def to_list(txt):
            return [x.strip() for x in txt.split(",") if x.strip()]

        new_config = {
            "title": job_title,
            "must_have": {
                "skills": to_list(must_skills),
                "experience": to_list(must_exp),
                "education": to_list(must_edu),
                "languages": to_list(must_lang),
                "certifications": []
            },
            "nice_to_have": {
                "skills": to_list(nice_skills),
                "experience": to_list(nice_exp),
                "education": [],
                "languages": [],
                "certifications": to_list(nice_certs)
            }
        }
        res = requests.post(f"{API_BASE_URL}/api/job", json=new_config)
        if res.status_code == 200:
            st.success("Job requirements successfully saved and applied to screening system!")
        else:
            st.error("Error saving job configuration.")




elif menu == "📥 Screen & Upload CVs":
    st.markdown('<div class="main-title">Screening Operations</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Automate Gmail CV collection or manually upload and screen new CVs.</div>', unsafe_allow_html=True)

    if not api_online:
        st.error("FastAPI Backend is offline.")
        st.stop()

    tab1, tab2 = st.tabs(["📧 Gmail Automated Screening", "📤 Direct File Upload"])

    with tab1:
        st.subheader("Fetch and Screen CVs from Gmail")
        st.write("Scans HR inbox for application emails with attached PDF / DOCX resumes.")
        max_em = st.slider("Max emails to scan:", min_value=1, max_value=30, value=10)

        if st.button("🔄 Start Gmail Screening Process", type="primary"):
            with st.spinner("Fetching emails and screening candidates..."):
                res = requests.post(f"{API_BASE_URL}/api/screen/gmail", params={"max_emails": max_em})
                if res.status_code == 200:
                    summary = res.json().get("summary", {})
                    st.success("Screening cycle completed successfully!")
                    st.write(f"- **Total Emails Found:** {summary.get('total_found')}")
                    st.write(f"- **Processed Emails:** {summary.get('processed')}")
                    st.write(f"- **Already Screened (Skipped):** {summary.get('skipped')}")
                    st.write(f"- **New CVs Evaluated:** {summary.get('new_cvs')}")
                else:
                    st.error(f"Screening failed: {res.text}")

    with tab2:
        st.subheader("Manual CV Upload & Immediate Screening")
        uploaded_file = st.file_uploader("Upload CV (PDF or DOCX):", type=["pdf", "docx"])
        cand_name_input = st.text_input("Candidate Name (Optional):", value="")

        if uploaded_file and st.button("⚡ Screen Uploaded CV"):
            with st.spinner("Parsing and evaluating CV against active job criteria..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                data = {"candidate_name": cand_name_input or uploaded_file.name}
                res = requests.post(f"{API_BASE_URL}/api/screen/upload", files=files, data=data)
                if res.status_code == 200:
                    st.success("CV screened successfully!")
                    c_res = res.json().get("candidate", {})
                    eval_res = c_res.get("evaluation", {})
                    st.write(f"**Score:** {eval_res.get('score_percentage')}%")
                    st.write(f"**Qualified:** {'Yes ✅' if eval_res.get('is_qualified') else 'No ❌'}")
                    st.json(eval_res)
                else:
                    st.error(f"Error screening CV: {res.text}")
                    
                    