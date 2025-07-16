import streamlit as st
import xml.etree.ElementTree as ET
import io
import zipfile
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# Configuration de la page
st.set_page_config(
    page_title="Nettoyage XML GERFLOR", 
    page_icon="🧹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation des données de session
if 'processing_history' not in st.session_state:
    st.session_state.processing_history = []
if 'total_files_processed' not in st.session_state:
    st.session_state.total_files_processed = 0
if 'total_modifications' not in st.session_state:
    st.session_state.total_modifications = 0
if 'session_start_time' not in st.session_state:
    st.session_state.session_start_time = datetime.now()

def detect_xml_encoding(file_content):
    """Détecte l'encodage d'un fichier XML"""
    # Lire les premiers bytes pour chercher la déclaration XML
    header = file_content[:200]
    
    # Chercher la déclaration d'encodage dans l'en-tête XML
    try:
        header_str = header.decode('ascii', errors='ignore')
        if 'encoding=' in header_str:
            start = header_str.find('encoding=') + 10
            end = header_str.find('"', start)
            if end == -1:
                end = header_str.find("'", start)
            if end != -1:
                encoding = header_str[start:end]
                return encoding.lower()
    except:
        pass
    
    return None

def decode_xml_content(file_content):
    """Décode le contenu XML avec détection automatique d'encodage"""
    # Détecter l'encodage depuis la déclaration XML
    detected_encoding = detect_xml_encoding(file_content)
    
    # Liste des encodages à tester
    encodings = []
    if detected_encoding:
        encodings.append(detected_encoding)
    
    # Encodages courants à tester
    encodings.extend(['utf-8', 'iso-8859-1', 'windows-1252', 'cp1252', 'latin-1'])
    
    # Supprimer les doublons
    encodings = list(dict.fromkeys(encodings))
    
    for encoding in encodings:
        try:
            return file_content.decode(encoding), encoding
        except (UnicodeDecodeError, LookupError):
            continue
    
    return None, None

def clean_xml_content(xml_content):
    """
    Nettoie le contenu XML en vidant les valeurs des balises Code et Description
    dans les sections PositionStatus
    """
    try:
        start_time = time.time()
        
        # Parse le XML
        root = ET.fromstring(xml_content)
        
        # Compteur des modifications
        modifications = 0
        
        # Parcourir tous les éléments pour trouver les PositionStatus
        for position_status in root.iter('PositionStatus'):
            # Chercher les balises Code et Description dans ce PositionStatus
            code_elem = position_status.find('Code')
            description_elem = position_status.find('Description')
            
            # Vider la valeur de Code si elle contient "6A"
            if code_elem is not None and code_elem.text == "6A":
                code_elem.text = ""
                modifications += 1
            
            # Vider la valeur de Description si elle contient "Ouvriers"
            if description_elem is not None and description_elem.text == "Ouvriers":
                description_elem.text = ""
                modifications += 1
        
        # Convertir l'arbre modifié en string
        cleaned_xml = ET.tostring(root, encoding='unicode', method='xml')
        
        processing_time = time.time() - start_time
        
        return cleaned_xml, modifications, processing_time
        
    except ET.ParseError as e:
        st.error(f"Erreur de parsing XML: {e}")
        return None, 0, 0
    except Exception as e:
        st.error(f"Erreur inattendue: {e}")
        return None, 0, 0

def log_processing(filename, file_size, modifications, processing_time):
    """Enregistre les statistiques de traitement"""
    log_entry = {
        'timestamp': datetime.now(),
        'filename': filename,
        'file_size_kb': round(file_size / 1024, 2),
        'modifications': modifications,
        'processing_time_ms': round(processing_time * 1000, 2)
    }
    
    st.session_state.processing_history.append(log_entry)
    st.session_state.total_files_processed += 1
    st.session_state.total_modifications += modifications

def create_dashboard():
    """Crée le dashboard de monitoring"""
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
            delta=len([h for h in st.session_state.processing_history if h['timestamp'].date() == datetime.now().date()])
        )
    
    with col2:
        st.metric(
            "Total modifications",
            st.session_state.total_modifications,
            delta=sum([h['modifications'] for h in st.session_state.processing_history[-10:]])
        )
    
    with col3:
        avg_time = sum([h['processing_time_ms'] for h in st.session_state.processing_history]) / len(st.session_state.processing_history)
        st.metric(
            "Temps moyen (ms)",
            f"{avg_time:.2f}",
            delta=f"{st.session_state.processing_history[-1]['processing_time_ms']:.2f}" if st.session_state.processing_history else "0"
        )
    
    with col4:
        total_size = sum([h['file_size_kb'] for h in st.session_state.processing_history])
        st.metric(
            "Volume traité (KB)",
            f"{total_size:.2f}",
            delta=f"{st.session_state.processing_history[-1]['file_size_kb']:.2f}" if st.session_state.processing_history else "0"
        )
    
    # Graphiques
    df = pd.DataFrame(st.session_state.processing_history)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Modifications par fichier")
        fig_modifications = px.bar(
            df.tail(20), 
            x='filename', 
            y='modifications',
            title="Derniers 20 fichiers traités",
            color='modifications',
            color_continuous_scale='Viridis'
        )
        fig_modifications.update_xaxes(tickangle=45)
        st.plotly_chart(fig_modifications, use_container_width=True)
    
    with col2:
        st.subheader("⏱️ Temps de traitement")
        fig_time = px.line(
            df.tail(20), 
            x='timestamp', 
            y='processing_time_ms',
            title="Évolution du temps de traitement",
            markers=True
        )
        st.plotly_chart(fig_time, use_container_width=True)
    
    # Graphique en secteurs
    st.subheader("📊 Répartition des modifications")
    modification_counts = df['modifications'].value_counts().head(10)
    fig_pie = px.pie(
        values=modification_counts.values,
        names=modification_counts.index,
        title="Répartition du nombre de modifications par fichier"
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # Tableau des derniers traitements
    st.subheader("📋 Historique des traitements")
    df_display = df.tail(10)[['timestamp', 'filename', 'file_size_kb', 'modifications', 'processing_time_ms']]
    df_display['timestamp'] = df_display['timestamp'].dt.strftime('%H:%M:%S')
    df_display.columns = ['Heure', 'Fichier', 'Taille (KB)', 'Modifications', 'Temps (ms)']
    st.dataframe(df_display, use_container_width=True)
    
    # Bouton d'export des statistiques
    if st.button("📥 Exporter les statistiques"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="⬇️ Télécharger CSV",
            data=csv,
            file_name=f"gerflor_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

def main():
    st.title("🧹 Nettoyage XML GERFLOR")
    st.markdown("**Application pour vider les valeurs des balises Code et Description**")
    
    # Sidebar avec informations et statistiques en temps réel
    with st.sidebar:
        st.header("ℹ️ Informations")
        st.markdown("""
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
        """)
        
        st.markdown("---")
        st.header("📊 Statistiques de session")
        st.metric("Fichiers traités", st.session_state.total_files_processed)
        st.metric("Modifications totales", st.session_state.total_modifications)
        
        session_duration = datetime.now() - st.session_state.session_start_time
        st.metric("Durée de session", f"{session_duration.seconds//60}min {session_duration.seconds%60}s")
        
        if st.button("🔄 Réinitialiser statistiques"):
            st.session_state.processing_history = []
            st.session_state.total_files_processed = 0
            st.session_state.total_modifications = 0
            st.session_state.session_start_time = datetime.now()
            st.rerun()
    
    # Tabs pour séparer les fonctionnalités
    tab1, tab2 = st.tabs(["🔧 Traitement", "📊 Monitoring"])
    
    with tab1:
        # Upload des fichiers
        st.header("📁 Charger vos fichiers XML")
        uploaded_files = st.file_uploader(
            "Sélectionnez vos fichiers XML",
            type=['xml'],
            accept_multiple_files=True,
            help="Vous pouvez sélectionner plusieurs fichiers XML à traiter"
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} fichier(s) chargé(s)")
            
            # Prévisualisation des fichiers
            with st.expander("👀 Prévisualisation des fichiers"):
                for file in uploaded_files:
                    st.write(f"📄 **{file.name}** - {file.size} bytes")
            
            # Bouton pour traiter les fichiers
            if st.button("🚀 Traiter les fichiers", type="primary"):
                # Conteneur pour les résultats
                results_container = st.container()
                
                # Préparer les fichiers traités
                processed_files = []
                total_modifications = 0
                
                # Barre de progression
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Traitement de {uploaded_file.name}...")
                    progress_bar.progress((i + 1) / len(uploaded_files))
                    
                    # Lire le contenu du fichier avec détection d'encodage
                    file_content = uploaded_file.read()
                    
                    # Décoder avec détection automatique d'encodage
                    xml_content, detected_encoding = decode_xml_content(file_content)
                    
                    if xml_content is None:
                        st.error(f"❌ Impossible de décoder le fichier {uploaded_file.name}. Encodage non supporté.")
                        continue
                    
                    # Afficher l'encodage détecté
                    st.info(f"📝 {uploaded_file.name} - Encodage détecté: {detected_encoding}")
                    
                    # Nettoyer le XML
                    cleaned_xml, modifications, processing_time = clean_xml_content(xml_content)
                    
                    if cleaned_xml:
                        # Enregistrer les statistiques
                        log_processing(uploaded_file.name, len(file_content), modifications, processing_time)
                        
                        # Préparer le nom du fichier nettoyé
                        original_name = uploaded_file.name
                        clean_name = original_name.replace('.xml', '_cleaned.xml')
                        
                        processed_files.append({
                            'original_name': original_name,
                            'clean_name': clean_name,
                            'content': cleaned_xml,
                            'modifications': modifications,
                            'processing_time': processing_time
                        })
                        
                        total_modifications += modifications
                
                status_text.text("✅ Traitement terminé !")
                progress_bar.progress(1.0)
                
                # Afficher les résultats
                with results_container:
                    st.header("📊 Résultats du traitement")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Fichiers traités", len(processed_files))
                    with col2:
                        st.metric("Total modifications", total_modifications)
                    with col3:
                        avg_time = sum([f['processing_time'] for f in processed_files]) / len(processed_files) if processed_files else 0
                        st.metric("Temps moyen", f"{avg_time*1000:.2f}ms")
                    with col4:
                        st.metric("Statut", "✅ Terminé" if processed_files else "❌ Erreur")
                    
                    # Tableau des résultats
                    if processed_files:
                        st.subheader("📋 Détail par fichier")
                        for file_info in processed_files:
                            with st.expander(f"📄 {file_info['original_name']} ({file_info['modifications']} modifications - {file_info['processing_time']*1000:.2f}ms)"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.download_button(
                                        label="⬇️ Télécharger le fichier nettoyé",
                                        data=file_info['content'],
                                        file_name=file_info['clean_name'],
                                        mime="application/xml"
                                    )
                                
                                with col2:
                                    if st.button(f"👀 Prévisualiser", key=f"preview_{file_info['original_name']}"):
                                        st.code(file_info['content'][:1000] + "..." if len(file_info['content']) > 1000 else file_info['content'], language="xml")
                        
                        # Téléchargement groupé si plusieurs fichiers
                        if len(processed_files) > 1:
                            st.subheader("📦 Téléchargement groupé")
                            
                            # Créer un ZIP avec tous les fichiers
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                for file_info in processed_files:
                                    zip_file.writestr(file_info['clean_name'], file_info['content'])
                            
                            zip_buffer.seek(0)
                            
                            st.download_button(
                                label="⬇️ Télécharger tous les fichiers (ZIP)",
                                data=zip_buffer.getvalue(),
                                file_name=f"gerflor_cleaned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                                mime="application/zip"
                            )
    
    with tab2:
        create_dashboard()
    
    # Footer
    st.markdown("---")
    st.markdown("**🏢 Application GERFLOR** - Nettoyage automatique des fichiers XML avec monitoring intégré")

if __name__ == "__main__":
    main()
