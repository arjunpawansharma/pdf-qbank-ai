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
    
    q_start = 1
    q_end = a_start - 1

    st.markdown("### 2. Build the Exam")
    if st.button("Scan PDF & Build Exam", type="primary"):
        st.warning("⏳ Deep scanning in progress. This may take a few minutes as we cross-reference multiple chapters. Please stay on this page.")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("📖 Memorizing all available Answer Keys...")
        answer_key_text = "".join([doc[i].get_text() for i in range(a_start - 1, a_end)])
        
        all_questions = []
        chunk_size = 3 
        
        for i in range(q_start - 1, q_end, chunk_size):
            chunk_end = min(i + chunk_size, q_end)
            status_text.text(f"Scanning pages {i + 1} to {chunk_end}...")
            
            question_text = "".join([doc[page_num].get_text() for page_num in range(i, chunk_end)])
            
            prompt = f"""
            You are a Bar Exam expert. Scan the text chunk and extract MCQs. 
            Cross-reference with the provided Answer Key text to find the OFFICIAL explanation.
            
            Return a JSON object with a 'questions' list. Each item must have:
            "subject", "fact_pattern", "question", "options", "correct_answer", "correct_explanation", "wrong_explanations".
            
            Questions chunk: {question_text}
            Answer Key reference: {answer_key_text}
            """
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={ "type": "json_object" }
                )
                extracted = json.loads(response.choices[0].message.content).get('questions', [])
                all_questions.extend(extracted)
            except Exception as e:
                st.error(f"Issue on pages {i+1}-{chunk_end}: {e}")
            
            total_pages = q_end - q_start + 1
            current_progress = (chunk_end - q_start + 1) / total_pages
            progress_bar.progress(min(1.0, current_progress))
        
        status_text.text("✅ All chapters scanned! Randomized 100-Q exam is ready.")
        
        contracts_qs = [q for q in all_questions if q.get('subject') == 'Contracts']
        crim_law_qs = [q for q in all_questions if q.get('subject') == 'Criminal Law']
        torts_qs = [q for q in all_questions if q.get('subject') == 'Torts']
        
        temp_exam = []
        temp_exam.extend(random.sample(contracts_qs, min(33, len(contracts_qs))))
        temp_exam.extend(random.sample(crim_law_qs, min(33, len(crim_law_qs))))
        temp_exam.extend(random.sample(torts_qs, min(34, len(torts_qs))))
        
        random.shuffle(temp_exam)
        st.session_state.exam_questions = temp_exam
        st.session_state.exam_submitted = False
        st.rerun()

if st.session_state.exam_questions:
    for i, q in enumerate(st.session_state.exam_questions):
        st.divider()
        st.subheader(f"Question {i+1} ({q.get('subject')})") 
        if q.get('fact_pattern'):
            st.markdown(f"_{q.get('fact_pattern')}_")
        st.markdown(f"**{q.get('question')}**")
        user_choice = st.radio("Select answer:", q.get('options', []), key=f"radio_{i}", label_visibility="collapsed", disabled=st.session_state.exam_submitted)
        
        if st.session_state.exam_submitted:
            if user_choice == q.get('correct_answer'):
                st.success(f"✅ Correct! {q.get('correct_explanation')}")
            else:
                st.error(f"❌ Incorrect. You chose: {user_choice}")
                st.success(f"✅ Correct Answer: {q.get('correct_answer')}")
                st.warning(f"**Official Explanation:** {q.get('wrong_explanations')}")

    st.divider()
    if not st.session_state.exam_submitted:
        if st.button("Submit Exam & View Explanations", type="primary"):
            st.session_state.exam_submitted = True
            st.rerun()
    else:
        if st.button("Retake This Exam"):
            st.session_state.exam_submitted = False
            st.rerun()
