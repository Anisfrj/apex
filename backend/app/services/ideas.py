# backend/app/services/ideas.py
from app.core.database import get_db_connection

async def get_ideas_ranked(
    label: str = None,
    sector: str = None,
    min_score: int = 0
) -> list[dict]:
    query = """
        SELECT *
        FROM v_ideas_ranked
        WHERE score_final_adjusted >= %(min_score)s
    """
    params = {"min_score": min_score}

    if label:
        query += " AND final_label = %(label)s"
        params["label"] = label

    if sector:
        query += " AND sector = %(sector)s"
        params["sector"] = sector

    query += " ORDER BY score_final_adjusted DESC"

    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            rows = await cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in rows]


async def get_idea_detail(idea_id: int) -> dict:
    """Retourne une idea avec ses signaux liés."""
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            # Idea principale
            await cur.execute(
                "SELECT * FROM v_ideas_ranked WHERE id = %s",
                (idea_id,)
            )
            row = await cur.fetchone()
            cols = [desc[0] for desc in cur.description]
            idea = dict(zip(cols, row))

            # Signaux liés
            await cur.execute("""
                SELECT s.symbol, s.signal_type, s.direction,
                       s.strength, s.drivers, s.as_of
                FROM signals s
                JOIN idea_signals_link isl ON isl.signal_id = s.id
                WHERE isl.idea_id = %s
                ORDER BY s.strength DESC
            """, (idea_id,))
            sig_rows = await cur.fetchall()
            sig_cols = [desc[0] for desc in cur.description]
            idea["signals"] = [dict(zip(sig_cols, r)) for r in sig_rows]

            return idea


async def generate_ideas_from_signals() -> int:
    """Appelle la fonction SQL generate_alerts() et retourne le nb d'alertes créées."""
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT generate_alerts()")
            result = await cur.fetchone()
            await conn.commit()
            return result[0]
