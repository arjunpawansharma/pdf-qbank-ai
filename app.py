import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI
import json
import random 

# Setup OpenAI Client using your secret key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("⚖️ Autonomous Bar Exam Builder")
st.write("Upload your MBE PDF. The AI will scan the entire document, identify the subjects, and build your custom exam.")

uploaded_file = st.file_uploader("Upload your MBE PDF", type="pdf")

if uploaded_file:
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    st.write(f"**PDF loaded successfully!** Total pages: {len(doc)}")
    
    if st.button("Scan PDF & Build Exam"):
        st.warning("⏳ Scanning a large document takes time. The AI is reading the pages in chunks. This may take 2-3 minutes. Please do not refresh!")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_questions = []
        chunk_size = 15 # Reads 15 pages at a time to prevent AI limits
        
        # 1. The Auto-Scanner Loop
        for i in range(0, len(doc), chunk_size):
            start_page = i
            end_page = min(i + chunk_size, len(doc))
            status_text.text(f"Scanning pages {start_page + 1} to {end_page}...")
            
            text = "".join([doc[page_num].get_text() for page_num in range(start_page, end_page)])
            
            # --- UPDATED PROMPT: Notice the new "subject" instruction ---
            prompt = f"""
            Scan the text and extract ALL multiple-choice questions you can find.
            For each question, provide:
            - "subject": Categorize the question strictly as 'Contracts', 'Criminal Law', 'Torts', or 'Other'.
            - "fact_pattern": The complete scenario or story leading up to the question.
            - "question": The actual question stem (the final sentence being asked).
            - "options": List of exactly 4 strings for A, B, C, D
            - "correct_answer": The exact string of the correct option
            - "correct_explanation": A brief 1-sentence reason why it is correct
            - "wrong_explanations": A brief 1-sentence reason why the others are wrong
            
            Return ONLY a JSON object with a key 'questions' containing the list.
            Text: {text}
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
                st.error(f"Issue reading pages {start_page+1}-{end_page}: {e}")
            
            # Update the loading bar
            progress = min(1.0, (i + chunk_size) / len(doc))
            progress_bar.progress(progress)
        
        status_text.text("✅ Scanning complete! Assembling your exam...")
        
        # 2. The Sorting Buckets
        contracts_qs = [q for q in all_questions if q.get('subject') == 'Contracts']
        crim_law_qs = [q for q in all_questions if q.get('subject') == 'Criminal Law']
        torts_qs = [q for q in all_questions if q.get('subject') == 'Torts']
        
        st.write(f"**Found in PDF:** {len(contracts_qs)} Contracts | {len(crim_law_qs)} Crim Law | {len(torts_qs)} Torts")
        
        # 3. Sample and Assemble
        exam_questions = []
        # Safely grab the requested amounts (or maximum available if the PDF had fewer than 33)
        exam_questions.extend(random.sample(contracts_qs, min(33, len(contracts_qs))))
        exam_questions.extend(random.sample(crim_law_qs, min(33, len(crim_law_qs))))
        exam_questions.extend(random.sample(torts_qs, min(34, len(torts_qs))))
        
        random.shuffle(exam_questions)
        
        st.success(f"🎉 Exam ready! Generated {len(exam_questions)} randomized questions.")
        
        # --- DISPLAY LOGIC ---
        for i, q in enumerate(exam_questions):
            st.divider()
            # We now display the subject the AI identified next to the question number
            st.subheader(f"Question {i+1} ({q.get('subject')})") 
            
            if q.get('fact_pattern'):
                st.markdown(f"_{q.get('fact_pattern')}_")
            
            st.markdown(f"**{q.get('question')}**")
            
            user_choice = st.radio("Select an answer:", q.get('options', []), key=f"radio_{i}", label_visibility="collapsed")
            
            if st.button(f"Check Answer {i+1}", key=f"btn_{i}"):
                if user_choice == q.get('correct_answer'):
                    st.success(f"✅ Correct! {q.get('correct_explanation')}")
                else:
                    st.error(f"❌ Incorrect. {q.get('wrong_explanations')}")
