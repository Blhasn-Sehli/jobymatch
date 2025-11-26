import streamlit as st
import json
import os
import tempfile
from datetime import datetime
import pandas as pd
import sys
import traceback

# Import your existing classes
from mixed_scraper import UnifiedJobScraper
from cv_parser_v2 import parse_cv, display_cv_summary

# Configure the Streamlit page
st.set_page_config(
    page_title="AI Job Search Assistant",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

def clean_json_data(data):
    """Recursively clean data to ensure it's JSON serializable with UTF-8"""
    if isinstance(data, dict):
        return {key: clean_json_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [clean_json_data(item) for item in data]
    elif isinstance(data, str):
        # Remove or replace non-UTF-8 characters
        return data.encode('utf-8', 'ignore').decode('utf-8')
    elif isinstance(data, (int, float)):
        # Convert numbers to string for consistency
        return str(data)
    elif data is None:
        return ""
    else:
        return str(data)  # Convert any other type to string

def save_cv_to_folder(cv_data):
    """Save CV data directly to results folder (overwrite existing)"""
    # Create results folder if it doesn't exist
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)
    
    # Clean the data before saving
    cleaned_data = clean_json_data(cv_data)
    
    # Save CV data (overwrite if exists)
    cv_path = os.path.join(results_dir, "parsed_cv.json")
    with open(cv_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    
    return cv_path

def save_jobs_to_folder(jobs_data):
    """Save jobs data directly to results folder (overwrite existing)"""
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)
    
    jobs_path = os.path.join(results_dir, "job_results.json")
    
    # Clean jobs data
    cleaned_jobs = clean_json_data(jobs_data)
    
    output = {
        'search_date': datetime.now().isoformat(),
        'total_matches': len(cleaned_jobs),
        'jobs': cleaned_jobs
    }
    
    # Overwrite existing file
    with open(jobs_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    return jobs_path

def main():
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2e86ab;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #2e86ab;
    }
    .job-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 5px solid #2e86ab;
    }
    .match-score {
        font-weight: bold;
        font-size: 1.2rem;
    }
    .high-match { color: #28a745; }
    .medium-match { color: #ffc107; }
    .low-match { color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<h1 class="main-header">💼 AI Job Search Assistant</h1>', unsafe_allow_html=True)
    st.markdown("""
    **Upload your CV, find matching jobs, and generate application emails - all in one place!**
    
    This tool combines:
    - 📄 **CV Parsing** with AI (Llama 3.2)
    - 🔍 **Job Scraping** from Tunisia + International sites
    - ✉️ **Email Generation** for job applications
    """)

    # Initialize session state variables
    if 'cv_data' not in st.session_state:
        st.session_state.cv_data = None
    if 'jobs_data' not in st.session_state:
        st.session_state.jobs_data = None
    if 'selected_job' not in st.session_state:
        st.session_state.selected_job = None
    if 'parsing_complete' not in st.session_state:
        st.session_state.parsing_complete = False
    if 'scraping_complete' not in st.session_state:
        st.session_state.scraping_complete = False

    # Sidebar for navigation and settings
    with st.sidebar:
        st.header("Navigation")
        page = st.radio("Go to:", ["📄 Upload CV", "🔍 Search Jobs", "✉️ Generate Email"])
        
        st.header("Settings")
        min_score = st.slider("Minimum Match Score (%)", 10, 50, 15)
        max_jobs = st.slider("Maximum Jobs to Show", 10, 100, 50)
        hours_old = st.selectbox("Jobs Posted Within", 
                               [168, 720, 1440, 2160], 
                               index=1,
                               format_func=lambda x: f"{x//24} days" if x >= 24 else f"{x} hours")

        if st.session_state.cv_data:
            st.header("CV Summary")
            st.write(f"**Name:** {st.session_state.cv_data.get('name', 'N/A')}")
            st.write(f"**Title:** {st.session_state.cv_data.get('title', 'N/A')}")
            
        if st.session_state.jobs_data:
            st.header("Search Results")
            st.write(f"**Jobs Found:** {len(st.session_state.jobs_data)}")
            if st.session_state.jobs_data:
                avg_score = sum(job.get('match_score', 0) for job in st.session_state.jobs_data) / len(st.session_state.jobs_data)
                st.write(f"**Average Match:** {avg_score:.1f}%")

    # Page 1: CV Upload and Parsing
    if page == "📄 Upload CV":
        st.markdown('<h2 class="section-header">Upload and Parse Your CV</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_file = st.file_uploader("Choose a PDF CV", type="pdf", help="Upload your CV in PDF format")
            
            if uploaded_file is not None:
                # Display file info
                file_details = {
                    "Filename": uploaded_file.name,
                    "File size": f"{uploaded_file.size / 1024:.1f} KB"
                }
                st.write("File details:", file_details)
                
                # Parse CV button
                if st.button("🚀 Parse CV with AI", type="primary", use_container_width=True):
                    with st.spinner("🤖 AI is analyzing your CV... This may take a minute."):
                        try:
                            # Save uploaded file to temporary file
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                tmp_path = tmp_file.name
                            
                            # Parse the CV
                            cv_data = parse_cv(tmp_path)
                            
                            # Store in session state
                            st.session_state.cv_data = cv_data
                            st.session_state.parsing_complete = True
                            
                            # Save directly to results folder (overwrite)
                            cv_path = save_cv_to_folder(cv_data)
                            
                            # Clean up temporary file
                            os.unlink(tmp_path)
                            
                            st.success("✅ CV parsed successfully!")
                            st.info(f"📁 CV saved to: `{cv_path}`")
                            
                        except Exception as e:
                            st.error(f"❌ Error parsing CV: {str(e)}")
        
        with col2:
            if st.session_state.parsing_complete and st.session_state.cv_data:
                st.success("CV Ready!")
                st.balloons()
                
                # Quick CV preview
                cv_data = st.session_state.cv_data
                st.subheader("CV Preview")
                st.write(f"**Name:** {cv_data.get('name', 'N/A')}")
                st.write(f"**Email:** {cv_data.get('email', 'N/A')}")
                st.write(f"**Title:** {cv_data.get('title', 'N/A')}")
                
                if 'skills' in cv_data and 'technical' in cv_data['skills']:
                    st.write("**Top Skills:**")
                    for skill in cv_data['skills']['technical'][:5]:
                        st.write(f"- {skill}")

        # Show detailed CV information after parsing
        if st.session_state.parsing_complete and st.session_state.cv_data:
            st.markdown('<h2 class="section-header">Detailed CV Analysis</h2>', unsafe_allow_html=True)
            
            cv_data = st.session_state.cv_data
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("👤 Personal Info")
                st.write(f"**Name:** {cv_data.get('name', 'N/A')}")
                st.write(f"**Email:** {cv_data.get('email', 'N/A')}")
                st.write(f"**Phone:** {cv_data.get('phone', 'N/A')}")
                
                if 'job_search_intent' in cv_data:
                    st.subheader("🎯 Job Search Intent")
                    intent = cv_data['job_search_intent']
                    st.write(f"**Type:** {intent.get('type', 'N/A')}")
                    st.write(f"**Level:** {intent.get('level', 'N/A')}")
                    st.write(f"**Domains:** {', '.join(intent.get('domains', []))}")
                    st.write(f"**Location:** {intent.get('location_preference', 'N/A')}")
            
            with col2:
                st.subheader("🎓 Education")
                for edu in cv_data.get('education', [])[:3]:
                    st.write(f"**{edu.get('degree', 'N/A')}**")
                    st.write(f"{edu.get('institution', 'N/A')} - {edu.get('period', 'N/A')}")
                    st.write("---")
                
                st.subheader("🌍 Languages")
                for lang in cv_data.get('languages', []):
                    st.write(f"**{lang.get('language', 'N/A')}:** {lang.get('level', 'N/A')}")
            
            with col3:
                st.subheader("🛠️ Skills")
                skills = cv_data.get('skills', {})
                if 'technical' in skills:
                    st.write("**Technical:**")
                    for skill in skills['technical'][:10]:
                        st.write(f"- {skill}")
                
                if 'tools' in skills:
                    st.write("**Tools:**")
                    for tool in skills['tools'][:5]:
                        st.write(f"- {tool}")

    # Page 2: Job Search
    elif page == "🔍 Search Jobs":
        st.markdown('<h2 class="section-header">Find Matching Jobs</h2>', unsafe_allow_html=True)
        
        if not st.session_state.parsing_complete:
            st.warning("⚠️ Please upload and parse your CV first on the 'Upload CV' page.")
            return
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info(f"Ready to search jobs for: **{st.session_state.cv_data.get('name', 'Candidate')}**")
            
            # Show search parameters
            search_term = st.session_state.cv_data.get('title', '')
            if not search_term and st.session_state.cv_data.get('job_search_intent', {}).get('domains'):
                search_term = st.session_state.cv_data['job_search_intent']['domains'][0]
            
            st.write(f"**Search term:** {search_term}")
            st.write(f"**Location preference:** {st.session_state.cv_data.get('job_search_intent', {}).get('location_preference', 'Any')}")
        
        with col2:
            if st.button("🔍 Search Jobs", type="primary", use_container_width=True):
                with st.spinner("🕵️‍♂️ Searching for matching jobs... This may take a few minutes."):
                    try:
                        # Save CV to results folder (overwrite)
                        cv_path = save_cv_to_folder(st.session_state.cv_data)

                        # Initialize scraper and search jobs
                        scraper = UnifiedJobScraper()
                        jobs = scraper.scrape_and_match(
                            cv_json_path=cv_path,
                            min_score=min_score,
                            max_results=max_jobs,
                            hours_old=hours_old
                        )
                        
                        # Store results
                        st.session_state.jobs_data = jobs
                        st.session_state.scraping_complete = True
                        
                        # Save jobs to results folder (overwrite)
                        jobs_path = save_jobs_to_folder(jobs)
                        
                        scraper.cleanup()
                        
                        st.success(f"✅ Found {len(jobs)} matching jobs!")
                        st.info(f"📁 Jobs saved to: `{jobs_path}`")
                        
                    except Exception as e:
                        st.error(f"❌ Error during job search: {str(e)}")
                        st.code(traceback.format_exc())
        
        # Display job results
        if st.session_state.scraping_complete and st.session_state.jobs_data:
            jobs = st.session_state.jobs_data
            
            st.markdown(f'<h3 class="section-header">📊 Found {len(jobs)} Matching Jobs</h3>', unsafe_allow_html=True)
            
            # Summary statistics
            if jobs:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Jobs", len(jobs))
                with col2:
                    avg_score = sum(job.get('match_score', 0) for job in jobs) / len(jobs)
                    st.metric("Average Match", f"{avg_score:.1f}%")
                with col3:
                    high_match = len([j for j in jobs if j.get('match_score', 0) >= 70])
                    st.metric("High Matches (70%+)", high_match)
                with col4:
                    tunisia_jobs = len([j for j in jobs if 'tunis' in str(j.get('location', '')).lower()])
                    st.metric("Jobs in Tunisia", tunisia_jobs)
                
                # Job sources
                sources = {}
                for job in jobs:
                    site = job.get('site', 'Unknown')
                    sources[site] = sources.get(site, 0) + 1
                
                st.write("**Job Sources:**")
                source_cols = st.columns(len(sources))
                for i, (source, count) in enumerate(sources.items()):
                    with source_cols[i]:
                        st.metric(source, count)
                
                # Job list with selection
                st.markdown('<h3 class="section-header">🎯 Job Opportunities</h3>', unsafe_allow_html=True)
                
                for i, job in enumerate(jobs):
                    # Determine match score color
                    score = job.get('match_score', 0)
                    if score >= 70:
                        score_class = "high-match"
                    elif score >= 40:
                        score_class = "medium-match"
                    else:
                        score_class = "low-match"
                    
                    # Create job card
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"### {job.get('title', 'No Title')}")
                            st.write(f"**Company:** {job.get('company', 'N/A')} | **Location:** {job.get('location', 'N/A')}")
                            st.write(f"**Source:** {job.get('site', 'N/A')}")
                            
                            if job.get('description'):
                                with st.expander("View Job Description"):
                                    st.write(job['description'][:500] + "..." if len(job['description']) > 500 else job['description'])
                        
                        with col2:
                            st.markdown(f'<div class="match-score {score_class}">{score}% Match</div>', unsafe_allow_html=True)
                            
                            # Select job button
                            if st.button(f"Select #{i+1}", key=f"select_{i}", use_container_width=True):
                                st.session_state.selected_job = job
                                st.success(f"✅ Selected: {job.get('title', 'Job')} at {job.get('company', 'Company')}")
                            
                            if job.get('url'):
                                st.markdown(f"[View Original]({job['url']})", unsafe_allow_html=True)
                        
                        st.markdown("---")

    # Page 3: Generate Email
    elif page == "✉️ Generate Email":
        st.markdown('<h2 class="section-header">Generate Application Email</h2>', unsafe_allow_html=True)
        
        if not st.session_state.scraping_complete:
            st.warning("⚠️ Please search for jobs first on the 'Search Jobs' page.")
            return
        
        if not st.session_state.selected_job:
            st.warning("⚠️ Please select a job first from the search results.")
            return
        
        job = st.session_state.selected_job
        cv_data = st.session_state.cv_data
        
        # Display selected job info
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.success("🎯 Selected Job")
            st.markdown(f"### {job.get('title', 'No Title')}")
            st.write(f"**Company:** {job.get('company', 'N/A')}")
            st.write(f"**Location:** {job.get('location', 'N/A')}")
            st.write(f"**Source:** {job.get('site', 'N/A')}")
            st.write(f"**Match Score:** {job.get('match_score', 0)}%")
            
            if job.get('url'):
                st.markdown(f"[View Original Job Posting]({job['url']})")
        
        with col2:
            st.info("Candidate Info")
            st.write(f"**Name:** {cv_data.get('name', 'N/A')}")
            st.write(f"**Email:** {cv_data.get('email', 'N/A')}")
            st.write(f"**Title:** {cv_data.get('title', 'N/A')}")
        
        # Email generation section
        st.markdown('<h3 class="section-header">✉️ Application Email</h3>', unsafe_allow_html=True)
        
        # Email template parameters
        col1, col2 = st.columns(2)
        
        with col1:
            email_subject = st.text_input(
                "Email Subject",
                value=f"Application for {job.get('title', 'Position')} - {cv_data.get('name', 'Candidate')}",
                help="Customize the email subject line"
            )
            
            tone = st.selectbox(
                "Email Tone",
                ["Professional", "Enthusiastic", "Formal", "Concise"],
                help="Select the tone of your application email"
            )
        
        with col2:
            highlight_skills = st.multiselect(
                "Skills to Highlight",
                options=cv_data.get('skills', {}).get('technical', []),
                default=cv_data.get('skills', {}).get('technical', [])[:3],
                help="Select which skills to emphasize in your application"
            )
            
            include_availability = st.checkbox("Include Availability", value=True)
        
        # Generate email button
        if st.button("🪄 Generate Application Email", type="primary", use_container_width=True):
            with st.spinner("🤖 Generating personalized application email..."):
                try:
                    # Basic email template
                    email_body = f"""
Dear Hiring Manager,

I am writing to express my enthusiastic interest in the {job.get('title', 'position')} position at {job.get('company', 'your company')}, which I discovered through {job.get('site', 'your job board')}. With my background in {cv_data.get('title', 'my field')} and expertise in {', '.join(highlight_skills[:3])}, I am confident that I possess the skills and experience necessary to excel in this role.

{"I am available to start " + cv_data.get('job_search_intent', {}).get('availability', 'immediately') + " and am excited about the opportunity to contribute to your team." if include_availability else ""}

Key qualifications that align with your requirements include:
{chr(10).join(f"• {skill}" for skill in highlight_skills)}

I have attached my CV for your review and would welcome the opportunity to discuss how my skills and experience can benefit {job.get('company', 'your company')}. Thank you for considering my application.

Sincerely,
{cv_data.get('name', 'Candidate')}
{cv_data.get('email', '')}
{cv_data.get('phone', '')}
"""
                    
                    # Display generated email
                    st.text_area("Generated Email", email_body, height=300)
                    
                    # Email actions
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.download_button(
                            label="📥 Download Email",
                            data=email_body,
                            file_name=f"application_{job.get('company', 'company')}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    with col2:
                        if st.button("📋 Copy to Clipboard", use_container_width=True):
                            st.code(email_body)
                            st.success("Email copied to clipboard!")
                    with col3:
                        if st.button("🔄 Regenerate", use_container_width=True):
                            st.rerun()
                            
                except Exception as e:
                    st.error(f"❌ Error generating email: {str(e)}")

if __name__ == "__main__":
    main()