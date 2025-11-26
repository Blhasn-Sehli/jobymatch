"""
Tests unitaires pour le module cv_parser.
"""

import pytest
import sys
from pathlib import Path

# Ajoute le dossier src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from cv_parser import (
    extract_email,
    extract_phone,
    extract_skills,
    parse_cv
)


def test_extract_email():
    """Teste l'extraction d'email depuis du texte."""
    text = "Contactez-moi à candidat@example.com pour plus d'infos"
    email = extract_email(text)
    assert email == "candidat@example.com"


def test_extract_phone():
    """Teste l'extraction de numéro de téléphone."""
    text = "Mon numéro : 06 12 34 56 78"
    phone = extract_phone(text)
    assert phone is not None
    assert "06" in phone


def test_extract_skills():
    """Teste l'extraction de compétences."""
    text = """
    COMPÉTENCES
    Python, Java, JavaScript
    SQL, MongoDB
    
    EXPÉRIENCE
    Développeur chez TechCorp
    """
    skills = extract_skills(text)
    assert len(skills) > 0
    assert any('python' in s.lower() for s in skills)


def test_parse_cv_returns_dict():
    """Vérifie que parse_cv retourne bien un dictionnaire avec les bonnes clés."""
    # Ce test nécessite un vrai PDF dans examples/
    # On le lance seulement si le fichier existe
    cv_path = Path(__file__).parent.parent / 'examples' / 'test_cv_simple.pdf'
    
    if cv_path.exists():
        result = parse_cv(str(cv_path))
        
        # Vérifie la structure
        assert isinstance(result, dict)
        assert 'name' in result
        assert 'email' in result
        assert 'phone' in result
        assert 'skills' in result
        assert 'experiences' in result
        
        # Vérifie les types
        assert isinstance(result['skills'], list)
        assert isinstance(result['experiences'], list)
    else:
        pytest.skip("Fichier test_cv_simple.pdf non trouvé")


