import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI
import json

# Setup OpenAI Client using your secret key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("📚 AI QBank Generator")
st.write("Upload a PDF to generate MCQs with detailed explanations.")

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    # Extract Text from PDF
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    full_text = "".join([page.get_text() for page in doc])
    
    if st.button("Generate QBank"):
        with st.spinner("Analyzing text and creating rationales..."):
            # The Prompt - Instructions for the AI
            prompt = f"""
            Extract 3 Multiple Choice Questions from the following text. 
            For each question, provide:
            - The question
            - 4 options (A, B, C, D)
            - The correct answer
            - A detailed 'Why this is correct' explanation
            - A 'Why this is wrong' explanation for the other 3 options.
            Return ONLY a JSON list of objects.
            
            Text: {full_text[:4000]} 
            """

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            
            # Parse and Display
            qbank = json.loads(response.choices[0].message.content)
            
            for i, q in enumerate(qbank['questions']):
                st.subheader(f"Q{i+1}: {q['question']}")
                user_choice = st.radio(f"Select answer for Q{i+1}", q['options'], key=f"q{i}")
                
                if st.button(f"Check Answer {i+1}"):
                    if user_choice == q['correct_answer']:
                        st.success(f"✅ Correct! {q['correct_explanation']}")
                    else:
                        st.error(f"❌ Incorrect. {q['wrong_explanations']}")
