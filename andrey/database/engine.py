import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from contextlib import asynccontextmanager
from config import Config
from datetime import datetime, timezone

Base = declarative_base()

config = Config()

# Engine yaratish
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,  # True qilsangiz SQL loglar chiqadi
    pool_pre_ping=True,  # Connectionlarni tekshirish
    pool_size=10,
    max_overflow=20
)

# Session maker

async_session = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def create_db():
    """Database va tablelarni yaratish"""
    async with engine.begin() as conn:
        # UUID extension
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        
        # Barcha tablelarni yaratish
        await conn.run_sync(Base.metadata.create_all)

        # TZ-2: idempotent schema patches for existing installations
        await _apply_schema_patches(conn)

        # TZ-2: seed default multi-analysis evaluator prompt (if none)
        await _seed_default_multi_analysis_prompt(conn)
    
    print("✅ Database tables created successfully")


async def _apply_schema_patches(conn):
    """Apply additive schema changes that SQLAlchemy create_all won't do (ALTER TABLE / indexes).

    Safe to run multiple times.
    """
    # --- ai_responses new columns ---
    await conn.execute(text("""
        ALTER TABLE ai_responses
            ADD COLUMN IF NOT EXISTS pdf_file_path VARCHAR(500);
    """))
    await conn.execute(text("""
        ALTER TABLE ai_responses
            ADD COLUMN IF NOT EXISTS analysis_set_id INTEGER;
    """))
    await conn.execute(text("""
        ALTER TABLE ai_responses
            ADD COLUMN IF NOT EXISTS is_for_strategic_hub BOOLEAN DEFAULT FALSE;
    """))

    # FK (best-effort; do not fail if already exists)
    await conn.execute(text("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'fk_ai_responses_analysis_set_id'
        ) THEN
            ALTER TABLE ai_responses
                ADD CONSTRAINT fk_ai_responses_analysis_set_id
                FOREIGN KEY (analysis_set_id) REFERENCES video_analysis_sets(id)
                ON DELETE SET NULL;
        END IF;
    END $$;
    """))

    # Indexes
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_ai_responses_analysis_set_id
        ON ai_responses (analysis_set_id);
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_ai_responses_is_for_strategic_hub
        ON ai_responses (is_for_strategic_hub);
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_video_analysis_sets_next_eval
        ON video_analysis_sets (next_evaluation_at);
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_video_analysis_sets_status
        ON video_analysis_sets (status);
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_quality_markers_set_id
        ON analysis_quality_markers (analysis_set_id);
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_quality_markers_is_best
        ON analysis_quality_markers (is_best);
    """))


async def _seed_default_multi_analysis_prompt(conn):
    """Insert the default evaluator prompt if table is empty.

    The prompt is designed to be editable via external web admin.
    """
    # Check if any prompt exists
    res = await conn.execute(text("SELECT COUNT(1) FROM multi_analysis_prompts"))
    cnt = int(res.scalar() or 0)
    if cnt > 0:
        return

    # Default prompt text (from TZ-2 docx, 'multi_analysis_evaluation_v1')
    prompt_text = """Ты эксперт-аналитик YouTube контента. Перед тобой несколько анализов одного и того же видео, выполненных в разное время.

ИНФОРМАЦИЯ О ВИДЕО:
- Video ID: {video_id}
- Название: {video_title}
- Всего анализов: {total_analyses}
- Период анализа: {analysis_period}

КРИТЕРИИ ОЦЕНКИ (по шкале 0-10):
1. ПОЛНОТА АНАЛИЗА (10 баллов): Насколько полно охвачены все аспекты видео (метаданные, тональность, темы, эмоции, аудитория, стратегические инсайты)
2. СТРУКТУРИРОВАННОСТЬ (10 баллов): Соответствие формату VIDEO_ANALYSIS_REPORT, наличие всех обязательных разделов, правильная структура
3. ГЛУБИНА ИНСАЙТОВ (10 баллов): Качество, оригинальность и глубина стратегических инсайтов, наличие кросс-модульных связей
4. ПРАКТИЧЕСКАЯ ЦЕННОСТЬ (10 баллов): Полезность рекомендаций для создателя, конкретность, реализуемость советов
5. ЧЕТКОСТЬ ИЗЛОЖЕНИЯ (10 баллов): Ясность, логичность, отсутствие противоречий, качество формулировок

АНАЛИЗЫ ДЛЯ ОЦЕНКИ:
{analyses_content}

ЗАДАЧА:
1. Оцени каждый анализ по 5 критериям (0-10 баллов за каждый критерий, где 10 - идеально)
2. Рассчитай общий балл для каждого анализа (среднее арифметическое по 5 критериям)
3. Выбери лучший анализ (с максимальным общим баллом)
4. Объясни кратко, почему этот анализ лучше
5. Предоставь рекомендации по улучшению для каждого анализа
6. Проранжируй анализы по качеству (1 - лучший, далее по убыванию)

ФОРМАТ ОТВЕТА (строго JSON, без дополнительного текста):
{
  \"evaluations\": [
    {
      \"analysis_id\": 101,
      \"scores\": {
        \"completeness\": 8,
        \"structure\": 8,
        \"insights_depth\": 7,
        \"practical_value\": 8,
        \"clarity\": 9
      },
      \"total_score\": 8.0,
      \"quality_rank\": 2,
      \"strengths\": [\"...\"],
      \"weaknesses\": [\"...\"],
      \"improvement_suggestions\": [\"...\"]
    }
  ],
  \"best_analysis_id\": 102,
  \"selection_reason\": \"...\",
  \"comparison_summary\": \"...\",
  \"overall_recommendations\": [\"...\"]
}

ВАЖНЫЕ ПРАВИЛА:
- Оценивай только на основе предоставленного текста анализов
- Не добавляй анализ, который не был предоставлен
- Если анализ имеет критические недостатки (отсутствие ключевых разделов), снижай оценку
- Будь объективен и последователен в оценке
"""

    now = datetime.now(tz=timezone.utc)
    await conn.execute(
        text(
            """
            INSERT INTO multi_analysis_prompts (name, prompt_text, version, description, is_active, created_at, updated_at)
            VALUES (:name, :prompt_text, :version, :description, TRUE, :created_at, :updated_at)
            """
        ),
        {
            "name": "multi_analysis_evaluation_v1",
            "prompt_text": prompt_text,
            "version": "1.0",
            "description": "TZ-2 default evaluator prompt (editable via external web admin)",
            "created_at": now,
            "updated_at": now,
        },
    )


async def get_session() -> AsyncSession:
    """Session olish uchun context manager"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
