# Application Nettoyage XML GERFLOR

Application Streamlit pour nettoyer automatiquement les fichiers XML GERFLOR en vidant les valeurs des balises Code et Description.

## 🎯 Fonctionnalités

- **Upload multiple** de fichiers XML
- **Nettoyage automatique** des balises spécifiques
- **Téléchargement** des fichiers traités
- **Interface utilisateur** intuitive
- **Prévisualisation** des modifications

## 🔧 Balises traitées

L'application vide les valeurs des balises suivantes :
- `<Code>6A</Code>` → `<Code></Code>`
- `<Description>Ouvriers</Description>` → `<Description></Description>`

## 📁 Structure XML ciblée

```xml
<PositionStatus>
  <Code>6A</Code>
  <Description>Ouvriers</Description>
</PositionStatus>
```

## 🚀 Utilisation

1. Chargez vos fichiers XML
2. Cliquez sur "Traiter les fichiers"
3. Téléchargez les fichiers nettoyés

## 🏢 Client

Application développée pour **GERFLOR**

## 📊 Déploiement

Cette application est déployée via Streamlit Cloud connecté à GitHub.
