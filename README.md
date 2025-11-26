# Job Match Backend

A CV parsing and job matching system powered by Ollama (local LLM) and web scraping capabilities.

## Features

- **CV Parsing**: Extract structured information from PDF resumes using Llama 3.2
- **Job Scraping**: Scrape job postings from various websites
- **Smart Matching**: Match CVs with job requirements
- **Local LLM**: Uses Ollama for privacy-focused, offline CV analysis

## Prerequisites

- Python 3.8 or higher
- Ollama (for local LLM processing)

## Installation

### 1. Install Ollama

#### Windows
1. Download Ollama from [https://ollama.ai/download](https://ollama.ai/download)
2. Run the installer
3. Verify installation by opening a terminal and running:
   ```bash
   ollama --version
   ```

#### macOS
```bash
brew install ollama
```

#### Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Pull the Llama 3.2 Model

After installing Ollama, pull the required model:

```bash
ollama pull llama3.2:3b
```

This will download the Llama 3.2 3B model (~2GB). Wait for the download to complete.

### 3. Start Ollama Service

Make sure Ollama is running:

```bash
ollama serve
```

**Note**: On Windows and macOS, Ollama typically runs automatically after installation. You can verify it's running by checking your system tray or running `ollama list`.

### 4. Clone the Repository

```bash
git clone https://github.com/MaherxBlhasn/job-match.git
cd job-match/backend
```

### 5. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 6. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Project Structure

```
backend/
├── src/
│   ├── __init__.py
│   ├── cv_parser_v2.py      # Main CV parser using Ollama
│   ├── cv_parser.py          # Legacy CV parser
│   ├── cv_query_builder.py  # Query builder for CV search
│   ├── job_scraper.py        # Tanit Jobs scraper with profile matching
│   └── matcher.py            # CV-Job matching logic
├── tests/
│   ├── __init__.py
│   └── test_cv_parser.py     # Unit tests
├── examples/
│   ├── cv1_parsed.json       # Sample parsed CV output
│   └── cv2_parsed.json       # Sample parsed CV output
├── requirements.txt
└── README.md
```

## Usage

### 1. Parsing a CV

#### Command Line
```bash
cd src
python cv_parser_v2.py ../examples/cv1.pdf
```

#### Python Code
```python
from src.cv_parser_v2 import parse_cv_with_ollama

# Parse a PDF CV
cv_data = parse_cv_with_ollama("path/to/cv.pdf")

# The output is a structured JSON with:
# - Personal information (name, email, phone, etc.)
# - Education history
# - Work experience
# - Skills
# - Languages
# - Certifications
print(cv_data)
```

### 2. Scraping Jobs from Tanit Jobs

Once you have a parsed CV, you can automatically scrape matching jobs from Tanit Jobs:

#### Command Line
```bash
cd src
python job_scraper.py ../examples/cv1_parsed.json
```

This will:
1. Load the CV profile
2. Extract relevant keywords (domains, skills, location preferences)
3. Search for jobs on Tanit Jobs website
4. Calculate match scores for each job (0-100%)
5. Save matched jobs to `matched_jobs.json`

#### Advanced Usage
```bash
# Specify output file and minimum match score
python job_scraper.py ../examples/cv1_parsed.json output.json 40

# Arguments:
# - cv1_parsed.json: Input CV file (from cv_parser_v2.py)
# - output.json: Output file for matched jobs (optional, default: matched_jobs.json)
# - 40: Minimum match score percentage (optional, default: 30)
```

#### Python Code
```python
from src.job_scraper import TanitJobsScraper

# Initialize scraper
scraper = TanitJobsScraper()

# Scrape and match jobs
matched_jobs = scraper.scrape_and_match(
    cv_json_path='../examples/cv1_parsed.json',
    min_score=30.0,  # Minimum match score (0-100)
    max_results=20   # Maximum jobs to return
)

# Display results
for job in matched_jobs:
    print(f"{job['title']} - Match: {job['match_score']}%")
    print(f"  Company: {job['company']}")
    print(f"  Location: {job['location']}")

# Save results
scraper.save_results(matched_jobs, 'matched_jobs.json')
```

### 3. Complete Workflow Example

```bash
# Step 1: Parse CV
cd src
python cv_parser_v2.py ../examples/cv1.pdf
# Output: cv1_parsed.json

# Step 2: Find matching jobs
python job_scraper.py ../examples/cv1_parsed.json matched_jobs.json 35
# Output: matched_jobs.json with jobs scored 35% or higher
```

### Example Output

See `examples/cv1_parsed.json` and `examples/cv2_parsed.json` for sample CV parsing outputs.

### Job Matching Algorithm

The scraper calculates match scores based on:
- **Domains** (30%): Cybersecurity, Networking, etc.
- **Technical Skills** (40%): Firewalls, VPN, Linux, etc.
- **Location Preference** (15%): Tunisia, France, etc.
- **Job Title Relevance** (15%): Keywords in job title

Jobs are ranked by match score and filtered by minimum threshold.

### Running Tests

```bash
pytest tests/
```

## Configuration

### Ollama Model Settings

The default model is `llama3.2:3b`. You can change this in the source code or use a different model:

```python
# In cv_parser_v2.py
response = ollama.chat(
    model='llama3.2:3b',  # Change model here
    messages=[...]
)
```

Available models (pull before use):
- `llama3.2:3b` (recommended, fast, lightweight)
- `llama3.2:7b` (better accuracy, slower)
- `llama3.2:70b` (best accuracy, requires powerful hardware)

## Troubleshooting

### Ollama Connection Error

If you get connection errors:

1. Verify Ollama is running:
   ```bash
   ollama list
   ```

2. Check if the model is downloaded:
   ```bash
   ollama list
   ```
   You should see `llama3.2:3b` in the list.

3. Try pulling the model again:
   ```bash
   ollama pull llama3.2:3b
   ```

### PDF Parsing Issues

If PDF text extraction fails:
- Ensure the PDF is text-based (not scanned images)
- Check file permissions
- Verify the PDF is not corrupted

### Tanit Jobs Scraping Issues

**Cloudflare Protection**: Tanit Jobs uses Cloudflare protection which may block automated scraping. If you encounter this:

1. **For Development/Testing**: The scraper includes error handling and will notify you when Cloudflare blocks the request

2. **For Production Use**, consider these solutions:
   - **Use Selenium/Playwright**: Automate a real browser to bypass protection
     ```bash
     pip install selenium playwright
     ```
   - **Use Tanit Jobs API**: Check if they offer an official API
   - **CAPTCHA Solving Services**: Integrate services like 2Captcha or Anti-Captcha
   - **Rotating Proxies**: Use proxy services to distribute requests

3. **Alternative Approach with Selenium**:
   ```python
   from selenium import webdriver
   from selenium.webdriver.chrome.options import Options
   
   options = Options()
   options.add_argument('--headless')
   driver = webdriver.Chrome(options=options)
   driver.get('https://www.tanitjobs.com')
   # ... scraping logic
   ```

### Memory Issues

If you encounter memory issues with the LLM:
- Use a smaller model (`llama3.2:3b` instead of larger versions)
- Close other applications
- Consider using the model with reduced context length

## Dependencies

Key dependencies:
- `ollama` - Local LLM interface
- `pdfminer.six` - PDF text extraction
- `beautifulsoup4` - Web scraping
- `selenium` - Dynamic website scraping
- `requests` - HTTP requests
- `pytest` - Testing framework

See `requirements.txt` for full list.

## Development

### Adding New Features

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Run tests:
   ```bash
   pytest tests/
   ```

4. Commit and push:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin feature/your-feature-name
   ```

## License

[Add your license here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on GitHub.
