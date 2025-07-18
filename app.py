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
    """
    modifications = 0
    original_content = xml_content
    
    # Méthode 1: Recherche avec expressions régulières pour gérer tous les cas
    # Pattern pour <Code>6A</Code> avec ou sans namespace
    code_patterns = [
        r'<Code>6A</Code>',  # Sans namespace
        r'<ns0:Code>6A</ns0:Code>',  # Avec ns0:
        r'<\w+:Code>6A</\w+:Code>',  # Avec n'importe quel namespace
        r'<Code\s*>6A</Code>',  # Avec espaces
        r'<Code>\s*6A\s*</Code>'  # Avec espaces autour de 6A
    ]
    
    for pattern in code_patterns:
        if re.search(pattern, xml_content):
            # Remplacer en gardant la structure des balises
            xml_content = re.sub(pattern, lambda m: m.group(0).replace('6A', ''), xml_content)
            modifications += len(re.findall(pattern, original_content))
    
    # Pattern pour <Description>Ouvriers</Description> avec ou sans namespace
    desc_patterns = [
        r'<Description>Ouvriers</Description>',  # Sans namespace
        r'<ns0:Description>Ouvriers</ns0:Description>',  # Avec ns0:
        r'<\w+:Description>Ouvriers</\w+:Description>',  # Avec n'importe quel namespace
        r'<Description\s*>Ouvriers</Description>',  # Avec espaces
        r'<Description>\s*Ouvriers\s*</Description>'  # Avec espaces autour
    ]
    
    for pattern in desc_patterns:
        if re.search(pattern, xml_content):
            # Remplacer en gardant la structure des balises
            xml_content = re.sub(pattern, lambda m: m.group(0).replace('Ouvriers', ''), xml_content)
            modifications += len(re.findall(pattern, original_content))
    
    return xml_content, modifications

def main():
    st.title("🧹 Nettoyage XML GERFLOR")
    st.markdown("**Suppression automatique des valeurs 6A et Ouvriers**")
    
    # Zone d'information
    with st.expander("ℹ️ Informations sur le traitement"):
        st.markdown("""
        Cette application traite vos fichiers XML en :
        - Supprimant la valeur "6A" dans toutes les balises `Code`
        - Supprimant la valeur "Ouvriers" dans toutes les balises `Description`
        - Fonctionne avec ou sans espaces de noms (ns0:, etc.)
        
        **Exemples de transformations :**
        ```xml
        <Code>6A</Code>                           →  <Code></Code>
        <ns0:Code>6A</ns0:Code>                   →  <ns0:Code></ns0:Code>
        <Description>Ouvriers</Description>       →  <Description></Description>
        <ns0:Description>Ouvriers</ns0:Description> →  <ns0:Description></ns0:Description>
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
            progress_bar = st.progress(0)
            for idx, uploaded_file in enumerate(uploaded_files):
                try:
                    # Lire le contenu
                    content = uploaded_file.read()
                    
                    # Essayer plusieurs encodages
                    xml_text = None
                    encoding_used = None
                    for encoding in ['utf-8', 'iso-8859-1', 'windows-1252', 'latin-1']:
                        try:
                            xml_text = content.decode(encoding)
                            encoding_used = encoding
                            break
                        except:
                            continue
                    
                    if xml_text is None:
                        st.error(f"❌ Impossible de décoder {uploaded_file.name}")
                        continue
                    
                    # Afficher l'encodage détecté
                    st.info(f"📝 Traitement de {uploaded_file.name} (encodage: {encoding_used})")
                    
                    # Nettoyer le XML
                    cleaned_xml, modifications = clean_xml_content(xml_text)
                    
                    # Ajouter aux résultats
                    results.append({
                        'name': uploaded_file.name,
                        'content': cleaned_xml,
                        'modifications': modifications,
                        'encoding': encoding_used
                    })
                    
                    total_modifications += modifications
                    
                    # Mettre à jour la barre de progression
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                    
                except Exception as e:
                    st.error(f"❌ Erreur avec {uploaded_file.name}: {str(e)}")
            
            # Effacer la barre de progression
            progress_bar.empty()
            
            # Afficher les résultats
            if results:
                st.header("📊 Résultats")
                
                # Statistiques
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Fichiers traités avec succès", len(results))
                with col2:
                    st.metric("Total des modifications", total_modifications)
                
                # Détails par fichier
                st.subheader("📋 Fichiers traités")
                
                for result in results:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            st.write(f"📄 **{result['name']}**")
                        
                        with col2:
                            if result['modifications'] > 0:
                                st.success(f"✅ {result['modifications']} modifications")
                            else:
                                st.warning(f"⚠️ Aucune modification")
                        
                        with col3:
                            # Bouton de téléchargement individuel
                            st.download_button(
                                label="⬇️ Télécharger",
                                data=result['content'],
                                file_name=result['name'].replace('.xml', '_cleaned.xml'),
                                mime="application/xml",
                                key=f"download_{result['name']}"
                            )
                
                # Afficher un aperçu pour vérification
                if st.checkbox("🔍 Voir un aperçu des modifications"):
                    for result in results:
                        if result['modifications'] > 0:
                            with st.expander(f"Aperçu de {result['name']}"):
                                # Chercher un exemple de modification
                                sample = result['content'][:2000]
                                
                                # Mettre en évidence les balises vides
                                highlighted = sample.replace('<Code></Code>', '**<Code></Code>**')
                                highlighted = highlighted.replace('<ns0:Code></ns0:Code>', '**<ns0:Code></ns0:Code>**')
                                highlighted = highlighted.replace('<Description></Description>', '**<Description></Description>**')
                                highlighted = highlighted.replace('<ns0:Description></ns0:Description>', '**<ns0:Description></ns0:Description>**')
                                
                                st.code(highlighted + "\n...", language="xml")
                                break
                
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
    st.caption("Supporte les fichiers avec ou sans espaces de noms (ns0:, etc.)")

if __name__ == "__main__":
    main()
