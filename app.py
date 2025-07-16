import streamlit as st
import xml.etree.ElementTree as ET
import io
import zipfile
import re
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

# ------------------------------------------------------------
# Encodage heuristique ----------------------------------------
try:
    import chardet  # Pour détecter l'encodage si le prologue est absent
except ModuleNotFoundError:
    chardet = None
    st.warning("Le module 'chardet' n'est pas installé ; détection d'encodage limitée.")


def decode_xml(raw: bytes) -> str:
    """Décodage robuste pour XML : UTF‑8 → prologue → ISO‑8859‑1 → heuristique → remplacement"""
    # 1) UTF‑8 (chemin rapide)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass

    # 2) Encodage déclaré dans le prologue
    m = re.search(rb'encoding=["\\']([A-Za-z0-9._-]+)["\\']', raw[:200])
    if m:
        enc = m.group(1).decode("ascii", errors="ignore")
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            pass

    # 3) ISO‑8859‑1 : décode toujours les octets 0–255
    try:
        return raw.decode("iso-8859-1")
    except UnicodeDecodeError:
        pass  # pratiquement jamais atteint

    # 4) Heuristique chardet (si dispo)
    if chardet:
        enc_guess = chardet.detect(raw)["encoding"] or "utf-8"
        try:
            return raw.decode(enc_guess)
        except UnicodeDecodeError:
            pass

    # 5) Ultime recours : remplace les caractères invalides
    return raw.decode("utf-8", errors="replace")

# ------------------------------------------------------------
# Streamlit — configuration de la page -----------------------
st.set_page_config(
    page_title="Nettoyage XML GERFLOR",
    page_icon="🧹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# État de session --------------------------------------------
if "processing_history" not in st.session_state:
    st.session_state.processing_history = []
if "total_files_processed" not in st.session_state:
    st.session_state.total_files_processed = 0
if "total_modifications" not in st.session_state:
    st.session_state.total_modifications = 0
if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = datetime.now()

# ------------------------------------------------------------
# Fonctions métier -------------------------------------------

def clean_xml_content(xml_text: str):
    """Vide <Code>6A</Code> et <Description>Ouvriers</Description> dans chaque <PositionStatus>."""
    try:
        start = time.time()
        root = ET.fromstring(xml_text)
        mods = 0
        for ps in root.iter("PositionStatus"):
            code = ps.find("Code")
            desc = ps.find("Description")
            if code is not None and code.text == "6A":
                code.text = ""
                mods += 1
            if desc is not None and desc.text == "Ouvriers":
                desc.text = ""
                mods += 1
        return ET.tostring(root, encoding="unicode"), mods, time.time() - start
    except ET.ParseError as e:
        st.error(f"Erreur de parsing XML : {e}")
        return None, 0, 0


def log_processing(filename, size, mods, duration):
    st.session_state.processing_history.append({
        "timestamp": datetime.now(),
        "filename": filename,
        "file_size_kb": round(size / 1024, 2),
        "modifications": mods,
        "processing_time_ms": round(duration * 1000, 2),
    })
    st.session_state.total_files_processed += 1
    st.session_state.total_modifications += mods

# ------------------------------------------------------------
# Dashboard ---------------------------------------------------

def create_dashboard():
    st.header("📊 Dashboard de Monitoring")
    if not st.session_state.processing_history:
        st.info("Aucune donnée de traitement disponible.")
        return

    # Métriques
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Fichiers traités", st.session_state.total_files_processed)
    with col2:
        st.metric("Total modifications", st.session_state.total_modifications)
    with col3:
        avg = sum(h["processing_time_ms"] for h in st.session_state.processing_history) / len(st.session_state.processing_history)
        st.metric("Temps moyen (ms)", f"{avg:.2f}")
    with col4:
        total_size = sum(h["file_size_kb"] for h in st.session_state.processing_history)
        st.metric("Volume traité (KB)", f"{total_size:.2f}")

    df = pd.DataFrame(st.session_state.processing_history)

    st.subheader("⏱️ Temps de traitement (20 derniers)")
    st.plotly_chart(px.line(df.tail(20), x="timestamp", y="processing_time_ms", markers=True), use_container_width=True)

    st.subheader("📋 Historique (10 derniers)")
    st.dataframe(df.tail(10), use_container_width=True)

# ------------------------------------------------------------
# Application principale -------------------------------------

def main():
    st.title("🧹 Nettoyage XML GERFLOR")
    st.markdown("**Application pour vider les valeurs des balises Code et Description**")

    # ---- Sidebar ----
    with st.sidebar:
        st.header("ℹ️ Infos")
        st.markdown("""
        <Code>6A</Code> → vide
        <Description>Ouvriers</Description> → vide
        """)
        st.markdown("---")
        st.header("📊 Statistiques session")
        st.metric("Fichiers", st.session_state.total_files_processed)
        st.metric("Modifications", st.session_state.total_modifications)
        dur = datetime.now() - st.session_state.session_start_time
        st.metric("Durée", f"{dur.seconds//60}m {dur.seconds%60}s")
        if st.button("🔄 Réinitialiser stats"):
            st.session_state.processing_history = []
            st.session_state.total_files_processed = 0
            st.session_state.total_modifications = 0
            st.session_state.session_start_time = datetime.now()
            st.rerun()

    # ---- Tabs ----
    tab1, tab2 = st.tabs(["🔧 Traitement", "📊 Monitoring"])

    with tab1:
        st.header("📁 Charger vos fichiers XML (ISO‑8859‑1 ou UTF‑8)")
        files = st.file_uploader("Sélectionnez vos fichiers", type="xml", accept_multiple_files=True)
        if files and st.button("🚀 Traiter", type="primary"):
            progress = st.progress(0.0)
            result = []
            for i, f in enumerate(files):
                raw = f.read()
                xml_text = decode_xml(raw)
                cleaned, mods, dur = clean_xml_content(xml_text)
                if cleaned is None:
                    continue
                log_processing(f.name, len(raw), mods, dur)
                name_clean = f.name.replace(".xml", "_cleaned.xml")
                result.append((name_clean, cleaned, mods, dur))
                progress.progress((i + 1) / len(files))
            progress.progress(1.0)

            # Résultats
            st.success("Traitement terminé !")
            for name, content, mods, dur in result:
                with st.expander(f"{name} — {mods} modifs — {dur*1000:.0f} ms"):
                    st.download_button("⬇️ Télécharger", content, file_name=name, mime="application/xml")
                    st.code(content[:1000] + ("..." if len(content) > 1000 else ""), language="xml")
            if len(result) > 1:
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                    for name, content, *_ in result:
                        z.writestr(name, content)
                buf.seek(0)
                st.download_button("⬇️ Tout télécharger (ZIP)", buf.getvalue(), file_name="gerflor_cleaned.zip", mime="application/zip")

    with tab2:
        create_dashboard()

    st.markdown("---")
    st.markdown("**🏢 GERFLOR** — Nettoyage automatique des fichiers XML")


if __name__ == "__main__":
    main()
