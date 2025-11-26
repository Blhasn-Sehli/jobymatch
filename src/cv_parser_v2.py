"""
Module de parsing de CV avec Ollama (LLM local).
Version 2 : Extraction complète et fiable via Llama 3.2.
"""

import json
import ollama
from pdfminer.high_level import extract_text
from typing import Dict, Optional


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extrait le texte brut d'un fichier PDF.
    
    Args:
        pdf_path: Chemin vers le fichier PDF
        
    Returns:
        Texte extrait du PDF
    """
    try:
        text = extract_text(pdf_path)
        # Nettoyage basique
        text = text.replace('\x00', '')  # Enlève caractères null
        text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
        return text
    except FileNotFoundError:
        raise FileNotFoundError(f"Le fichier {pdf_path} n'existe pas")
    except Exception as e:
        raise Exception(f"Erreur lors de l'extraction du PDF : {str(e)}")


def create_extraction_prompt(cv_text: str) -> str:
    """
    Crée le prompt pour demander à Llama d'extraire les infos du CV.
    
    Version améliorée : gère les CVs avec formats variés.
    """
    prompt = f"""Tu es un expert en parsing de CV. Extrais TOUTES les informations du CV ci-dessous et retourne-les au format JSON UNIQUEMENT (pas de texte avant ou après le JSON).

IMPORTANT - DIFFÉRENCE ENTRE EXPÉRIENCES ET PROJETS :
- EXPÉRIENCES = emplois, stages, freelance, travail en entreprise (même sans nom d'entreprise explicite)
- PROJETS = projets académiques, personnels, hackathons, projets d'école

Structure JSON attendue :
{{
  "name": "Nom complet du candidat",
  "email": "adresse@email.com",
  "phone": "numéro de téléphone",
  "title": "Titre professionnel ou poste recherché",
  "summary": "Résumé/profil du candidat (section PROFIL ou RÉSUMÉ)",
  "education": [
    {{
      "degree": "Diplôme exact",
      "institution": "Nom complet de l'établissement",
      "location": "Ville, Pays si mentionné",
      "period": "Dates exactes (ex: 2023-2025)",
      "details": "Détails comme spécialisation, mention, co-diplomation"
    }}
  ],
  "job_search_intent": 
    {{
      "type": "Type recherché : stage/emploi/alternance/freelance",
      "level": "Niveau : stage d'été/stage PFE/junior/senior/temps partiel",
      "duration_min": "Durée minimale si mentionnée",
      "duration_max": "Durée maximale si mentionnée", 
      "domains": ["Domaines d'intérêt ou secteurs visés"],
      "availability": "Disponibilité : immédiate/à partir de DATE/recherche actuellement",
      "location_preference": "Préférences géographiques si mentionnées",
      "extracted_from": "Citation exacte du CV d'où tu as extrait cette info"
    }}
  ],
  "experiences": [
    {{
      "title": "Titre du poste ou description courte du rôle",
      "company": "Nom de l'entreprise (ou 'Non spécifié' si absent)",
      "location": "Lieu de l'entreprise (PAS l'adresse du candidat)",
      "period": "Dates ou durée exactes",
      "type": "Type de contrat : Stage/CDI/CDD/Temps partiel/Freelance/Projet de fin d'études",
      "description": "Description complète des missions et responsabilités",
      "technologies": ["tech1", "tech2"]
    }}
  ],
  "projects": [
    {{
      "name": "Nom du projet",
      "date": "Date ou période",
      "description": "Description détaillée du projet",
      "technologies": ["tech1", "tech2"],
      "context": "Contexte : hackathon/projet académique/projet personnel"
    }}
  ],
  "skills": {{
    "technical": ["Liste de compétences techniques, langages, frameworks"],
    "tools": ["Outils, logiciels, plateformes"],
    "other": ["Compétences transversales, soft skills"]
  }},
  "languages": [
    {{
      "language": "Nom de la langue",
      "level": "Niveau exact mentionné (Courant/Natif/B2/C1/Avancé/Intermédiaire)"
    }}
  ],
  "certifications": [
    "Nom complet de chaque certification avec organisme si mentionné"
  ],
  "associations": [
    {{
      "name": "Nom de l'association",
      "position": "Rôle/poste occupé",
      "period": "Période d'engagement"
    }}
  ]
}}

RÈGLES CRITIQUES D'EXTRACTION :

