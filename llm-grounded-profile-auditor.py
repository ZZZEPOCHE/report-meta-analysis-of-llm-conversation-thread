# llm-grounded-profile-auditor.py
# Outer-Layer Epistemic Auditor

import os
import re
import sys
import argparse
import platform
import requests
from pathlib import Path
from typing import Any

# Optional rich for nicer output
try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# SDK Imports
try:
    from google import genai
    from google.genai.types import Tool, UrlContext, GenerateContentConfig
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# GeoIP for EU/EEA blocking
try:
    import geoip2.database
    GEOIP_AVAILABLE = True
except ImportError:
    GEOIP_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

# ====================== EU/EEA ISO Codes ======================
EU_EEA_COUNTRIES = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR",
    "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI",
    "SK", "IS", "LI", "NO"
}

def get_public_ip() -> str | None:
    try:
        return requests.get("https://api.ipify.org", timeout=8).text.strip()
    except Exception:
        return None

def download_geolite2_db(db_path: Path):
    url = "https://git.io/GeoLite2-Country.mmdb"
    print("Downloading GeoLite2-Country database for EU/EEA geo-blocking...")
    try:
        r = requests.get(url, stream=True, timeout=40)
        r.raise_for_status()
        with open(db_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("✓ GeoIP database downloaded.")
    except Exception as e:
        print(f"Failed to download GeoIP DB: {e}")
        print("You can manually download from https://git.io/GeoLite2-Country.mmdb")
        return False
    return True

def check_eu_eea_block() -> bool:
    """Returns True if in EU/EEA. Soft warning on macOS 11 setups."""
    if not GEOIP_AVAILABLE:
        print("geoip2 not installed → skipping geo-block. (pip install geoip2)")
        return False

    db_path = Path.home() / ".cache" / "GeoLite2-Country.mmdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        if not download_geolite2_db(db_path):
            return False

    ip = get_public_ip()
    if not ip:
        print("Could not detect public IP → skipping geo-block.")
        return False

    try:
        with geoip2.database.Reader(str(db_path)) as reader:
            response = reader.country(ip)
            country = response.country.iso_code or ""
            if country in EU_EEA_COUNTRIES:
                print(f"\n⚠️  EU/EEA detected (country: {country}).")
                print("This tool includes EU/EEA geo-restriction due to regulatory considerations.")
                print("Continuing in limited mode. Use responsibly.\n")
                return True
    except Exception:
        pass  # silent fallback

    return False

def get_python_version() -> str:
    return platform.python_version()

def get_model_backend(model: str) -> str:
    model_lower = model.lower()
    if "gemini" in model_lower:
        return "gemini"
    elif "grok" in model_lower:
        return "grok"
    elif any(x in model_lower for x in ["gpt", "o1", "o3"]):
        return "openai"
    return "unknown"

# ====================== STRICT SYSTEM PROMPT ======================
STRICT_SYSTEM_PROMPT = (
    "You are a strict Fact-Focused Researcher in Outer-Layer Governance Mode. "
    "Invariant: Never hallucinate or synthesize personas, skills, backgrounds, expertise, or technical histories. "
    "Comply with epistemic honesty over plausibility. "
    "When a URL is provided, ground strictly on actual fetched content. "
    "Never use username/handle/etymology to infer anything. "
    "If the page is empty, 404, dormant, or non-technical: reply exactly with: "
    "'This appears to be a non-technical or empty profile. No professional background, skills, or public activity was found.' "
    "Always use the exact Forensic Profile Audit Report format. "
    "Prioritize minimalism and verifiable invariants."
)

def create_gemini_config(temperature: float = 0.1):
    """Correct 2026 configuration for URL Context tool."""
    tools = [Tool(url_context=UrlContext())]
    return GenerateContentConfig(
        tools=tools,
        temperature=temperature,
        max_output_tokens=2048,
        system_instruction=STRICT_SYSTEM_PROMPT
    )

def call_model(client: Any, backend: str, model: str, prompt: str, temperature: float = 0.1) -> str:
    try:
        if backend == "gemini":
            config = create_gemini_config(temperature)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )
            if hasattr(response, "text") and response.text:
                return response.text
            # Fallback for candidates
            if response.candidates:
                parts = []
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, "text") and part.text:
                                parts.append(part.text)
                return "".join(parts) or "No content returned from Gemini."
            return "No content returned from Gemini."

        elif backend in ("openai", "grok"):
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": STRICT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=2048
            )
            return response.choices[0].message.content or "No content returned."

        return "Unsupported model backend."

    except Exception as e:
        return f"Model call error: {str(e)}\n\nUnable to retrieve/verify content at this time."

