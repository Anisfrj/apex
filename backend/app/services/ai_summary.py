"""Service IA — génère un résumé analyste via Groq LLM."""
import json
import re
from groq import AsyncGroq
from ..core.config import get_settings
from ..core.logging import get_logger

logger = get_logger("ai_summary")


async def generate_ai_summary(
    symbol: str,
    company_name: str | None,
    roic: float | None,
    fcf: float | None,
    sector: str | None,
    revenue_growth: float | None = None,
) -> dict:
    settings = get_settings()

    if not settings.groq_api_key:
        logger.warning("groq_api_key_missing")
        return _fallback_summary(symbol)

    client = AsyncGroq(api_key=settings.groq_api_key)

    roic_str = f"{roic:.1f}%" if roic is not None else "N/A"
    fcf_str = f"${fcf/1e9:.2f}B" if fcf and abs(fcf) >= 1e9 else (f"${fcf/1e6:.1f}M" if fcf else "N/A")
    growth_str = f"{revenue_growth*100:.1f}%" if revenue_growth else "N/A"

    prompt = f"""Tu es un analyste buy-side senior chez un hedge fund.
Analyse ces données financières pour {company_name or symbol} ({symbol}):
- Secteur: {sector or 'N/A'}
- ROIC: {roic_str}
- Free Cash Flow: {fcf_str}
- Croissance revenus: {growth_str}

Génère une analyse concise en JSON (réponse UNIQUEMENT en JSON, sans texte autour):
{{
  "moat": ["avantage 1 (max 12 mots)", "avantage 2", "avantage 3"],
  "risks": ["risque 1 (max 12 mots)", "risque 2"],
  "catalysts": ["catalyseur 1 (max 12 mots)", "catalyseur 2"]
}}

Règles: sois factuel, synthétique, évite les généralités. Base-toi sur les chiffres fournis."""

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        raw = response.choices[0].message.content.strip()
        # Extraire JSON même si le LLM ajoute du texte autour
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return _fallback_summary(symbol)
    except Exception as e:
        logger.error("ai_summary_failed", symbol=symbol, error=str(e))
        return _fallback_summary(symbol)


def _fallback_summary(symbol: str) -> dict:
    return {
        "moat": ["Données insuffisantes pour générer l'analyse", "Configurez GROQ_API_KEY dans .env", ""],
        "risks": ["Analyse IA non disponible", "Vérifiez les logs backend"],
        "catalysts": ["Sync les données via /api/trigger/sync-macro", "Puis relancez l'analyse"],
    }
