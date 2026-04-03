# backend/app/services/ideas.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def get_ideas_ranked(
    db: AsyncSession,
    label: str = None,
    sector: str = None,
    min_score: int = 0
) -> list[dict]:
    query = """
        SELECT *
        FROM v_ideas_ranked
        WHERE score_final_adjusted >= :min_score
    """
    params = {"min_score": min_score}

    if label:
        query += " AND final_label = :label"
        params["label"] = label

    if sector:
        query += " AND sector = :sector"
        params["sector"] = sector

    query += " ORDER BY score_final_adjusted DESC"

    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [dict(row) for row in rows]


async def get_idea_detail(db: AsyncSession, idea_id: int) -> dict:
    """Retourne une idea avec ses signaux liés."""
    # Idea principale
    result = await db.execute(
        text("SELECT * FROM v_ideas_ranked WHERE id = :id"),
        {"id": idea_id}
    )
    row = result.mappings().first()
    if not row:
        return None
    idea = dict(row)

    # Signaux liés
    sig_result = await db.execute(
        text("""
            SELECT s.symbol, s.signal_type, s.direction,
                   s.strength, s.drivers, s.as_of
            FROM signals s
            JOIN idea_signals_link isl ON isl.signal_id = s.id
            WHERE isl.idea_id = :idea_id
            ORDER BY s.strength DESC
        """),
        {"idea_id": idea_id}
    )
    idea["signals"] = [dict(r) for r in sig_result.mappings().all()]

    return idea


async def generate_ideas_from_signals(db: AsyncSession) -> int:
    """Appelle la fonction SQL generate_alerts() et retourne le nb d'alertes créées."""
    result = await db.execute(text("SELECT generate_alerts()"))
    row = result.fetchone()
    await db.commit()
    return row[0] if row else 0