# ====================== LEGAL DISCLOSURE ======================
FULL_LEGAL_DISCLOSURE = """
================================================================================
LEGAL DISCLOSURE, WAIVERS AND DISCLAIMERS

Independent open-source tool by ZZZ_EPOCHE. MIT License.
No affiliation with xAI, Google, OpenAI or any LLM provider.

Provided "AS IS" without warranty.
User is solely responsible for compliance with all laws (incl. EU AI Act, GDPR).

Use responsibly.
================================================================================
"""

def print_legal_summary():
    summary = (
        "=== Legal Notice ===\n"
        "Independent epistemic auditing tool (MIT License).\n"
        "AS IS — Use at your own risk.\n"
        "Run with --legal for full disclaimer.\n"
    )
    if console:
        console.print(summary, style="dim")
    else:
        print(summary)

def main():
    # EU/EEA geo-check (soft on macOS 11 setups)
    in_eu = check_eu_eea_block()

    parser = argparse.ArgumentParser(
        description="Outer-Layer Epistemic Profile Auditor (macOS 11 + Python 3)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--model", default="gemini-3-flash-preview",
                        help="Model: gemini-3-flash-preview, gpt-4o, grok-4, etc.")
    parser.add_argument("--temp", type=float, default=0.1, help="Temperature (default 0.1)")
    parser.add_argument("--legal", action="store_true", help="Show full legal disclosure and exit")
    parser.add_argument("--hard-block", action="store_true", help="Exit on EU/EEA detection instead of warning")
    args = parser.parse_args()

    if args.legal:
        if console:
            console.print(FULL_LEGAL_DISCLOSURE, style="dim")
        else:
            print(FULL_LEGAL_DISCLOSURE)
        sys.exit(0)

    print_legal_summary()

    print(f"Python version: {get_python_version()} | Platform: {platform.platform()}")
    print("macOS 11 compatible mode active\n")

    if in_eu and args.hard_block:
        print("Hard block enabled → exiting.")
        sys.exit(1)

    backend = get_model_backend(args.model)

    # Client setup (unchanged from your original, just cleaner)
    client = None
    if backend == "gemini":
        if not GEMINI_AVAILABLE:
            print("Error: google-genai not installed → pip install google-genai")
            sys.exit(1)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Error: GEMINI_API_KEY environment variable not set.")
            sys.exit(1)
        client = genai.Client(api_key=api_key)

    elif backend == "openai":
        if not OPENAI_AVAILABLE:
            print("Error: openai not installed → pip install openai")
            sys.exit(1)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY not set.")
            sys.exit(1)
        client = OpenAI(api_key=api_key)

    elif backend == "grok":
        if not OPENAI_AVAILABLE:
            print("Error: openai package required for Grok → pip install openai")
            sys.exit(1)
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            print("Error: XAI_API_KEY not set.")
            sys.exit(1)
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    else:
        print(f"Unsupported model: {args.model}")
        sys.exit(1)

    # Header
    if console:
        console.print(f"[bold cyan]=== Outer-Layer Epistemic Profile Auditor ===[/bold cyan]")
        console.print(f"Backend: [green]{backend.upper()}[/green] • Model: [yellow]{args.model}[/yellow]\n")
    else:
        print(f"=== Outer-Layer Epistemic Profile Auditor ===\nBackend: {backend.upper()} • Model: {args.model}\n")

    while True:
        try:
            user_input = input("Prompt (or 'quit'): ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Exiting.")
                break

            if re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', user_input):
                urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', user_input)
                msg = f"🔗 Detected {len(urls)} URL(s) → Enforcing strict epistemic grounding..."
                if console:
                    console.print(f"[yellow]{msg}[/yellow]")
                else:
                    print(msg)

            result = call_model(client, backend, args.model, user_input, args.temp)

            full_output = (
                "=" * 90 + "\n" +
                result + "\n\n" +
                "Tool provided under MIT License — AS IS, no warranty. Full legal: --legal\n" +
                "=" * 90
            )
            print(full_output)

        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()