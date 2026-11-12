import re
import requests
import spacy

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

MAX_SOURCES = 10
MAX_PAGE_TEXT = 20000
REQUEST_TIMEOUT = 8

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ProspectIQ/1.0)"
}


def normalize_name(name):
    """Normalize company names for deduplication."""

    name = (name or "").lower().strip()

    name = re.sub(
        r"\b(incorporated|inc|limited|ltd|llc|corp|corporation)\b",
        "",
        name
    )

    return re.sub(r"[^a-z0-9]", "", name)


def normalize_domain(url):
    """Extract a normalized domain from a URL."""

    if not url:
        return None

    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        domain = urlparse(url).netloc.lower()
        return domain.removeprefix("www.")

    except Exception:
        return None


def rank_sources(discovery_data):
    """Select relevant sources using Python."""

    campaign = discovery_data["campaign"]
    sources = discovery_data["sources"]

    campaign_text = " ".join([
        campaign.get("product", ""),
        campaign.get("target_industry", ""),
        campaign.get("target_location", ""),
        campaign.get("ideal_customer", "")
    ]).lower()

    keywords = {
        word
        for word in re.findall(r"\b[a-zA-Z0-9]+\b", campaign_text)
        if len(word) > 3
    }

    directory_words = [
        "companies", "startups", "directory",
        "database", "list", "saas"
    ]

    ranked = []

    for source in sources:

        title = source.get("title", "") or ""
        content = source.get("content", "") or ""

        combined_text = f"{title} {content}".lower()

        score = sum(
            1 for keyword in keywords
            if keyword in combined_text
        )

        if any(word in title.lower() for word in directory_words):
            score += 2

        if score > 0:
            ranked.append({
                "title": title,
                "url": source.get("url", ""),
                "content": content,
                "score": score
            })

    ranked.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return ranked[:MAX_SOURCES]



def fetch_page(url):
    """Fetch HTML and extract relevant main content and links."""

    if not url:
        return "", []

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        if "text/html" not in response.headers.get(
            "Content-Type", ""
        ).lower():
            return "", []

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove irrelevant elements.
        for element in soup([
            "script", "style", "noscript",
            "header", "footer", "nav",
            "aside", "form"
        ]):
            element.decompose()

        # Prefer the main article content.
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(attrs={"role": "main"})
            or soup.body
            or soup
        )

        # Extract readable text.
        page_text = main_content.get_text(
            separator=" ",
            strip=True
        )

        page_text = re.sub(r"\s+", " ", page_text)
        page_text = page_text[:8000]

        # Extract links from the main content only.
        links = []

        for anchor in main_content.find_all("a", href=True):

            link_text = anchor.get_text(" ", strip=True)
            href = urljoin(url, anchor["href"])

            if (
                link_text
                and href.startswith(("http://", "https://"))
            ):
                links.append({
                    "text": link_text,
                    "url": href
                })

        return page_text, links

    except requests.RequestException as error:

        print(f"Could not fetch page: {error}")

        return "", []




def extract_organizations(text):
    """Extract and clean organization names using spaCy."""

    if not text:
        return []

    doc = nlp(text)
    organizations = []
    seen = set()

    for entity in doc.ents:
        if entity.label_ != "ORG":
            continue

        name = " ".join(entity.text.strip().split())

        if len(name) < 3:
            continue

        name_key = normalize_name(name)

        if not name_key or name_key in seen:
            continue

        # Remove obvious non-company phrases.
        words_to_reject = {
            "privacy", "terms", "careers", "about us",
            "contact us", "read more", "view all",
            "united states", "ranking team", "dataset",
            "business management platform", "social platforms",
            "b2b sales marketing", "technology services"
        }

        if name.lower() in words_to_reject:
            continue

        # Reject names that are mostly generic words.
        generic_words = {
            "company", "companies", "services", "solutions",
            "platform", "software", "technology", "business",
            "market", "report", "ranking", "team", "group"
        }

        name_words = set(name.lower().split())

        if name_words.issubset(generic_words):
            continue

        seen.add(name_key)
        organizations.append(name)

    return organizations



