"""
Construit des requêtes de recherche intelligentes depuis un CV parsé.
"""

from typing import Dict, List, Set


class CVQueryBuilder:
    """
    Génère des mots-clés de recherche optimisés depuis un CV.
    
    Exemple : Si le CV mentionne "Cybersécurité, Python, Fortinet"
    → génère ["cybersécurité", "cybersecurity", "réseau", "network security"]
    """
    
    # Synonymes et traductions pour élargir la recherche
    SYNONYMS = {
        'cybersécurité': ['cybersecurity', 'sécurité informatique', 'infosec'],
        'réseau': ['network', 'réseaux', 'networking'],
        'développeur': ['developer', 'dev', 'ingénieur logiciel'],
        'data': ['data scientist', 'data analyst', 'data engineer'],
        'devops': ['devops', 'sre', 'infrastructure'],
        'cloud': ['aws', 'azure', 'gcp', 'cloud computing'],
    }
    
    def __init__(self, cv_data: Dict):
        """
        Initialise avec les données du CV parsé.
        
        Args:
            cv_data: Sortie de parse_cv() (dict avec name, skills, etc.)
        """
        self.cv_data = cv_data
    
    def build_queries(self, max_queries: int = 3) -> List[str]:
        """
        Construit une liste de requêtes de recherche.
        
        Stratégie :
        1. Utiliser le "title" du CV comme requête principale
        2. Combiner 2-3 compétences techniques clés
        3. Ajouter des synonymes/traductions
        
        Args:
            max_queries: Nombre max de requêtes à générer
            
        Returns:
            Liste de strings de recherche
            
        Example:
            >>> builder = CVQueryBuilder(cv_data)
            >>> queries = builder.build_queries()
            >>> print(queries)
            ['cybersécurité réseau', 'cybersecurity network', 'security engineer']
        """
        queries = []
        
        # 1. Titre du CV (souvent le meilleur indicateur)
        title = self.cv_data.get('title', '')
        if title and len(title) > 5:
            queries.append(self._clean_query(title))
        
        # 2. Compétences techniques principales (top 3)
        skills = self.cv_data.get('skills', {})
        technical_skills = skills.get('technical', [])[:3]
        
        if technical_skills:
            # Requête combinée : ex "Python Linux cybersécurité"
            combined = ' '.join(technical_skills)
            queries.append(self._clean_query(combined))
        
        # 3. Certifications → mots-clés (Fortinet → cybersecurity)
        certs = self.cv_data.get('certifications', [])
        if certs:
            cert_keywords = self._extract_keywords_from_certs(certs)
            if cert_keywords:
                queries.append(' '.join(cert_keywords[:2]))
        
        # 4. Traductions et synonymes
        queries_with_synonyms = []
        for query in queries:
            queries_with_synonyms.append(query)
            # Ajouter version anglaise si détectée française
            if any(fr in query.lower() for fr in ['cybersécurité', 'réseau', 'développeur']):
                en_query = self._translate_to_english(query)
                if en_query != query:
                    queries_with_synonyms.append(en_query)
        
        # Limiter au nombre max et enlever doublons
        unique_queries = list(dict.fromkeys(queries_with_synonyms))  # preserve order
        return unique_queries[:max_queries]
    
    def _clean_query(self, text: str) -> str:
        """Nettoie une requête (enlever ponctuation excessive, etc.)."""
        import re
        # Enlever ponctuation sauf espaces et tirets
        text = re.sub(r'[^\w\s\-]', ' ', text)
        # Réduire espaces multiples
        text = ' '.join(text.split())
        return text.strip().lower()
    
    def _extract_keywords_from_certs(self, certs: List[str]) -> List[str]:
        """
        Extrait des mots-clés depuis les certifications.
        
        Ex: "Fortinet Certified Fundamentals in Cybersecurity" → ["cybersecurity"]
        """
        keywords = set()
        
        # Mots-clés tech courants dans les certifications
        tech_terms = [
            'cybersecurity', 'cybersécurité', 'security', 'network', 'réseau',
            'cloud', 'aws', 'azure', 'cisco', 'fortinet', 'linux', 'windows'
        ]
        
        for cert in certs:
            cert_lower = cert.lower()
            for term in tech_terms:
                if term in cert_lower:
                    keywords.add(term)
        
        return list(keywords)
    
    def _translate_to_english(self, query: str) -> str:
        """Traduit mots-clés français → anglais (mapping simple)."""
        translations = {
            'cybersécurité': 'cybersecurity',
            'réseau': 'network',
            'réseaux': 'networks',
            'développeur': 'developer',
            'ingénieur': 'engineer',
            'sécurité': 'security'
        }
        
        result = query
        for fr, en in translations.items():
            result = result.replace(fr, en)
        
        return result
    
    def get_location_from_cv(self) -> str:
        """
        Déduit la localisation depuis le CV.
        
        Stratégie : regarder les expériences, ou utiliser "Tunisie" par défaut.
        """
        # Regarder les expériences
        experiences = self.cv_data.get('experiences', [])
        
        for exp in experiences:
            location = exp.get('location', '')
            if location and location.lower() not in ['null', 'n/a', '']:
                # Simplifier : "Tunis, Tunisie" → "Tunis"
                return location.split(',')[0].strip()
        
        # Fallback : regarder l'éducation
        education = self.cv_data.get('education', [])
        for edu in education:
            location = edu.get('location', '')
            if location and 'Tunisie' in location:
                return "Tunis"
        
        # Défaut
        return "Tunis"


if __name__ == "__main__":
    # Test rapide avec le CV de Salima
    cv_example = {
        "name": "Antoinne Szciir",
        "title": "Cybersécurité, administration réseau et virtualisation",
        "skills": {
            "technical": ["Python", "Java", "C", "Linux", "Windows Server"]
        },
        "certifications": [
            "Fortinet Certified Fundamentals in Cybersecurity"
        ]
    }
    
    builder = CVQueryBuilder(cv_example)
    queries = builder.build_queries()
    location = builder.get_location_from_cv()
    
    print("🔍 Requêtes générées :")
    for q in queries:
        print(f"  - '{q}'")
    print(f"\n📍 Localisation détectée : {location}")