1. EXPÉRIENCES PROFESSIONNELLES :
   - Cherche les sections : "EXPÉRIENCE", "EXPERIENCE PROFESSIONNELLE", "PARCOURS"
   - Inclus TOUS les emplois, stages, missions, même courts
   - Si le CV dit "Temps partiel", "Stage", "Projet de fin d'études" → c'est une EXPÉRIENCE
   - Si pas de nom d'entreprise : mets "Non spécifié" dans company
   - Le "title" doit décrire le rôle (ex: "Développeur Backend", "Stagiaire Réseaux")
   - Extrais TOUTES les technologies mentionnées dans chaque expérience
   - Extrais une description pour chaque expérience (si possible)

2. PROJETS :
   - Cherche les sections : "PROJETS", "PROJETS ACADÉMIQUES", "RÉALISATIONS"
   - Ce sont des projets d'école, personnels, hackathons
   - NE PAS confondre avec les expériences professionnelles
   - Si un projet est fait POUR une entreprise (stage/emploi) → c'est une EXPÉRIENCE

3. LOCALISATION :
   - Pour "location" dans experiences : utilise UNIQUEMENT le lieu de l'entreprise/organisation
   - NE JAMAIS mettre l'adresse personnelle du candidat dans les expériences
   - Si le lieu n'est pas mentionné : mets null

4. COMPÉTENCES :
   - Regroupe intelligemment : langages de programmation, frameworks, outils
   - Garde les noms exacts (ex: "Next.js" pas "Nextjs")

5. IMPORTANT pour job_search_intent :
    - Cherche dans les sections PROFIL, RÉSUMÉ, OBJECTIF, en-tête du CV
    - Exemples de phrases à détecter :
    * "recherche un stage de fin d'études de 12 semaines minimum"
    * "cherche un stage d'été pour mettre à profit mes compétences"
    * "à la recherche d'un poste de développeur junior"
    * "disponible immédiatement pour un CDI"
    - Si rien n'est explicite, déduis depuis :
    * Formation en cours → probablement stage
    * Formation terminée + peu d'expérience → junior
    * Plusieurs années d'expérience → senior

EXEMPLES POUR T'AIDER :

Exemple 1 - Expérience avec entreprise :
Texte CV : "Stage en Cybersécurité | Openyx Tech, Tunisie | 5 semaines | 2024"
→ {{"title": "Stage en Cybersécurité", "company": "Openyx Tech", "location": "Tunisie", "period": "5 semaines | 2024", "type": "Stage"}}

Exemple 2 - Expérience sans entreprise :
Texte CV : "Maintenance plateforme cryptomonnaies | 10/2024-04/2025 | Temps partiel"
→ {{"title": "Développeur - Maintenance plateforme cryptomonnaies", "company": "Non spécifié", "location": null, "period": "10/2024-04/2025", "type": "Temps partiel"}}

Exemple 3 - Projet académique :
Texte CV : "Système RH basé sur IA - hackathon EY | 01/2025"
→ Dans "projects", PAS dans "experiences"

CV À ANALYSER :
{cv_text}