def find_company_website(company_name, links):
    """Match company names with relevant external website links."""

    company_key = normalize_name(company_name)

    if not company_key:
        return None

    company_words = company_key.split()

    # Avoid matching generic, short organization names.
    generic_names = {
        "data", "api", "gpt", "ai", "tech",
        "software", "services", "solutions",
        "group", "company", "business", "cloud"
    }

    if company_key in generic_names:
        return None

    excluded_domains = {
        "linkedin.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "youtube.com",
        "wikipedia.org",
        "crunchbase.com",
        "wellfound.com",
        "glassdoor.com"
    }

    best_match = None
    best_score = 0

    for link in links:

        link_text = link.get("text", "").strip()
        link_url = link.get("url", "").strip()

        if not link_text or not link_url:
            continue

        domain = normalize_domain(link_url)

        if not domain:
            continue

        if any(
            domain == excluded or domain.endswith("." + excluded)
            for excluded in excluded_domains
        ):
            continue

        link_key = normalize_name(link_text)

        if not link_key:
            continue

        link_words = link_key.split()

        # Single-word names must match exactly.
        if len(company_words) == 1:

            if link_key == company_key:
                score = 100
            else:
                continue

        else:

            # Company name must appear as a complete sequence
            # of words, not merely as a substring.
            if (
                link_key == company_key
                or link_key.startswith(company_key + " ")
                or (" " + company_key + " ") in (" " + link_key + " ")
                or link_key.endswith(" " + company_key)
            ):
                score = 100
            else:
                continue

        if score > best_score:
            best_score = score
            best_match = link_url

    return best_match if best_score >= 100 else None



def is_likely_company(name):
    """Filter obvious non-company names."""

    name = name.strip()
    normalized = normalize_name(name)

    ignored_names = {
        "tracked", "unitedstates", "saas",
        "linkedin", "facebook", "instagram",
        "twitter", "youtube", "google",
        "readmore", "viewall", "privacy",
        "terms", "careers", "aboutus",
        "contactus", "learnmore", "getstarted",
        "company", "companies", "startups",
        "customers", "employees", "industries",
        "headquarters", "funding", "revenue",
        "overview", "solutions", "resources",
        "technology", "software", "enterprise"
    }

    if len(normalized) < 3:
        return False

    if normalized in ignored_names:
        return False

    if len(name.split()) > 5:
        return False

    if name.isdigit():
        return False

    return True




def extract_companies(discovery_data):

    sources = discovery_data["sources"]

    print(f"Total research sources: {len(sources)}")

    selected_sources = rank_sources(discovery_data)

    print(f"Selected sources: {len(selected_sources)}")

    if not selected_sources:
        return {
            "total_candidates": 0,
            "companies": [],
            "research_summary": "No relevant sources found.",
            "limitations": ["No sources matched campaign keywords."]
        }

    company_records = {}

    for index, source in enumerate(selected_sources, start=1):

        print(
            f"Processing source {index}/{len(selected_sources)}: "
            f"{source['title']}"
        )

        combined_text = (
            source.get("title", "") + " " +
            source.get("content", "")
        )

        page_text, links = fetch_page(source["url"])

        if page_text:
            combined_text += " " + page_text

        organizations = extract_organizations(combined_text)

        print(f"Organizations detected: {len(organizations)}")

        for name in organizations:

            if not is_likely_company(name):
                continue

            name_key = normalize_name(name)

            if not name_key:
                continue

            website = find_company_website(name, links)
            domain = normalize_domain(website)

            # Precision-first filtering:
            # Do not accept an organization without a website match.
            if not website or not domain:
                continue

            # Avoid treating the research directory itself as a company.
            source_domain = normalize_domain(source["url"])

            if source_domain and domain == source_domain:
                continue

            record_key = f"domain:{domain}"

            if record_key not in company_records:

                company_records[record_key] = {
                    "company_name": name,
                    "website": website,
                    "domain": domain,
                    "industry": None,
                    "location": None,
                    "employee_count": None,
                    "company_type": "unclear",
                    "evidence": (
                        f"Organization identified in {source['title']}. "
                        "Website link found on the source page. "
                        "Independent verification is still required."
                    ),
                    "buying_signal": None,
                    "fit_reason": (
                        "Potential company candidate based on campaign "
                        "research. Product fit has not been verified."
                    ),
                    "source_urls": [source["url"]],
                    "confidence": "Needs verification"
                }

            else:

                existing = company_records[record_key]

                if source["url"] not in existing["source_urls"]:
                    existing["source_urls"].append(source["url"])

    final_companies = list(company_records.values())

    print("\nEXTRACTION SUMMARY")
    print("------------------")
    print("Sources processed:", len(selected_sources))
    print("Unique candidates:", len(final_companies))

    return {
        "total_candidates": len(final_companies),
        "companies": final_companies,
        "research_summary": (
            f"Processed {len(selected_sources)} sources using "
            f"Python, Beautiful Soup and spaCy. "
            f"Identified {len(final_companies)} website-linked candidates."
        ),
        "limitations": [
            "spaCy may miss unfamiliar company names.",
            "Some organization names may still be false positives.",
            "Companies without matching website links are excluded.",
            "Some websites may block automated page fetching.",
            "Website links do not independently prove company identity.",
            "Employee counts and buying signals are not verified."
        ]
    }
