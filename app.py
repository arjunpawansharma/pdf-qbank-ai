import streamlit as st
import fitz  # PyMuPDF

st.title("📚 PDF to QBank Creator")

uploaded_file = st.file_uploader("Upload a PDF question bank", type="pdf")

if uploaded_file:
    # This reads the PDF
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    
    st.success("PDF Uploaded successfully!")
    
    if st.button("Generate Questions"):
        st.write("Sending text to AI... (Integration coming next!)")
        # In the next step, we will add the AI logic here.