Retourne UNIQUEMENT le JSON, sans aucun texte explicatif avant ou après.
JSON:"""
    
    return prompt

def parse_cv_with_ollama(cv_text: str, model: str = "llama3.2:3b") -> Dict:
    """
    Parse le CV en utilisant Ollama (Llama 3.2).
    
    Args:
        cv_text: Texte extrait du CV
        model: Nom du modèle Ollama à utiliser
        
    Returns:
        Dictionnaire structuré avec toutes les infos du CV
    """
    try:
        # Crée le prompt
        prompt = create_extraction_prompt(cv_text)
        
        # Appelle Ollama
        print("🤖 Parsing du CV avec Llama 3.2...")
        response = ollama.chat(
            model=model,
            messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            options={
                'temperature': 0.2,  # Peu de créativité = plus précis
                'top_p': 0.9,
                'num_ctx': 4096
            }
        )
        
        # Extrait le contenu de la réponse
        content = response['message']['content']
        
        # Nettoie le JSON (enlève markdown si présent)
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        # Parse le JSON
        cv_data = json.loads(content)
        
        print("✅ Parsing terminé avec succès !")
        return cv_data
        
    except json.JSONDecodeError as e:
        print(f"❌ Erreur de parsing JSON : {e}")
        print(f"Réponse brute : {content[:500]}")
        raise Exception("Le modèle n'a pas retourné un JSON valide")
    except Exception as e:
        print(f"❌ Erreur lors du parsing : {str(e)}")
        raise


def parse_cv(pdf_path: str, model: str = "llama3.2:3b") -> Dict:
    """
    Fonction principale : Parse un CV PDF complet.
    
    Args:
        pdf_path: Chemin vers le fichier PDF du CV
        model: Modèle Ollama à utiliser (défaut: llama3.2:3b)
        
    Returns:
        Dictionnaire avec toutes les informations du CV
        
    Example:
        >>> cv_data = parse_cv("examples/SALIMA_ZRIBI_CV.pdf")
        >>> print(cv_data['name'])
        'SALIMA ZRIBI'
        >>> print(len(cv_data['experiences']))
        2
    """
    # 1. Extraction du texte
    print(f"📄 Extraction du texte de {pdf_path}...")
    cv_text = extract_text_from_pdf(pdf_path)
    # pour afficher le contenu du pdf
    # open("cv.txt", "w", encoding="utf-8").write(cv_text)

    
    if not cv_text or len(cv_text) < 100:
        raise Exception("Le CV extrait est trop court ou vide")
    
    print(f"✅ {len(cv_text)} caractères extraits")
    
    # 2. Parsing avec Ollama
    cv_data = parse_cv_with_ollama(cv_text, model)
    
    return cv_data


def display_cv_summary(cv_data: Dict):
    """
    Affiche un résumé formaté du CV parsé.
    """
    print("\n" + "="*60)
    print("📋 RÉSUMÉ DU CV PARSÉ")
    print("="*60)
    
    print(f"\n👤 NOM : {cv_data.get('name', 'N/A')}")
    print(f"📧 EMAIL : {cv_data.get('email', 'N/A')}")
    print(f"📞 TÉLÉPHONE : {cv_data.get('phone', 'N/A')}")
    print(f"💼 TITRE : {cv_data.get('title', 'N/A')}")
    
    if cv_data.get('summary'):
        print(f"\n📝 RÉSUMÉ : {cv_data['summary'][:150]}...")
    
    # Formation
    education = cv_data.get('education', [])
    print(f"\n🎓 FORMATION ({len(education)}) :")
    for edu in education[:3]:
        print(f"  • {edu.get('degree', 'N/A')} - {edu.get('institution', 'N/A')} ({edu.get('period', 'N/A')})")
    
    # Expériences
    experiences = cv_data.get('experiences', [])
    print(f"\n💼 EXPÉRIENCES ({len(experiences)}) :")
    for exp in experiences[:3]:
        print(f"  • {exp.get('title', 'N/A')} @ {exp.get('company', 'N/A')} ({exp.get('period', 'N/A')})")
    
    # Projets
    projects = cv_data.get('projects', [])
    print(f"\n🚀 PROJETS ({len(projects)}) :")
    for proj in projects[:3]:
        print(f"  • {proj.get('name', 'N/A')} ({proj.get('date', 'N/A')})")
    
    # Compétences
    skills = cv_data.get('skills', {})
    technical_skills = skills.get('technical', [])
    print(f"\n🛠️  COMPÉTENCES TECHNIQUES ({len(technical_skills)}) :")
    print(f"  {', '.join(technical_skills[:10])}")
    
    # Langues
    languages = cv_data.get('languages', [])
    print(f"\n🌍 LANGUES ({len(languages)}) :")
    for lang in languages:
        print(f"  • {lang.get('language', 'N/A')} : {lang.get('level', 'N/A')}")
    
    # Certifications
    certifications = cv_data.get('certifications', [])
    if certifications:
        print(f"\n🏆 CERTIFICATIONS ({len(certifications)}) :")
        for cert in certifications[:3]:
            print(f"  • {cert}")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python src/cv_parser_v2.py <chemin_vers_cv.pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    try:
        # Parse le CV
        cv_data = parse_cv(pdf_path)
        
        # Affiche le résumé
        display_cv_summary(cv_data)
        
        # Sauvegarde en JSON (optionnel)
        output_path = pdf_path.replace('.pdf', '_parsed.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cv_data, f, ensure_ascii=False, indent=2)
        print(f"💾 Résultat sauvegardé dans : {output_path}")
        
    except Exception as e:
        print(f"❌ ERREUR : {str(e)}")
        sys.exit(1)
