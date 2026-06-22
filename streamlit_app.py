import json

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="CAG Estimator", layout="wide")


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def _create_server_session() -> str:
    res = requests.post(f"{API_BASE}/api/v1/sessions", timeout=10)
    res.raise_for_status()
    return res.json()["session_id"]


def reset_state() -> None:
    st.session_state.session_id = _create_server_session()
    st.session_state.messages = []
    st.session_state.project_metadata = {}
    st.session_state.turn_count = 0


if "session_id" not in st.session_state:
    try:
        reset_state()
    except Exception as exc:
        st.error(f"No se pudo iniciar sesión con la API: {exc}")
        st.stop()


# ---------------------------------------------------------------------------
# Sidebar — session info + metadata panel
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("Sesión activa")
    st.caption(f"ID: `{st.session_state.session_id[:8]}…`")
    st.caption(f"Turnos en ventana: **{st.session_state.turn_count}**")

    if st.button("Nueva conversación", use_container_width=True):
        try:
            reset_state()
        except Exception as exc:
            st.error(f"Error al crear sesión: {exc}")
        st.rerun()

    st.divider()

    # --- Project metadata panel ---
    st.subheader("Project Metadata")
    meta: dict = st.session_state.project_metadata

    if meta:
        if meta.get("project_name"):
            st.metric("Proyecto", meta["project_name"])
        if meta.get("assumed_team_size"):
            st.metric("Tamaño de equipo", meta["assumed_team_size"])
        if meta.get("mentioned_technologies"):
            st.write("**Tecnologías detectadas**")
            st.write(" · ".join(meta["mentioned_technologies"]))
        if meta.get("agreed_scope"):
            st.write("**Alcance acordado**")
            st.write(meta["agreed_scope"])
    else:
        st.info("Sin metadatos aún. Envía la primera transcripción para que el modelo los extraiga.")

    with st.expander("JSON completo"):
        st.json(meta or {})


# ---------------------------------------------------------------------------
# Main area — chat history + input form
# ---------------------------------------------------------------------------

st.title("CAG Estimator")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

with st.form("estimate_form", clear_on_submit=True):
    transcript = st.text_area(
        "Transcripción de la reunión",
        placeholder="Pega aquí el texto de la reunión o call de requisitos…",
        height=220,
    )
    attachments = st.file_uploader(
        "Documentación adjunta (opcional)",
        accept_multiple_files=True,
        type=["pdf", "txt", "md", "png", "jpg", "jpeg", "webp"],
        help="PDFs, imágenes o documentos de texto complementarios.",
    )
    submitted = st.form_submit_button("Estimar", type="primary", use_container_width=True)

if submitted:
    if not transcript.strip():
        st.warning("La transcripción no puede estar vacía.")
    else:
        # Always send multipart so FastAPI receives both Form + File fields.
        # Encoding transcript as a nameless file part keeps the Content-Type
        # as multipart/form-data even when there are no actual attachments.
        multipart: list[tuple] = [("transcript", (None, transcript.encode(), "text/plain"))]
        for f in attachments or []:
            multipart.append(
                ("attachments", (f.name, f.getvalue(), f.type or "application/octet-stream"))
            )

        st.session_state.messages.append({"role": "user", "content": transcript})
        st.chat_message("user").markdown(transcript)

        extracted_meta: dict = {}

        def stream_gen():
            url = f"{API_BASE}/api/v1/sessions/{st.session_state.session_id}/estimate"
            try:
                with requests.post(url, files=multipart, stream=True, timeout=180) as res:
                    res.raise_for_status()
                    pending = ""
                    for chunk in res.iter_content(chunk_size=None, decode_unicode=True):
                        pending += chunk
                        if "\x00" in pending:
                            text_part, meta_json = pending.split("\x00", 1)
                            if text_part:
                                yield text_part
                            extracted_meta.update(json.loads(meta_json))
                            return
                        else:
                            yield pending
                            pending = ""
            except requests.exceptions.ConnectionError:
                yield "**Error:** no se pudo conectar con la API. Asegúrate de que el servidor está en marcha."
            except requests.exceptions.HTTPError as e:
                yield f"**Error {e.response.status_code}:** {e.response.text}"
            except Exception as e:
                yield f"**Error inesperado:** {e}"

        with st.chat_message("assistant"):
            full_response = st.write_stream(stream_gen())

        st.session_state.messages.append({"role": "assistant", "content": full_response})
        if extracted_meta:
            st.session_state.project_metadata = extracted_meta
        st.session_state.turn_count += 1
        st.rerun()
