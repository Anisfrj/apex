"""Service Telegram Bot — Envoi des alertes structurées."""

import httpx
from ..core.config import get_settings
from ..core.logging import get_logger

logger = get_logger("telegram")

TELEGRAM_API = "https://api.telegram.org/bot"


async def send_telegram_message(text: str, parse_mode: str = "HTML") -> bool:
    """Envoie un message via Telegram Bot API."""
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("telegram_not_configured")
        return False

    url = f"{TELEGRAM_API}{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info("telegram_message_sent", length=len(text))
            return True
    except Exception as e:
        logger.error("telegram_send_error", error=str(e))
        return False


def format_equity_alert(
    company_name: str,
    symbol: str,
    insider_name: str,
    insider_title: str,
    amount: float,
    roic: float,
    fcf: float,
    sector: str,
    above_sma200: bool,
    macro_trend: str,
) -> str:
    """Formate une alerte Actions structurée pour Telegram."""
    sma_emoji = "🟢" if above_sma200 else "🔴"
    return (
        f"🚨 <b>ALERTE INSIDER BUY</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏢 <b>{company_name}</b> (${symbol})\n"
        f"👤 {insider_name} — <i>{insider_title}</i>\n"
        f"💰 Montant: <b>${amount:,.0f}</b>\n\n"
        f"📊 <b>Fondamentaux</b>\n"
        f"  • ROIC: <b>{roic:.1f}%</b>\n"
        f"  • FCF: <b>${fcf:,.0f}</b>\n"
        f"  • Secteur: {sector}\n\n"
        f"📈 <b>Technique</b>\n"
        f"  • Secteur vs MM200: {sma_emoji} {'Au-dessus' if above_sma200 else 'En-dessous'}\n\n"
        f"🌍 <b>Macro</b>: {macro_trend}\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )


def format_crypto_alert(
    protocol: str,
    tvl: float,
    tvl_change: float,
    mcap: float,
    fdv: float,
    mcap_fdv_ratio: float,
    fees_24h: float | None,
) -> str:
    """Formate une alerte Crypto structurée pour Telegram."""
    fees_str = f"${fees_24h:,.0f}" if fees_24h else "N/A"
    return (
        f"🚨 <b>ALERTE CRYPTO — TVL SPIKE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 <b>{protocol.upper()}</b>\n"
        f"📊 TVL: <b>${tvl:,.0f}</b> ({tvl_change:+.1f}%)\n\n"
        f"💎 <b>Métriques</b>\n"
        f"  • Market Cap: ${mcap:,.0f}\n"
        f"  • FDV: ${fdv:,.0f}\n"
        f"  • Ratio MCap/FDV: <b>{mcap_fdv_ratio:.2f}</b>\n"
        f"  • Fees 24h: {fees_str}\n\n"
        f"✅ Ratio MCap/FDV > 0.4 — Dilution limitée\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )
