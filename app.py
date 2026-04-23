import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI
import json
import random 

# Setup OpenAI Client using your secret key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("⚖️ Autonomous Bar Exam Builder")
st.write("Upload your MBE PDF. The AI will extract questions and cross-reference them with the book's official answer key to build your exam.")

# --- Initialize the App's "Memory" ---
if "exam_questions" not in st.session_state:
    st.session_state.exam_questions = None
if "exam_submitted" not in st.session_state:
    st.session_state.exam_submitted = False
# --- NEW: Memory for the Auto-Detected Pages ---
if "layout_detected" not in st.session_state:
    st.session_state.layout_detected = False
if "q_range" not in st.session_state:
    st.session_state.q_range = (1, 30)
if "a_range" not in st.session_state:
    st.session_state.a_range = (31, 60)

uploaded_file = st.file_uploader("Upload your MBE PDF", type="pdf")

if uploaded_file:
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    st.write(f"**PDF loaded successfully!** Total pages: {len(doc)}")
    
    st.markdown("### 1. Locate the Sections")
    
    # --- NEW: The AI Pre-Scan Button ---
    if not st.session_state.layout_detected:
        if st.button("🤖 Auto-Detect Sections from Table of Contents"):
            with st.spinner("Reading the Table of Contents..."):
                # Grab the first 15 pages where the TOC usually lives
                toc_text = "".join([doc[i].get_text() for i in range(min(15, len(doc)))])
                
                toc_prompt = f"""
                Scan this Table of Contents from a Bar Exam prep book. 
                Identify the starting page number for the practice Multiple Choice Questions, and the starting page number for the Explanatory Answers.
                If you can't find exact numbers, make your best logical guess based on the chapters.
                
                Return ONLY a JSON object:
                {{
                    "questions_start_page": int,
                    "answers_start_page": int
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
                    
                    q_start = layout.get("questions_start_page", 1)
                    a_start = layout.get("answers_start_page", q_start + 30)
                    
                    # Update memory with the AI's findings
                    st.session_state.q_range = (q_start, a_start - 1)
                    st.session_state.a_range = (a_start, min(a_start + 40, len(doc)))
                    st.session_state.layout_detected = True
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Auto-detect failed: {e}")
    
    # Show the sliders (pre-filled with AI's guess if auto-detected)
    if st.session_state.layout_detected:
        st.success("✅ Layout detected! You can fine-tune the AI's guess below if needed.")
        
    col1, col2 = st.columns(2)
    with col1:
        q_start, q_end = st.slider("Pages with Questions", 1, len(doc), st.session_state.q_range)
    with col2:
        a_start, a_end = st.slider("Pages with Answer Key", 1, len(doc), st.session_state.a_range)
    
    st.markdown("### 2. Build the Exam")
    if st.button("Scan PDF & Build Exam", type="primary
