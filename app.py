import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI
import json
import random 

# Setup OpenAI Client using your secret key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("⚖️ Custom 100-Question Bar Exam Builder")
st.write("Extract specific subjects, mix them up, and test yourself.")

uploaded_file = st.file_uploader("Upload your MBE PDF", type="pdf")

if uploaded_file:
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    st.write(f"**PDF loaded successfully!** Total pages: {len(doc)}")
    
    st.markdown("### 1. Locate the Subjects")
    st.write("Use the sliders to tell the AI exactly which pages contain the questions for each subject.")
    
    # Create 3 columns for the 3 subjects
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sub1_name = st.text_input("Subject 1", "Contracts")
        sub1_pages = st.slider(f"{sub1_name} Pages", 1, len(doc), (1, min(10, len(doc))), key="s1")
        sub1_count = st.number_input(f"{sub1_name} Q's", min_value=1, value=33, key="c1")
        
    with col2:
        sub2_name = st.text_input("Subject 2", "Criminal Law")
        sub2_pages = st.slider(f"{sub2_name} Pages", 1, len(doc), (11, min(20, len(doc))), key="s2")
        sub2_count = st.number_input(f"{sub2_name} Q's", min_value=1, value=33, key="c2")
        
    with col3:
        sub3_name = st.text_input("Subject 3", "Torts") 
        sub3_pages = st.slider(f"{sub3_name} Pages", 1, len(doc), (21, min(30, len(doc))), key="s3")
        sub3_count = st.number_input(f"{sub3_name} Q's", min_value=1, value=34, key="c3")
        
    st.markdown("### 2. Generate the Exam")
    if st.button("Extract and Shuffle 100 Questions"):
        st.warning("⏳ This is a massive request! It may take 1-2 minutes for the AI to read the pages and write 100 explanations. Please do not refresh the page.")
        
        all_questions = []
        
        # Function to handle the extraction for each subject
        def extract_questions(pages_tuple, count, subject):
            start, end = pages_tuple
            text = "".join([doc[i].get_text() for i in range(start - 1, end)])
            
            # --- UPDATED PROMPT TO CATCH THE FACT PATTERN ---
            prompt = f"""
            Scan the text and extract EXACTLY {count} multiple-choice questions related to {subject}.
            For each question, provide:
            - "fact_pattern": The complete scenario or story leading up to the question.
            - "question": The actual question stem (the final sentence being asked).
            - "options": List of exactly 4 strings for A, B, C, D
            - "correct_answer": The exact string of the correct option
            - "correct_explanation": A brief 1-sentence reason why it is correct
            - "wrong_explanations": A brief 1-sentence reason why the others are wrong
            
            Keep explanations concise. Return ONLY a JSON object with a key 'questions' containing the list.
            Text: {text}
            """
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            return json.loads(response.choices[0].message.content).get('questions', [])

        # Process Subject 1
        with st.spinner(f"Reading pages {sub1_pages[0]}-{sub1_pages[1]} for {sub1_name}..."):
            try:
                all_questions.extend(extract_questions(sub1_pages, sub1_count, sub1_name))
            except Exception as e:
                st.error(f"Error with {sub1_name}: {e}")
                
        # Process Subject 2
        with st.spinner(f"Reading pages {sub2_pages[0]}-{sub2_pages[1]} for {sub2_name}..."):
            try:
                all_questions.extend(extract_questions(sub2_pages, sub2_count, sub2_name))
            except Exception as e:
                st.error(f"Error with {sub2_name}: {e}")
                
        # Process Subject 3
        with st.spinner(f"Reading pages {sub3_pages[0]}-{sub3_pages[1]} for {sub3_name}..."):
            try:
                all_questions.extend(extract_questions(sub3_pages, sub3_count, sub3_name))
            except Exception as e:
                st.error(f"Error with {sub3_name}: {e}")
        
        # Shuffle and Display
        if all_questions:
            random.shuffle(all_questions) 
            st.success(f"✅ Successfully built an exam with {len(all_questions)} shuffled questions!")
            
            # --- UPDATED DISPLAY LOGIC ---
            for i, q in enumerate(all_questions):
                st.divider() # Adds a nice line between questions
                st.subheader(f"Question {i+1}")
                
                # Show the fact pattern first, in italics
                if q.get('fact_pattern'):
                    st.markdown(f"_{q.get('fact_pattern')}_")
                
                # Show the question stem in bold
                st.markdown(f"**{q.get('question')}**")
                
                user_choice = st.radio("Select an answer:", q.get('options', []), key=f"radio_{i}", label_visibility="collapsed")
                
                if st.button(f"Check Answer {i+1}", key=f"btn_{i}"):
                    if user_choice == q.get('correct_answer'):
                        st.success(f"✅ Correct! {q.get('correct_explanation')}")
                    else:
                        st.error(f"❌ Incorrect. {q.get('wrong_explanations')}")
