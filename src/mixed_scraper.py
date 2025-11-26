"""
Unified Job Scraper - Combines Tunisia local sites + international job boards
Scrapes from:
  - Tunisia: Emploi.tn, Tanitjobs, Keejob (via Selenium)
  - International: LinkedIn, Indeed, ZipRecruiter (via JobSpy)
Outputs all results to a single JSON file with match scores.
"""

import json
import pandas as pd
from typing import Dict, List
from datetime import datetime
import time
import re

# Selenium imports
SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from bs4 import BeautifulSoup
    SELENIUM_AVAILABLE = True
except ImportError:
    print("⚠ Selenium not installed. Tunisia sites will be skipped.")

# JobSpy import
JOBSPY_AVAILABLE = False
try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    print("⚠ JobSpy not installed. International sites will be skipped.")


class UnifiedJobScraper:
    """
    Unified job scraper combining Tunisia sites + international job boards.
    """
    
    def __init__(self):
        """Initialize the unified scraper."""
        print("🔧 Initializing Unified Job Scraper...")
        
        global SELENIUM_AVAILABLE
        
        self.driver = None
        
        # Initialize Selenium if available
        if SELENIUM_AVAILABLE:
            try:
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                self.wait = WebDriverWait(self.driver, 10)
                print("✓ Selenium WebDriver initialized - Tunisia sites enabled")
            except Exception as e:
                print(f"⚠ Selenium init failed: {str(e)[:100]}")
                print("  Tunisia sites will be skipped")
                SELENIUM_AVAILABLE = False
        
        if JOBSPY_AVAILABLE:
            print("✓ JobSpy initialized - International sites enabled")
        
        if not SELENIUM_AVAILABLE and not JOBSPY_AVAILABLE:
            raise RuntimeError("Neither Selenium nor JobSpy available. Install at least one.")
    
    def load_cv_profile(self, cv_json_path: str) -> Dict:
        """Load the parsed CV JSON file."""
        try:
            with open(cv_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"CV file not found: {cv_json_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in CV file: {cv_json_path}")
    
    def extract_search_keywords(self, cv_data: Dict) -> Dict[str, any]:
        """Extract search keywords from CV profile."""
        keywords = {
            'title': cv_data.get('title', ''),
            'domains': [],
            'skills': [],
            'location': ''
        }
        
        if 'job_search_intent' in cv_data:
            intent = cv_data['job_search_intent']
            keywords['domains'] = intent.get('domains', [])
            keywords['location'] = intent.get('location_preference', '')
        
        if 'skills' in cv_data and 'technical' in cv_data['skills']:
            keywords['skills'] = cv_data['skills']['technical'][:10]
        
        return keywords
    
    def build_search_term(self, keywords: Dict) -> str:
        """Build search term from CV keywords."""
        if keywords['title'] and len(keywords['title'].split()) <= 4:
            return keywords['title']
        
        if keywords['domains'] and keywords['domains'][0]:
            domain = keywords['domains'][0]
            return domain.split()[0] if domain else "informatique"
        
        if keywords['skills']:
            return keywords['skills'][0]
        
        return "informatique"
    
    # ========================================================================
    # TUNISIA SITES SCRAPING (Selenium)
    # ========================================================================
    
    def scrape_emploi_tn(self, search_term: str, max_jobs: int = 30) -> List[Dict]:
        """Scrape jobs from Emploitunisie.com using Selenium."""
        if not SELENIUM_AVAILABLE or not self.driver:
            return []
        
        print(f"\n[Tunisia 1/3] Scraping Emploitunisie.com for '{search_term}'...")
        jobs = []
        
        try:
            url = f"https://www.emploitunisie.com/recherche-jobs-tunisie/{search_term.replace(' ', '%20')}"
            self.driver.get(url)
            time.sleep(4)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            job_cards = soup.find_all('h3')
            
            for card in job_cards[:max_jobs]:
                try:
                    job_container = card.find_parent(['article', 'div', 'section'])
                    if job_container:
                        job = self._parse_emploi_tn_job(job_container, card)
                        if job:
                            jobs.append(job)
                except:
                    continue
            
            print(f"      ✓ Found {len(jobs)} jobs from Emploitunisie.com")
        except Exception as e:
            print(f"      ⚠ Emploitunisie.com error: {str(e)[:100]}")
        
        return jobs
    
    def _parse_emploi_tn_job(self, card, title_elem=None) -> Dict:
        """Parse a single job card from Emploitunisie.com."""
        job = {
            'title': '',
            'company': '',
            'location': 'Tunisie',
            'description': '',
            'url': '',
            'site': 'Emploitunisie.com',
            'date_posted': '',
            'scraped_at': datetime.now().isoformat()
        }
        
        if title_elem:
            title_link = title_elem.find('a', href=True)
            if title_link:
                job['title'] = title_link.get_text(strip=True)
                job['url'] = title_link['href']
                if not job['url'].startswith('http'):
                    job['url'] = 'https://www.emploitunisie.com' + job['url']
        
        company_elem = card.find('a', href=lambda x: x and '/recruteur/' in x if x else False)
        if company_elem:
            job['company'] = company_elem.get_text(strip=True)
        
        location_patterns = ['Tunis', 'Sfax', 'Sousse', 'Ariana', 'Nabeul', 'Monastir', 'Lac']
        text_content = card.get_text()
        for loc in location_patterns:
            if loc in text_content:
                job['location'] = loc
                break
        
        desc_elem = card.find('p')
        if desc_elem:
            job['description'] = desc_elem.get_text(strip=True)[:500]
        
        return job if job['title'] else None
    
    def scrape_tanitjobs(self, search_term: str, max_jobs: int = 30) -> List[Dict]:
        """Scrape jobs from Tanitjobs.com using Selenium."""
        if not SELENIUM_AVAILABLE or not self.driver:
            return []
        
        print(f"\n[Tunisia 2/3] Scraping Tanitjobs for '{search_term}'...")
        jobs = []
        
        try:
            url = f"https://www.tanitjobs.com/recherche/?q={search_term}"
            self.driver.get(url)
            time.sleep(3)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            job_cards = (
                soup.find_all('div', class_='job-item')[:max_jobs] or
                soup.find_all('div', class_='offer')[:max_jobs] or
                soup.find_all('article')[:max_jobs]
            )
            
            for card in job_cards:
                try:
                    job = self._parse_tanitjobs_job(card)
                    if job:
                        jobs.append(job)
                except:
                    continue
            
            print(f"      ✓ Found {len(jobs)} jobs from Tanitjobs")
        except Exception as e:
            print(f"      ⚠ Tanitjobs error: {str(e)[:100]}")
        
        return jobs
    
    def _parse_tanitjobs_job(self, card) -> Dict:
        """Parse a single job card from Tanitjobs."""
        job = {
            'title': '',
            'company': '',
            'location': 'Tunisie',
            'description': '',
            'url': '',
            'site': 'Tanitjobs',
            'date_posted': '',
            'scraped_at': datetime.now().isoformat()
        }
        
        title_elem = card.find(['h2', 'h3', 'h4', 'a'])
        if title_elem:
            job['title'] = title_elem.get_text(strip=True)
            if title_elem.name == 'a' and title_elem.get('href'):
                job['url'] = title_elem['href']
                if not job['url'].startswith('http'):
                    job['url'] = 'https://www.tanitjobs.com' + job['url']
        
        company_elem = card.find(['span', 'div'], text=re.compile('entreprise|société', re.I))
        if company_elem:
            job['company'] = company_elem.get_text(strip=True)
        
        location_elem = card.find(text=re.compile('tunis|sfax|sousse|nabeul', re.I))
        if location_elem:
            job['location'] = location_elem.strip()
        
        desc_elem = card.find('p')
        if desc_elem:
            job['description'] = desc_elem.get_text(strip=True)[:500]
        
        return job if job['title'] else None
    
    def scrape_keejob(self, search_term: str, max_jobs: int = 30) -> List[Dict]:
        """Scrape jobs from Keejob.com using Selenium."""
        if not SELENIUM_AVAILABLE or not self.driver:
            return []
        
        print(f"\n[Tunisia 3/3] Scraping Keejob for '{search_term}'...")
        jobs = []
        
        try:
            url = f"https://www.keejob.com/offres-emploi/?keywords={search_term.replace(' ', '+')}"
            self.driver.get(url)
            time.sleep(4)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            job_titles = soup.find_all('h2')
            
            for title_elem in job_titles[:max_jobs]:
                try:
                    job_container = title_elem.find_parent(['div', 'article', 'li'])
                    if job_container:
                        job = self._parse_keejob_job(job_container, title_elem)
                        if job:
                            jobs.append(job)
                except:
                    continue
            
            print(f"      ✓ Found {len(jobs)} jobs from Keejob")
        except Exception as e:
            print(f"      ⚠ Keejob error: {str(e)[:100]}")
        
        return jobs
    
    def _parse_keejob_job(self, card, title_elem=None) -> Dict:
        """Parse a single job card from Keejob."""
        job = {
            'title': '',
            'company': '',
            'location': 'Tunisie',
            'description': '',
            'url': '',
            'site': 'Keejob',
            'date_posted': '',
            'scraped_at': datetime.now().isoformat()
        }
        
        if title_elem:
            title_link = title_elem.find('a', href=True)
            if title_link:
                job['title'] = title_link.get_text(strip=True)
                job['url'] = title_link['href']
                if not job['url'].startswith('http'):
                    job['url'] = 'https://www.keejob.com' + job['url']
        
        company_elem = card.find('a', href=lambda x: x and '/companies/' in x if x else False)
        if company_elem:
            job['company'] = company_elem.get_text(strip=True)
        
        location_patterns = ['Tunis', 'Sfax', 'Sousse', 'Ariana', 'Nabeul', 'Monastir', 'Ben Arous']
        for text_elem in card.find_all(string=True):
            text = str(text_elem).strip()
            for loc in location_patterns:
                if loc in text:
                    job['location'] = loc
                    break
            if job['location'] != 'Tunisie':
                break
        
        desc_elem = card.find('p')
        if desc_elem:
            job['description'] = desc_elem.get_text(strip=True)[:500]
        
        return job if job['title'] else None
    
    # ========================================================================
    # INTERNATIONAL SITES SCRAPING (JobSpy)
    # ========================================================================
    
    def scrape_international_jobs(self, search_term: str, location: str = "", 
                                  results_wanted: int = 50, hours_old: int = 720) -> List[Dict]:
        """Scrape jobs from international sites using JobSpy."""
        if not JOBSPY_AVAILABLE:
            return []
        
        print(f"\n🌍 Scraping International Job Boards...")
        print(f"   Search: '{search_term}'")
        print(f"   Location: {location or 'Worldwide'}")
        
        all_jobs = []
        
        # LinkedIn
        print("\n[International 1/4] Scraping LinkedIn...")
        try:
            jobs = scrape_jobs(
                site_name=["linkedin"],
                search_term=search_term,
                location=location or "Tunisia",
                results_wanted=results_wanted,
                hours_old=hours_old,
                linkedin_fetch_description=True
            )
            if jobs is not None and not jobs.empty:
                all_jobs.extend(self._convert_jobspy_to_dict(jobs, 'LinkedIn'))
                print(f"      ✓ {len(jobs)} jobs from LinkedIn")
        except Exception as e:
            print(f"      ⚠ LinkedIn error: {str(e)[:100]}")
        
        # Indeed USA
        print("\n[International 2/4] Scraping Indeed USA...")
        try:
            jobs = scrape_jobs(
                site_name=["indeed"],
                search_term=f"{search_term} remote",
                location="",
                country_indeed="USA",
                results_wanted=results_wanted,
                hours_old=hours_old
            )
            if jobs is not None and not jobs.empty:
                all_jobs.extend(self._convert_jobspy_to_dict(jobs, 'Indeed USA'))
                print(f"      ✓ {len(jobs)} jobs from Indeed USA")
        except Exception as e:
            print(f"      ⚠ Indeed USA error: {str(e)[:100]}")
        
        # Indeed France
        print("\n[International 3/4] Scraping Indeed France...")
        try:
            jobs = scrape_jobs(
                site_name=["indeed"],
                search_term=search_term,
                location="",
                country_indeed="France",
                results_wanted=results_wanted // 2,
                hours_old=hours_old
            )
            if jobs is not None and not jobs.empty:
                all_jobs.extend(self._convert_jobspy_to_dict(jobs, 'Indeed France'))
                print(f"      ✓ {len(jobs)} jobs from Indeed France")
        except Exception as e:
            print(f"      ⚠ Indeed France error: {str(e)[:100]}")
        
        # ZipRecruiter
        print("\n[International 4/4] Scraping ZipRecruiter...")
        try:
            jobs = scrape_jobs(
                site_name=["zip_recruiter"],
                search_term=f"{search_term} remote",
                location="",
                results_wanted=results_wanted // 2,
                hours_old=hours_old
            )
            if jobs is not None and not jobs.empty:
                all_jobs.extend(self._convert_jobspy_to_dict(jobs, 'ZipRecruiter'))
                print(f"      ✓ {len(jobs)} jobs from ZipRecruiter")
        except Exception as e:
            print(f"      ⚠ ZipRecruiter error: {str(e)[:100]}")
        
        return all_jobs
    
    def _convert_jobspy_to_dict(self, jobs_df: pd.DataFrame, site: str) -> List[Dict]:
        """Convert JobSpy DataFrame to list of dictionaries."""
        jobs = []
        for _, job in jobs_df.iterrows():
            jobs.append({
                'title': job.get('title', 'N/A'),
                'company': job.get('company', 'N/A'),
                'location': job.get('location', 'N/A'),
                'description': str(job.get('description', ''))[:5000],
                'url': job.get('job_url', ''),
                'site': site,
                'date_posted': str(job.get('date_posted', '')),
                'is_remote': bool(job.get('is_remote', False)),
                'scraped_at': datetime.now().isoformat()
            })
        return jobs
    
    # ========================================================================
    # MATCHING AND SCORING
    # ========================================================================
    
    def calculate_match_score(self, job: Dict, cv_data: Dict) -> float:
        """Calculate match score between job and CV."""
        score = 0.0
        
        job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
        
        if job.get('title'):
            score += 10
        
        # Check domains (30 points)
        if 'job_search_intent' in cv_data and 'domains' in cv_data['job_search_intent']:
            domains = cv_data['job_search_intent']['domains']
            if domains:
                domain_keywords = []
                for domain in domains:
                    words = [w.lower() for w in domain.split() if len(w) > 4]
                    domain_keywords.extend(words)
                
                if domain_keywords:
                    matching = sum(1 for kw in domain_keywords if kw in job_text)
                    score += (matching / len(domain_keywords)) * 30
        
        # Check skills (35 points)
        if 'skills' in cv_data and 'technical' in cv_data['skills']:
            skills = cv_data['skills']['technical'][:20]
            if skills:
                matching_skills = 0
                for skill in skills:
                    skill_lower = skill.lower()
                    if skill_lower in job_text:
                        matching_skills += 1
                    else:
                        skill_words = skill_lower.split()
                        if any(word in job_text for word in skill_words if len(word) > 3):
                            matching_skills += 0.5
                
                score += (matching_skills / len(skills)) * 35
        
        # Location bonus (15 points)
        if 'tunis' in job.get('location', '').lower() or job.get('is_remote'):
            score += 15
        
        # Title match (10 points)
        cv_title = cv_data.get('title', '').lower()
        job_title = job.get('title', '').lower()
        if cv_title and job_title:
            title_words = [w for w in cv_title.split() if len(w) > 3]
            if title_words:
                matching = sum(1 for w in title_words if w in job_title)
                score += (matching / len(title_words)) * 10
        
        return min(score, 100.0)
    
    # ========================================================================
    # MAIN SCRAPING WORKFLOW
    # ========================================================================
    
    def scrape_and_match(self, cv_json_path: str, min_score: float = 15.0, 
                         max_results: int = 50, hours_old: int = 720) -> List[Dict]:
        """
        Main method: scrape from all sources and match with CV.
        
        Args:
            cv_json_path: Path to parsed CV JSON
            min_score: Minimum match score (0-100)
            max_results: Maximum jobs to return
            hours_old: Only jobs posted within X hours (for international sites)
        """
        print("=" * 70)
        print("UNIFIED JOB SCRAPER - Tunisia + International Sites")
        print("=" * 70)
        
        # Load CV
        print(f"\n📄 Loading CV profile from: {cv_json_path}")
        cv_data = self.load_cv_profile(cv_json_path)
        
        print(f"👤 Candidate: {cv_data.get('name', 'Unknown')}")
        print(f"💼 Profile: {cv_data.get('title', 'N/A')}")
        
        # Extract keywords
        print("\n🔑 Extracting search keywords...")
        keywords = self.extract_search_keywords(cv_data)
        print(f"   Domains: {', '.join(keywords['domains'][:3]) if keywords['domains'] else 'N/A'}")
        
        search_term = self.build_search_term(keywords)
        print(f"   🔍 Search term: '{search_term}'")
        
        # Scrape all sources
        all_jobs = []
        
        # 1. Tunisia sites (Selenium)
        if SELENIUM_AVAILABLE and self.driver:
            print("\n" + "="*70)
            print("🇹🇳 SCRAPING TUNISIA JOB SITES")
            print("="*70)
            try:
                all_jobs.extend(self.scrape_emploi_tn(search_term, 30))
                all_jobs.extend(self.scrape_tanitjobs(search_term, 30))
                all_jobs.extend(self.scrape_keejob(search_term, 30))
            except Exception as e:
                print(f"⚠ Tunisia scraping error: {str(e)[:100]}")
        
        # 2. International sites (JobSpy)
        if JOBSPY_AVAILABLE:
            print("\n" + "="*70)
            print("🌍 SCRAPING INTERNATIONAL JOB BOARDS")
            print("="*70)
            try:
                intl_jobs = self.scrape_international_jobs(
                    search_term=search_term,
                    location=keywords['location'] or "Tunisia",
                    results_wanted=50,
                    hours_old=hours_old
                )
                all_jobs.extend(intl_jobs)
            except Exception as e:
                print(f"⚠ International scraping error: {str(e)[:100]}")
        
        # Cleanup
        self.cleanup()
        
        if not all_jobs:
            print("\n⚠️  No jobs found from any source")
            return []
        
        print(f"\n{'='*70}")
        print(f"✅ TOTAL: {len(all_jobs)} jobs scraped from all sources")
        print(f"{'='*70}")
        
        # Calculate match scores
        print(f"\n📊 Calculating match scores...")
        matched_jobs = []
        
        for job in all_jobs:
            score = self.calculate_match_score(job, cv_data)
            
            if score >= min_score:
                job['match_score'] = round(score, 2)
                matched_jobs.append(job)
        
        # Sort by score
        matched_jobs.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Remove duplicates based on title+company
        seen = set()
        unique_jobs = []
        for job in matched_jobs:
            key = (
                    str(job.get('title', '')).lower(), 
                    str(job.get('company', '')).lower()
                )
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        
        print(f"   ✓ {len(unique_jobs)} unique matching jobs (removed {len(matched_jobs) - len(unique_jobs)} duplicates)")
        
        return unique_jobs[:max_results]
    
    def cleanup(self):
        """Close the Selenium WebDriver."""
        try:
            if self.driver:
                self.driver.quit()
                print("\n🔒 Browser closed")
        except:
            pass
    
    def save_results(self, jobs: List[Dict], output_path: str):
        """Save matched jobs to JSON file."""
        # Group jobs by source for summary
        sources = {}
        for job in jobs:
            site = job.get('site', 'Unknown')
            sources[site] = sources.get(site, 0) + 1
        
        output = {
            'search_date': datetime.now().isoformat(),
            'total_matches': len(jobs),
            'sources_summary': sources,
            'source_info': 'Tunisia: Emploi.tn, Tanitjobs, Keejob | International: LinkedIn, Indeed, ZipRecruiter',
            'jobs': jobs
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Results saved to: {output_path}")
        print(f"\n📊 Jobs by source:")
        for site, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            print(f"   {site}: {count} jobs")


def main():
    """Main function for command-line usage."""
    import sys
    
    if len(sys.argv) < 2:
        print("=" * 70)
        print("UNIFIED JOB SCRAPER - Tunisia + International Sites")
        print("=" * 70)
        print("\nUsage: python unified_job_scraper.py <cv_json_path> [output_path] [min_score] [hours_old]")
        print("\nExamples:")
        print("  python unified_job_scraper.py cv_parsed.json")
        print("  python unified_job_scraper.py cv_parsed.json all_jobs.json 20")
        print("  python unified_job_scraper.py cv_parsed.json jobs.json 15 2160")
        print("\nParameters:")
        print("  cv_json_path : Path to parsed CV JSON file (required)")
        print("  output_path  : Output JSON file (default: jobs.json)")
        print("  min_score    : Minimum match % (default: 15)")
        print("  hours_old    : Jobs posted within X hours for international sites (default: 720 = 1 month)")
        print("\nSources:")
        print("  Tunisia      : Emploi.tn, Tanitjobs, Keejob (Selenium)")
        print("  International: LinkedIn, Indeed, ZipRecruiter (JobSpy)")
        print("\nRequirements:")
        print("  pip install selenium beautifulsoup4 python-jobspy pandas")
        sys.exit(1)
    
    cv_json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "jobs.json"
    min_score = float(sys.argv[3]) if len(sys.argv) > 3 else 15.0
    hours_old = int(sys.argv[4]) if len(sys.argv) > 4 else 720
    
    scraper = None
    
    try:
        scraper = UnifiedJobScraper()
        
        matched_jobs = scraper.scrape_and_match(
            cv_json_path=cv_json_path,
            min_score=min_score,
            max_results=50,
            hours_old=hours_old
        )
        
        if matched_jobs:
            print(f"\n{'=' * 70}")
            print(f"✅ FINAL RESULTS: {len(matched_jobs)} matching jobs")
            print("=" * 70)
            
            # Show top 10
            for i, job in enumerate(matched_jobs[:10], 1):
                print(f"\n{i}. [{job['match_score']}%] {job['title']}")
                print(f"   🏢 {job['company']}")
                print(f"   📍 {job['location']}")
                print(f"   🌐 {job['site']}")
                if job.get('url'):
                    print(f"   🔗 {job['url'][:80]}...")
            
            if len(matched_jobs) > 10:
                print(f"\n... and {len(matched_jobs) - 10} more jobs")
            
            scraper.save_results(matched_jobs, output_path)
            
            print(f"\n{'=' * 70}")
            print("✅ Job search completed successfully!")
            print("=" * 70)
        else:
            print("\n⚠️  No matching jobs found.")
            print("Try:")
            print("  • Lowering min_score (e.g., 10)")
            print("  • Increasing hours_old (e.g., 2160 for 3 months)")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if scraper:
            scraper.cleanup()


if __name__ == "__main__":
    main()