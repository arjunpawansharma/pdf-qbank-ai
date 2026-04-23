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
# --- NEW: Memory to track if the exam is finished ---
if "exam_submitted" not in st.session_state:
    st.session_state.exam_submitted = False

uploaded_file = st.file_uploader("Upload your MBE PDF", type="pdf")

if uploaded_file:
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    
    st.markdown("### Locate the Sections")
    st.info("MBE books separate questions and answers. Use the sliders to tell the AI where to look so it can use the official explanations.")
    
    col1, col2 = st.columns(2)
    with col1:
        q_start, q_end = st.slider("Pages with Questions", 1, len(doc), (1, min(30, len(doc))))
    with col2:
        a_start, a_end = st.slider("Pages with Answer Key", 1, len(doc), (min(31, len(doc)), min(60, len(doc))))
    
    if st.button("Scan PDF & Build Exam"):
        st.warning("⏳ Scanning questions and cross-referencing the answer key... This takes time. Please do not refresh!")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 1. Memorize the Answer Key
        status_text.text("📖 Memorizing the official Answer Key...")
        answer_key_text = "".join([doc[i].get_text() for i in range(a_start - 1, a_end)])
        
        all_questions = []
        chunk_size = 15 
        
        # 2. The Auto-Scanner Loop 
        for i in range(q_start - 1, q_end, chunk_size):
            chunk_end = min(i + chunk_size, q_end)
            status_text.text(f"Scanning Question pages {i + 1} to {chunk_end}...")
            
            question_text = "".join([doc[page_num].get_text() for page_num in range(i, chunk_end)])
            
            prompt = f"""
            You are an expert legal AI.
            
            Task 1: Scan the TEXT CHUNK below and extract ALL multiple-choice questions you can find.
            Task 2: For every question you extract, search the ANSWER KEY TEXT below to find the book's official explanation. 
            
            For each question, provide:
            - "subject": Categorize the question strictly as 'Contracts', 'Criminal Law', 'Torts', or 'Other'.
            - "fact_pattern": The complete scenario or story leading up to the question.
            - "question": The actual question stem (the final sentence being asked).
            - "options": List of exactly 4 strings for A, B, C, D
            - "correct_answer": The exact string of the correct option
            - "correct_explanation": The exact reason why it is correct, sourced STRICTLY from the ANSWER KEY TEXT.
            - "wrong_explanations": The exact reason why the others are wrong, sourced STRICTLY from the ANSWER KEY TEXT.
            
            Return ONLY a JSON object with a key 'questions' containing the list.
            
            TEXT CHUNK (Questions to extract): 
            {question_text}
            
            ANSWER KEY TEXT (Use this to find the exact explanations):
            {answer_key_text}
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
                st.error(f"Issue reading pages {i+1}-{chunk_end}: {e}")
            
            total_pages_to_scan = q_end - q_start + 1
            pages_scanned = chunk_end - q_start + 1
            progress_bar.progress(min(1.0, pages_scanned / total_pages_to_scan))
        
        status_text.text("✅ Scanning complete! Assembling your exam...")
        
        # 3. The Sorting Buckets
        contracts_qs = [q for q in all_questions if q.get('subject') == 'Contracts']
        crim_law_qs = [q for q in all_questions if q.get('subject') == 'Criminal Law']
        torts_qs = [q for q in all_questions if q.get('subject') == 'Torts']
        
        # 4. Sample and Assemble
        temp_exam = []
        temp_exam.extend(random.sample(contracts_qs, min(33, len(contracts_qs))))
        temp_exam.extend(random.sample(crim_law_qs, min(33, len(crim_law_qs))))
        temp_exam.extend(random.sample(torts_qs, min(34, len(torts_qs))))
        
        random.shuffle(temp_exam)
        
        # Save the finalized exam and RESET the submission status
        st.session_state.exam_questions = temp_exam
        st.session_state.exam_submitted = False
        st.rerun()

# --- Display logic outside the button block ---
if st.session_state.exam_questions:
    if not st.session_state.exam_submitted:
        st.success(f"🎉 Exam ready! You have {len(st.session_state.exam_questions)} questions to complete.")
    else:
        st.info("📊 Exam Submitted! Review your answers below.")
    
    for i, q in enumerate(st.session_state.exam_questions):
        st.divider()
        st.subheader(f"Question {i+1} ({q.get('subject')})") 
        
        if q.get('fact_pattern'):
            st.markdown(f"_{q.get('fact_pattern')}_")
        
        st.markdown(f"**{q.get('question')}**")
        
        # Disable the radio buttons if the exam is already submitted
        user_choice = st.radio(
            "Select an answer:", 
            q.get('options', []), 
            key=f"radio_{i}", 
            label_visibility="collapsed",
            disabled=st.session_state.exam_submitted
        )
        
        # --- NEW: Only show the feedback IF the exam is submitted ---
        if st.session_state.exam_submitted:
            if user_choice == q.get('correct_answer'):
                st.success(f"✅ Correct! {q.get('correct_explanation')}")
            else:
                st.error(f"❌ Incorrect. You chose: {user_choice}")
                st.success(f"✅ Correct Answer: {q.get('correct_answer')}")
                st.warning(f"**Explanation:** {q.get('wrong_explanations')}")

    # --- NEW: The Master Submit Button at the bottom ---
    st.divider()
    if not st.session_state.exam_submitted:
        # A large, primary-colored button to submit the whole test
        if st.button("Submit Exam & View Explanations", type="primary"):
            st.session_state.exam_submitted = True
            st.rerun()
    else:
        # Give them an option to clear their answers and try again
        if st.button("Retake This Exam"):
            st.session_state.exam_submitted = False
            st.rerun()
