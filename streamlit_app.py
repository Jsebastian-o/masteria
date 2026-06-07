import json
import time
import requests
import streamlit as st

API_STREAM_URL = "http://localhost:8000/api/v1/estimate/stream"

st.title("Estimator")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_meta" not in st.session_state:
    st.session_state.last_meta = None

# Sidebar
with st.sidebar:
    st.header("Last call info")

    if st.session_state.last_meta:
        meta = st.session_state.last_meta
        st.subheader("Metrics")
        st.metric("Model", meta["model"])
        col1, col2 = st.columns(2)
        col1.metric("Input tokens", meta["input_tokens"])
        col2.metric("Output tokens", meta["output_tokens"])
        st.metric("Response time", f"{meta['response_time']:.2f} s")

        st.subheader("System prompt")
        st.text_area("", value=meta["system_prompt"], height=400, disabled=True, label_visibility="collapsed")
    else:
        st.info("Submit a translation to see call details here.")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Copy client translation"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    meta_out = {}

    def stream_gen():
        t0 = time.time()
        try:
            with requests.post(API_STREAM_URL, json={"translation": prompt}, stream=True) as res:
                res.raise_for_status()
                pending = ""
                for chunk in res.iter_content(chunk_size=None, decode_unicode=True):
                    pending += chunk
                    if "\x00" in pending:
                        text_part, meta_json = pending.split("\x00", 1)
                        if text_part:
                            yield text_part
                        meta_out.update(json.loads(meta_json))
                        meta_out["response_time"] = time.time() - t0
                        return
                    else:
                        yield pending
                        pending = ""
        except requests.exceptions.ConnectionError:
            yield "Error: could not connect to the API. Make sure the server is running."
        except Exception as e:
            yield f"Error: {e}"

    with st.chat_message("assistant"):
        full_response = st.write_stream(stream_gen())

    st.session_state.messages.append({"role": "assistant", "content": full_response})
    if meta_out:
        st.session_state.last_meta = meta_out
    st.rerun()
