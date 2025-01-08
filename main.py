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
    for uploaded_file in uploaded_files:
        if uploaded_file is None:
            continue
        # Učitaj PDF fajl direktno iz Gradio fajl objekta
        loader = PyPDFLoader(uploaded_file.name)
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


def search_documents(query, db):
    retriever = db.as_retriever(
        search_type="similarity", search_kwargs={"k": 3})
    relevant_docs = retriever.invoke(query)
    context = "\n".join([doc.page_content for doc in relevant_docs])
    return context


def generate_response(context, user_input):
    query = f"{context}\n\nQuestion: {user_input}"
    response = llm.invoke([HumanMessage(content=query)])
    return response.content


def chatbot(input_text, db=None):
    if db is None:
        return "Nema dostupnih dokumenata za pretragu. Molimo učitajte PDF fajlove."

    context = search_documents(input_text, db)
    if not context:
        return "Nisam pronašao relevantne informacije u dokumentima."

    return generate_response(context, input_text)


# Gradio GUI sa unapređenim UI-jem
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 **PDF Chatbot Assistant**")
    gr.Markdown("""
    ### Dobrodošli u vaš personalizovani PDF Chatbot!
    - 📄 **Učitajte jedan ili više PDF dokumenata.**
    - ❓ **Postavite pitanja vezana za sadržaj dokumenata.**
    - 💬 **Dobijte pametne odgovore na osnovu sadržaja.**
    
    Napravljen sa ❤️ koristeći Gradio i LangChain.
    """)

    with gr.Row():
        uploaded_file = gr.File(
            label="📄 **Upload PDF Fajla**", file_types=[".pdf"], interactive=True)

    with gr.Row():
        query = gr.Textbox(label="❓ **Postavite pitanje**",
                           placeholder="Unesite vaše pitanje ovde...")
        output = gr.Textbox(label="💬 **Odgovor**")

    reset_btn = gr.Button("🔄 **Reset Chat**")

    # Event handlers
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
