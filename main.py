import os
import gradio as gr
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from langchain.schema import HumanMessage

# Učitaj API ključ
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Funkcija za učitavanje više PDF dokumenata i pravljenje vektorske baze


def load_and_create_db(uploaded_files):
    docs = []
    for file_path in uploaded_files:
        if file_path is None:
            continue
        # Učitaj PDF fajl koristeći putanju
        loader = PyPDFLoader(file_path)
        docs.extend(loader.load())

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500, chunk_overlap=150)
    splits = text_splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings()
    db = Chroma.from_documents(splits, embeddings)

    return db


# Kreiraj LLM model
llm = ChatOpenAI(model_name="gpt-4", temperature=0)

# Funkcija za chat


def chatbot(input_text, chat_history=[], db=None):
    try:
        # Proveri da li je baza kreirana
        if db is None:
            return "Nema dostupnih dokumenata za pretragu. Molimo učitajte PDF fajlove."

        # Pretraži relevantne dokumente
        retriever = db.as_retriever(
            search_type="similarity", search_kwargs={"k": 3})
        relevant_docs = retriever.invoke(input_text)

        # Kreiraj kontekst iz dokumenata
        context = "\n".join([doc.page_content for doc in relevant_docs])

        # Kreiraj upit sa kontekstom
        query = f"{context}\n\nQuestion: {input_text}"

        # Generiši odgovor
        response = llm.invoke([HumanMessage(content=query)])

        # Vraćanje odgovora
        return response.content
    except Exception as e:
        return f"ERROR: {str(e)}"


# Gradio GUI sa personalizovanim UI-jem
with gr.Blocks() as demo:
    gr.Markdown("# 🤖 Personalized PDF Chatbot")
    gr.Markdown("""
    ### Dobrodošli u vaš PDF Chatbot!
    - Učitajte jedan PDF dokument.
    - Postavite pitanja vezana za sadržaj dokumenata.
    """)

    with gr.Row():
        uploaded_file = gr.File(label="📄 Upload PDF", file_types=[
                                ".pdf"], interactive=True)

    reset_btn = gr.Button("🔄 Reset Chat")

    query = gr.Textbox(label="Postavite pitanje")
    output = gr.Textbox(label="Odgovor")

    def reset_chat():
        return ""

    def process_query(file, user_input):
        if file is None:
            return "Molimo učitajte PDF fajl pre nego što postavite pitanje."

        # Prosledi putanju fajla direktno loader-u
        db = load_and_create_db([file])
        return chatbot(user_input, db=db)

    reset_btn.click(fn=reset_chat, inputs=[], outputs=[output])
    query.submit(fn=process_query, inputs=[
                 uploaded_file, query], outputs=[output])

# Pokreni Gradio aplikaciju bez public share-a
demo.launch()
