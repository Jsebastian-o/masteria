import requests
import streamlit as st

API_URL = "http://localhost:8000/api/v1/estimate"

st.title("Estimator")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Copy client translation"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        res = requests.post(API_URL, json={"translation": prompt})
        res.raise_for_status()
        response = res.json()["estimation"]
    except requests.exceptions.ConnectionError:
        response = "Error: could not connect to the API. Make sure the server is running."
    except Exception as e:
        response = f"Error: {e}"
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})