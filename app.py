import streamlit as st
import xml.etree.ElementTree as ET
import io
import zipfile
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import re
# chardet est optionnel : s'il n'est pas présent, on fonctionnera quand même.
try:
    import chardet  # détection heuristique d'encodage
except ModuleNotFoundError:
    chardet = None
    st.warning("Le module 'chardet' n'est pas installé ; détection d'encodage limitée aux prologues XML.")

# ------------------------------------------------------------
#  Helper : décodage robuste des fichiers XML
# ------------------------------------------------------------

def decode_xml(raw: bytes) -> str:
    """Décodage UTF‑8 → encodage déclaré → heuristique (si chardet dispo)."""
    # 1) UTF‑8 rapide
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass

    # 2) Encodage indiqué dans le prologue XML
    m = re.search(rb'encoding=["\'']([A-Za-z0-9._-]+)["\'']', raw[:200])
    if m:
        enc = m.group(1).decode(errors="ignore")
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass

    # 3) Heuristique via chardet (si dispo)
    if chardet:
        guess = chardet.detect(raw)["encoding"] or "utf-8"
        return raw.decode(guess, errors="replace")

    # 4) Fallback : remplace les caractères invalides
    return raw.decode("utf-8", errors="replace")

def decode_and_parse_xml(raw: bytes):
    """Retourne (root, cleaned_xml_str) ou lève une erreur ET.ParseError."""
    # Décodage + parsing en un seul endroit pour centraliser les erreurs
    xml_text = decode_xml(raw)
    root = ET.fromstring(xml_text)
    return root, xml_text
(raw: bytes) -> str:
    """Retourne le contenu texte d'un fichier XML en gérant l'encodage.

    1. Essaie UTF‑8 (chemin rapide).
    2. Si échec, lit l'encodage déclaré dans le prologue XML.
    3. Sinon, utilise chardet pour une détection heuristique.
    Toutes les erreurs résiduelles sont remplacées afin d'éviter
    toute levée d'UnicodeDecodeError.
    """
    # 1) UTF‑8
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass

    # 2) Encodage déclaré dans le prologue
    m = re.search(rb'encoding=["\']([A-Za-z0-9._-]+)["\']', raw[:200])
    if m:
        enc = m.group(1).decode()
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass

    # 3) Détection heuristique
    guess = chardet.detect(raw)["encoding"] or "utf-8"
    return raw.decode(guess, errors="replace")

# ------------------------------------------------------------
#  Configuration de la page Streamlit
# ------------------------------------------------------------

st.set_page_config(
    page_title="Nettoyage XML GERFLOR",
    page_icon="🧹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------
#  Initialisation des données de session
# ------------------------------------------------------------

if "processing_history" not in st.session_state:
    st.session_state.processing_history = []
if "total_files_processed" not in st.session_state:
    st.session_state.total_files_processed = 0
if "total_modifications" not in st.session_state:
    st.session_state.total_modifications = 0
if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = datetime.now()

# ------------------------------------------------------------
#  Fonctions métier
# ------------------------------------------------------------

def clean_xml_content(xml_content: str):
    """Nettoie le XML en vidant <Code>6A</Code> et <Description>Ouvriers</Description>."""
    try:
        start_time = time.time()

        root = ET.fromstring(xml_content)
        modifications = 0

        # Parcourir les PositionStatus
        for position_status in root.iter("PositionStatus"):
            code_elem = position_status.find("Code")
            description_elem = position_status.find("Description")

            if code_elem is not None and code_elem.text == "6A":
                code_elem.text = ""
                modifications += 1

            if description_elem is not None and description_elem.text == "Ouvriers":
                description_elem.text = ""
                modifications += 1

        cleaned_xml = ET.tostring(root, encoding="unicode", method="xml")
        processing_time = time.time() - start_time
        return cleaned_xml, modifications, processing_time

    except ET.ParseError as e:
        st.error(f"Erreur de parsing XML: {e}")
        return None, 0, 0
    except Exception as e:
        st.error(f"Erreur inattendue: {e}")
        return None, 0, 0

def log_processing(filename, file_size, modifications, processing_time):
    """Enregistre les statistiques de traitement dans la session."""
    log_entry = {
        "timestamp": datetime.now(),
        "filename": filename,
        "file_size_kb": round(file_size / 1024, 2),
        "modifications": modifications,
        "processing_time_ms": round(processing_time * 1000, 2),
    }

    st.session_state.processing_history.append(log_entry)
    st.session_state.total_files_processed += 1
    st.session_state.total_modifications += modifications

# ------------------------------------------------------------
#  Tableau de bord
# ------------------------------------------------------------

def create_dashboard():
    st.header("📊 Dashboard de Monitoring")

    if not st.session_state.processing_history:
        st.info("Aucune donnée de traitement disponible. Traitez des fichiers pour voir les statistiques.")
        return

    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Fichiers traités",
            st.session_state.total_files_processed,
            delta=len([h for h in st.session_state.processing_history if h["timestamp"].date() == datetime.now().date()]),
        )

    with col2:
        st.metric(
            "Total modifications",
            st.session_state.total_modifications,
            delta=sum([h["modifications"] for h in st.session_state.processing_history[-10:]]),
        )

    with col3:
        avg_time = sum([h["processing_time_ms"] for h in st.session_state.processing_history]) / len(
            st.session_state.processing_history
        )
        st.metric("Temps moyen (ms)", f"{avg_time:.2f}")

    with col4:
        total_size = sum([h["file_size_kb"] for h in st.session_state.processing_history])
        st.metric("Volume traité (KB)", f"{total_size:.2f}")

    # Graphiques
    df = pd.DataFrame(st.session_state.processing_history)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Modifications par fichier")
        fig_modifications = px.bar(
            df.tail(20),
            x="filename",
            y="modifications",
            title="Derniers 20 fichiers traités",
            color="modifications",
            color_continuous_scale="Viridis",
        )
        fig_modifications.update_xaxes(tickangle=45)
        st.plotly_chart(fig_modifications, use_container_width=True)

    with col2:
        st.subheader("⏱️ Temps de traitement")
        fig_time = px.line(
            df.tail(20),
            x="timestamp",
            y="processing_time_ms",
            title="Évolution du temps de traitement",
            markers=True,
        )
        st.plotly_chart(fig_time, use_container_width=True)

    st.subheader("📊 Répartition des modifications")
    modification_counts = df["modifications"].value_counts().head(10)
    fig_pie = px.pie(
        values=modification_counts.values,
        names=modification_counts.index,
        title="Répartition du nombre de modifications par fichier",
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("📋 Historique des traitements")
    df_display = df.tail(10)[
        ["timestamp", "filename", "file_size_kb", "modifications", "processing_time_ms"]
    ]
    df_display["timestamp"] = df_display["timestamp"].dt.strftime("%H:%M:%S")
    df_display.columns = ["Heure", "Fichier", "Taille (KB)", "Modifications", "Temps (ms)"]
    st.dataframe(df_display, use_container_width=True)

    if st.button("📥 Exporter les statistiques"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="⬇️ Télécharger CSV",
            data=csv,
            file_name=f"gerflor_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

# ------------------------------------------------------------
#  Interface principale
# ------------------------------------------------------------

def main():
    st.title("🧹 Nettoyage XML GERFLOR")
    st.markdown("**Application pour vider les valeurs des balises Code et Description**")

    # --- Sidebar ---
    with st.sidebar:
        st.header("ℹ️ Informations")
        st.markdown(
            """
        **Balises traitées :**
        - `<Code>6A</Code>` → `<Code></Code>`
        - `<Description>Ouvriers</Description>` → `<Description></Description>`

        **Structure ciblée :**
        ```xml
        <PositionStatus>
          <Code>6A</Code>
          <Description>Ouvriers</Description>
        </PositionStatus>
        ```
        """
        )

        st.markdown("---")
        st.header("📊 Statistiques de session")
        st.metric("Fichiers traités", st.session_state.total_files_processed)
        st.metric("Modifications totales", st.session_state.total_modifications)

        session_duration = datetime.now() - st.session_state.session_start_time
        st.metric("Durée de session", f"{session_duration.seconds // 60}min {session_duration.seconds % 60}s")

        if st.button("🔄 Réinitialiser statistiques"):
            st.session_state.processing_history = []
            st.session_state.total_files_processed = 0
            st.session_state.total_modifications = 0
            st.session_state.session_start_time = datetime.now()
            st.rerun()

    # --- Tabs ---
    tab1, tab2 = st.tabs(["🔧 Traitement", "📊 Monitoring"])

    # --------------------------------------------------------
    #  Tab 1 : Traitement des fichiers
    # --------------------------------------------------------

    with tab1:
        st.header("📁 Charger vos fichiers XML")
        uploaded_files = st.file_uploader(
            "Sélectionnez vos fichiers XML",
            type=["xml"],
            accept_multiple_files=True,
            help="Vous pouvez sélectionner plusieurs fichiers XML à traiter",
        )

        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} fichier(s) chargé(s)")

            with st.expander("👀 Prévisualisation des fichiers"):
                for file in uploaded_files:
                    st.write(f"📄 **{file.name}** - {file.size} bytes")

            if st.button("🚀 Traiter les fichiers", type="primary"):
                results_container = st.container()
                processed_files = []
                total_modifications = 0

                progress_bar = st.progress(0)
                status_text = st.empty()

                for i, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Traitement de {uploaded_file.name}...")
                    progress_bar.progress((i + 1) / len(uploaded_files))

                    file_content = uploaded_file.read()
                    xml_content = decode_xml(file_content)  # ✅ encodage robuste

                    cleaned_xml, modifications, processing_time = clean_xml_content(xml_content)

                    if cleaned_xml:
                        log_processing(uploaded_file.name, len(file_content), modifications, processing_time)

                        original_name = uploaded_file.name
                        clean_name = original_name.replace(".xml", "_cleaned.xml")

                        processed_files.append(
                            {
                                "original_name": original_name,
                                "clean_name": clean_name,
                                "content": cleaned_xml,
                                "modifications": modifications,
                                "processing_time": processing_time,
                            }
                        )

                        total_modifications += modifications

                status_text.text("✅ Traitement terminé !")
                progress_bar.progress(1.0)

                # ------------------------------------------------
                #  Affichage des résultats
                # ------------------------------------------------

                with results_container:
                    st.header("📊 Résultats du traitement")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Fichiers traités", len(processed_files))
                    with col2:
                        st.metric("Total modifications", total_modifications)
                    with col3:
                        avg_time = (
                            sum([f["processing_time"] for f in processed_files]) / len(processed_files)
                            if processed_files
                            else 0
                        )
                        st.metric("Temps moyen", f"{avg_time * 1000:.2f}ms")
                    with col4:
                        st.metric("Statut", "✅ Terminé" if processed_files else "❌ Erreur")

                    if processed_files:
                        st.subheader("📋 Détail par fichier")
                        for file_info in processed_files:
                            with st.expander(
                                f"📄 {file_info['original_name']} ({file_info['modifications']} modifications - {file_info['processing_time']*1000:.2f}ms)"
                            ):
                                col1, col2 = st.columns(2)

                                with col1:
                                    st.download_button(
                                        label="⬇️ Télécharger le fichier nettoyé",
                                        data=file_info["content"],
                                        file_name=file_info["clean_name"],
                                        mime="application/xml",
                                    )

                                with col2:
                                    if st.button(
                                        f"👀 Prévisualiser", key=f"preview_{file_info['original_name']}"
                                    ):
                                        preview = (
                                            file_info["content"][:1000] + "..."
                                            if len(file_info["content"]) > 1000
                                            else file_info["content"]
                                        )
                                        st.code(preview, language="xml")

                        # ---------------------------
                        #  Téléchargement groupé ZIP
                        # ---------------------------
                        if len(processed_files) > 1:
                            st.subheader("📦 Téléchargement groupé")
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                                for file_info in processed_files:
                                    zip_file.writestr(file_info["clean_name"], file_info["content"])

                            zip_buffer.seek(0)
                            st.download_button(
                                label="⬇️ Télécharger tous les fichiers (ZIP)",
                                data=zip_buffer.getvalue(),
                                file_name=f"gerflor_cleaned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                                mime="application/zip",
                            )

    # --------------------------------------------------------
    #  Tab 2 : Dashboard
    # --------------------------------------------------------

    with tab2:
        create_dashboard()

    st.markdown("---")
    st.markdown("**🏢 Application GERFLOR** - Nettoyage automatique des fichiers XML avec monitoring intégré")

# ------------------------------------------------------------

if __name__ == "__main__":
    main()
