import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI
import json
import random 

# Setup OpenAI Client using your secret key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="Autonomous Bar Exam Builder", page_icon="⚖️")

st.title("⚖️ Autonomous Bar Exam Builder")
st.write("Upload your MBE PDF. The AI will extract questions and cross-reference them with the book's official answer key to build your exam.")

# --- Initialize the App's "Memory" ---
if "exam_questions" not in st.session_state:
    st.session_state.exam_questions = None
if "exam_submitted" not in st.session_state:
    st.session_state.exam_submitted = False
if "layout_detected" not in st.session_state:
    st.session_state.layout_detected = False
if "q_range" not in st.session_state:
    st.session_state.q_range = (1, 30)
if "a_range" not in st.session_state:
    st.session_state.a_range = (31, 268)

uploaded_file = st.file_uploader("Upload your MBE PDF", type="pdf")

if uploaded_file:
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    st.write(f"**PDF loaded successfully!** Total pages: {len(doc)}")
    
    st.markdown("### 1. Locate the Sections")
    
    # --- UPGRADED: Multi-Part Answer Key Detection ---
    if not st.session_state.layout_detected:
        if st.button("🤖 Auto-Detect Sections (Multi-Chapter Mode)"):
            with st.spinner("Reading the Table of Contents to map chapters..."):
                toc_text = "".join([doc[i].get_text() for i in range(min(15, len(doc)))])
                
                toc_prompt = f"""
                Scan this Table of Contents from a Bar Exam prep book. 
                Identify the page where the first practice questions start.
                Then, identify the ranges for ALL 'Explanatory Answers' or 'Answer Key' sections.
                
                Return ONLY a JSON object:
                {{
                    "questions_start_page": int,
                    "answer_key_start": int,
                    "answer_key_end": int
                }}
                Text: {toc_text}
                """
                
                try:
                    toc_response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": toc_prompt}],
                        response_format={ "type": "json_object" }
                    )
                    layout = json.loads(toc_response.choices[0].message.content)
                    
                    q_start_val = layout.get("questions_start_page", 1)
                    a_start_val = layout.get("answer_key_start", q_start_val + 20)
                    a_end_val = layout.get("answer_key_end", len(doc))
                    
                    st.session_state.q_range = (q_start_val, a_start_val - 1)
                    st.session_state.a_range = (a_start_val, a_end_val)
                    st.session_state.layout_detected = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Auto-detect failed: {e}")
    
    if st.session_state.layout_detected:
        st.success("✅ Multi-part layout detected!")

    st.info("The AI will scan for questions and cross-reference them against the Answer Key range below.")
    
    a_start, a_end = st.slider("Full Answer Key Range (covers all chapters)", 1, len(doc), st.session_state.a_range)
    
    # Auto-calculate the scan area
    q_start = 1
    q_end = a_start - 1

    st.markdown("### 2. Build the Exam")
    if st.button("Scan PDF & Build Exam", type="primary"):
        st.warning("⏳ Deep scanning in progress. This may take a few minutes as we cross-reference multiple chapters. Please stay on this page.")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 1. Broad Answer Key Memorization
        status_text.text("📖 Memorizing all available Answer Keys...")
        answer_key_text = "".join([doc[i].get_text() for i in range(a_start - 1
