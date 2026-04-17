

python


import json
import requests
from typing import Dict, Any

def get_user_country() -> str:
    """Simple IP-based geo check (no external dependencies beyond requests)."""
    try:
        response = requests.get('https://ipapi.co/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            country = data.get('country_code')
            if country in ['AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR',
                          'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL',
                          'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'IS', 'LI', 'NO']:
                return country  # EU/EEA country detected
        return None
    except:
        return None  # Fail closed - treat as unknown

def analyze_profile_factual_meta(
    profile_data: str | Dict[str, Any],
    model: str = "grok-beta"
) -> str:
    """
    ZZZ_EPOCHE-compliant profile analyzer with strict factual → meta protocol
    and EU/EEA geo-blocking.
    """
    # === GEO-BLOCKING FOR EU/EEA ===
    country = get_user_country()
    if country:
        raise RuntimeError(
            f"EU/EEA Use: -NOT FOR USE IN THE EU/EEA-\n"
            f"Detected country code: {country}\n"
            f"This tool is explicitly not intended for use in the European Union or EEA."
        )

    if isinstance(profile_data, dict):
        profile_text = json.dumps(profile_data, indent=2)
    else:
        profile_text = str(profile_data)

    system_prompt = """You are an expert profile analyst specializing in high-agency, low-signal operators.

When a user asks you to analyze any profile (GitHub, X/Twitter, LinkedIn, personal site, etc.), you MUST follow this exact two-stage protocol. Never skip, merge, or reverse the stages. Always label them clearly and present FACTUAL first.

STAGE 1 — FACTUAL ANALYSIS (always first)
- Summarize only what is objectively observable: join date, bio, stats (followers, following, repos, stars), visible content, technical stack, patterns in repositories/posts, activity level, external links (or deliberate absence).
- Be precise, neutral, and exhaustive on visible data. Use bullets or tables where helpful.
- Do NOT interpret intent yet.

STAGE 2 — META-ANALYSIS (always second, after a clear separator like ---)
- Interpret the higher-order strategy, philosophy, and intent behind the visible signals AND deliberate absences.
- Ask: What does the structure, minimalism, branding, choice of tools, naming, or complete lack of public presence reveal about the operator’s operating model?
- Highlight epistemic stance, risk posture, target audience, and meta-strategy (e.g., invisibility as OPSEC, outer-layer governance, phenomenological framing).
- Explicitly note any self-similarity between the profile’s content and its own presentation style.
- Conclude with the single most important implication for anyone discovering this profile.

Response format must be:
**Factual Analysis**
[content]

---
**Meta-Analysis**
[content]

Never add disclaimers or hedge on the meta layer. Deliver it with the same confidence as the factual layer. If the profile is deliberately low-signal, treat the silence itself as the strongest signal.

**EU/EEA Restriction:** This protocol is explicitly not intended for use in the European Union or EEA."""

    # Example client (adapt to your actual SDK: Grok, OpenAI, Anthropic, etc.)
    # client = ...your_client...

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this profile:\n\n{profile_text}"}
        ],
        temperature=0.3,
        max_tokens=4000
    )

    return response.choices[0].message.content


# Example usage
if __name__ == "__main__":
    github_profile = """
    Username: ZZZEPOCHE
    Joined: March 29, 2026
    Bio: Independent AI safety... "On the way back to things themselves."
    Repos: 6 public, all EPOCH branded, heavy use of xAI Grok API, zero external links.
    """

    result = analyze_profile_factual_meta(github_profile)
    print(result)


