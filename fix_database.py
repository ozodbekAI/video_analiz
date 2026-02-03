# Database fix utilities
import asyncio
from database.crud import check_prompts_exist
from database.engine import async_session
from database.models import AIResponse
from sqlalchemy import update


async def test_prompts():
    """Test prompts existence"""
    for analysis_type in [
        'audience_map',
        'content_prediction',
        'channel_diagnostics',
        'content_ideas',
        'viral_potential',
        'iterative_ideas'
    ]:
        result = await check_prompts_exist(analysis_type)
        print(f"\n{analysis_type}:")
        print(f"  Exists: {result['exists']}")
        print(f"  Found: {result['found']}")
        print(f"  Missing: {result['missing']}")


async def fix_strategic_hub_flags():
    """
    Fix is_for_strategic_hub flag for existing advanced analyses.
    All advanced/advanced_final analyses should be in Strategic Hub.
    """
    async with async_session() as session:
        # Count before
        from sqlalchemy import select, func
        count_before = await session.execute(
            select(func.count(AIResponse.id))
            .where(AIResponse.analysis_type.in_(["advanced", "advanced_final"]))
            .where(AIResponse.is_for_strategic_hub == True)
        )
        before = count_before.scalar_one()
        
        # Update all advanced analyses
        result = await session.execute(
            update(AIResponse)
            .where(AIResponse.analysis_type.in_(["advanced", "advanced_final"]))
            .where(AIResponse.chunk_id == 0)
            .values(is_for_strategic_hub=True)
        )
        await session.commit()
        
        # Count after
        count_after = await session.execute(
            select(func.count(AIResponse.id))
            .where(AIResponse.analysis_type.in_(["advanced", "advanced_final"]))
            .where(AIResponse.is_for_strategic_hub == True)
        )
        after = count_after.scalar_one()
        
        print(f"✅ Strategic Hub flags fixed!")
        print(f"   Before: {before} analyses in hub")
        print(f"   After: {after} analyses in hub")
        print(f"   Updated: {result.rowcount} rows")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "prompts":
            asyncio.run(test_prompts())
        elif sys.argv[1] == "strategic_hub":
            asyncio.run(fix_strategic_hub_flags())
        else:
            print("Usage: python fix_database.py [prompts|strategic_hub]")
    else:
        print("Usage: python fix_database.py [prompts|strategic_hub]")
        print("  prompts       - Test prompts existence")
        print("  strategic_hub - Fix Strategic Hub flags for existing analyses")