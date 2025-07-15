import streamlit as st
import xml.etree.ElementTree as ET
import io
import zipfile
from datetime import datetime

def clean_xml_content(xml_content):
    """
    Nettoie le contenu XML en vidant les valeurs des balises Code et Description
    dans les sections PositionStatus
    """
    try:
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
        
        return cleaned_xml, modifications
        
    except ET.ParseError as e:
        st.error(f"Erreur de parsing XML: {e}")
        return None, 0
    except Exception as e:
        st.error(f"Erreur inattendue: {e}")
        return None, 0

def main():
    st.set_page_config(
        page_title="Nettoyage XML GERFLOR", 
        page_icon="🧹",
        layout="wide"
    )
    
    st.title("🧹 Nettoyage XML GERFLOR")
    st.markdown("**Application pour vider les valeurs des balises Code et Description**")
    
    # Sidebar avec informations
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
        
        # Bouton pour traiter les fichiers
        if st.button("🚀 Traiter les fichiers", type="primary"):
            # Conteneur pour les résultats
            results_container = st.container()
            
            # Préparer les fichiers traités
            processed_files = []
            total_modifications = 0
            
            with st.spinner("Traitement en cours..."):
                for uploaded_file in uploaded_files:
                    # Lire le contenu du fichier
                    xml_content = uploaded_file.read().decode('utf-8')
                    
                    # Nettoyer le XML
                    cleaned_xml, modifications = clean_xml_content(xml_content)
                    
                    if cleaned_xml:
                        # Préparer le nom du fichier nettoyé
                        original_name = uploaded_file.name
                        clean_name = original_name.replace('.xml', '_cleaned.xml')
                        
                        processed_files.append({
                            'original_name': original_name,
                            'clean_name': clean_name,
                            'content': cleaned_xml,
                            'modifications': modifications
                        })
                        
                        total_modifications += modifications
            
            # Afficher les résultats
            with results_container:
                st.header("📊 Résultats du traitement")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Fichiers traités", len(processed_files))
                with col2:
                    st.metric("Total modifications", total_modifications)
                with col3:
                    st.metric("Statut", "✅ Terminé" if processed_files else "❌ Erreur")
                
                # Tableau des résultats
                if processed_files:
                    st.subheader("📋 Détail par fichier")
                    for file_info in processed_files:
                        with st.expander(f"📄 {file_info['original_name']} ({file_info['modifications']} modifications)"):
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
    
    # Footer
    st.markdown("---")
    st.markdown("**🏢 Application GERFLOR** - Nettoyage automatique des fichiers XML")

if __name__ == "__main__":
    main()
