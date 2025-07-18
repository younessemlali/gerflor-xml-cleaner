import streamlit as st
import re
import io
import zipfile
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="Nettoyage XML GERFLOR", 
    page_icon="🧹",
    layout="wide"
)

def clean_xml_content(xml_content):
    """
    Nettoie le contenu XML en vidant les valeurs 6A et Ouvriers
    dans les balises Code et Description des blocs PositionStatus
    """
    modifications = 0
    
    # Pattern pour trouver et traiter les blocs PositionStatus
    # Ce pattern capture tout le bloc PositionStatus
    pattern = r'(<PositionStatus>.*?</PositionStatus>)'
    
    def process_block(match):
        nonlocal modifications
        block = match.group(1)
        original_block = block
        
        # Remplacer <Code>6A</Code> par <Code></Code>
        if '<Code>6A</Code>' in block:
            block = block.replace('<Code>6A</Code>', '<Code></Code>')
            modifications += 1
        
        # Remplacer <Description>Ouvriers</Description> par <Description></Description>
        if '<Description>Ouvriers</Description>' in block:
            block = block.replace('<Description>Ouvriers</Description>', '<Description></Description>')
            modifications += 1
        
        return block
    
    # Appliquer les modifications
    cleaned_xml = re.sub(pattern, process_block, xml_content, flags=re.DOTALL)
    
    return cleaned_xml, modifications

def main():
    st.title("🧹 Nettoyage XML GERFLOR")
    st.markdown("**Suppression automatique des valeurs 6A et Ouvriers**")
    
    # Zone d'information
    with st.expander("ℹ️ Informations sur le traitement"):
        st.markdown("""
        Cette application traite vos fichiers XML en :
        - Supprimant la valeur "6A" dans les balises `<Code>`
        - Supprimant la valeur "Ouvriers" dans les balises `<Description>`
        - Uniquement dans les blocs `<PositionStatus>`
        
        **Exemple de transformation :**
        ```xml
        <PositionStatus>
            <Code>6A</Code>              →    <Code></Code>
            <Description>Ouvriers</Description>    →    <Description></Description>
        </PositionStatus>
        ```
        """)
    
    # Upload des fichiers
    st.header("📁 Charger vos fichiers XML")
    uploaded_files = st.file_uploader(
        "Sélectionnez un ou plusieurs fichiers XML",
        type=['xml'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} fichier(s) chargé(s)")
        
        if st.button("🚀 Nettoyer les fichiers", type="primary", use_container_width=True):
            
            # Préparer les résultats
            results = []
            total_modifications = 0
            
            # Traiter chaque fichier
            for uploaded_file in uploaded_files:
                try:
                    # Lire le contenu
                    content = uploaded_file.read()
                    
                    # Essayer plusieurs encodages
                    xml_text = None
                    for encoding in ['utf-8', 'iso-8859-1', 'windows-1252', 'latin-1']:
                        try:
                            xml_text = content.decode(encoding)
                            break
                        except:
                            continue
                    
                    if xml_text is None:
                        st.error(f"❌ Impossible de décoder {uploaded_file.name}")
                        continue
                    
                    # Nettoyer le XML
                    cleaned_xml, modifications = clean_xml_content(xml_text)
                    
                    # Ajouter aux résultats
                    results.append({
                        'name': uploaded_file.name,
                        'content': cleaned_xml,
                        'modifications': modifications
                    })
                    
                    total_modifications += modifications
                    
                except Exception as e:
                    st.error(f"❌ Erreur avec {uploaded_file.name}: {str(e)}")
            
            # Afficher les résultats
            if results:
                st.header("📊 Résultats")
                
                # Statistiques
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Fichiers traités", len(results))
                with col2:
                    st.metric("Total modifications", total_modifications)
                
                # Détails par fichier
                st.subheader("📋 Fichiers traités")
                
                for result in results:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            st.write(f"📄 **{result['name']}**")
                        
                        with col2:
                            st.write(f"✏️ {result['modifications']} modifications")
                        
                        with col3:
                            # Bouton de téléchargement individuel
                            st.download_button(
                                label="⬇️ Télécharger",
                                data=result['content'],
                                file_name=result['name'].replace('.xml', '_cleaned.xml'),
                                mime="application/xml",
                                key=f"download_{result['name']}"
                            )
                
                # Téléchargement groupé si plusieurs fichiers
                if len(results) > 1:
                    st.markdown("---")
                    st.subheader("📦 Téléchargement groupé")
                    
                    # Créer un ZIP
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for result in results:
                            clean_name = result['name'].replace('.xml', '_cleaned.xml')
                            zip_file.writestr(clean_name, result['content'])
                    
                    zip_buffer.seek(0)
                    
                    st.download_button(
                        label="⬇️ Télécharger tous les fichiers (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name=f"gerflor_cleaned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
    
    else:
        st.info("👆 Veuillez charger un ou plusieurs fichiers XML à nettoyer")
    
    # Footer
    st.markdown("---")
    st.markdown("🏢 **GERFLOR** - Nettoyage automatique des fichiers XML")

if __name__ == "__main__":
    main()
