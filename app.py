import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI
import json
import random 

# Setup OpenAI Client using your secret key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="Autonomous Bar Exam Builder", page_icon="⚖️")

st.title("⚖️ Autonomous Bar Exam Builder")
st.write("Upload your MBE PDF. This version is optimized to avoid OpenAI Rate Limits.")

# --- Initialize Memory ---
if "exam_questions" not in st.session_state:
    st.session_state.exam_questions = None
if "exam_submitted" not in st.session_state:
    st.session_state.exam_submitted = False

uploaded_file = st.file_uploader("Upload your MBE PDF", type="pdf")

if uploaded_file:
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    st.write(f"**PDF loaded successfully!** Total pages: {len(doc)}")
    
    st.markdown("### 1. Identify Sections")
    col1, col2 = st.columns(2)
    with col1:
        q_start, q_end = st.slider("Question Pages", 1, len(doc), (1, 50))
    with col2:
        a_start, a_end = st.slider("Answer Key Pages", 1, len(doc), (150, 281))

    if st.button("Scan PDF & Build Exam", type="primary"):
        st.toast("🚀 Starting optimized scan...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # STEP 1: Extract Questions ONLY (Saves tokens)
        all_questions = []
        chunk_size = 8
        
        for i in range(q_start - 1, q_end, chunk_size):
            chunk_end = min(i + chunk_size, q_end)
            status_text.warning(f"🔍 Extracting questions from pages {i+1} to {chunk_end}...")
            
            text = "".join([doc[p].get_text() for p in range(i, chunk_end)])
            
            # Simple prompt to keep token count low
            prompt = f"Extract all multiple choice questions from this text. Return a JSON list of objects with 'subject' (Contracts, Torts, or Criminal Law), 'fact_pattern', 'question', 'options' (list of 4 strings), and 'id'. Text: {text}"
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini", # Using mini for extraction to save money/limits
                    messages=[{"role": "user", "content": prompt}],
                    response_format={ "type": "json_object" }
                )
                data = json.loads(response.choices[0].message.content)
                all_questions.extend(data.get('questions', []))
            except Exception as e:
                st.error(f"Error: {e}")
            
            progress_bar.progress(min(0.5, (chunk_end / q_end) / 2))

        # STEP 2: Match with Answer Key (Only for the found questions)
        if all_questions:
            status_text.info("📖 Matching official explanations from Answer Key...")
            answer_text = "".join([doc[p].get_text() for p in range(a_start-1, a_end)])
            
            # We process 5 questions at a time to stay under the 30k limit
            for idx in range(0, len(all_questions), 5):
                batch = all_questions[idx:idx+5]
                status_text.warning(f"🖋️ Writing explanations for questions {idx+1} to {idx+len(batch)}...")
                
                match_prompt = f"""
                Use the Answer Key below to find the correct answer and explanations for these specific questions.
                QUESTIONS: {json.dumps(batch)}
                ANSWER KEY: {answer_text[:15000]} # Limit key text to stay under rate limit
                
                Return JSON with 'updated_questions' list including 'correct_answer', 'correct_explanation', 'wrong_explanations'.
                """
                
                try:
                    res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": match_prompt}],
                        response_format={ "type": "json_object" }
                    )
                    updates = json.loads(res.choices[0].message.content).get('updated_questions', [])
                    for j, up in enumerate(updates):
                        if idx + j < len(all_questions):
                            all_questions[idx+j].update(up)
                except:
                    pass
                
                progress_bar.progress(0.5 + (min(0.5, (idx / len(all_questions)) / 2)))

        # Final Assembly
        random.shuffle(all_questions)
        st.session_state.exam_questions = all_questions[:100]
        st.session_state.exam_submitted = False
        st.rerun()

if st.session_state.exam_questions:
    st.success(f"🎉 Exam ready! {len(st.session_state.exam_questions)} questions loaded.")
    for i, q in enumerate(st.session_state.exam_questions):
        st.divider()
        st.subheader(f"Q{i+1}: {q.get('subject')}")
        st.write(q.get('fact_pattern', ''))
        st.bold(q.get('question', ''))
        choice = st.radio("Answer:", q.get('options', []), key=f"r_{i}", disabled=st.session_state.exam_submitted)
        
        if st.session_state.exam_submitted:
            if choice == q.get('correct_answer'):
                st.success(f"✅ Correct! {q.get('correct_explanation','')}")
            else:
                st.error(f"❌ Incorrect. Correct: {q.get('correct_answer')}")
                st.warning(f"Explanations: {q.get('wrong_explanations','')}")

    if not st.session_state.exam_submitted:
        if st.button("Submit Exam", type="primary"):
            st.session_state.exam_submitted = True
            st.rerun()
