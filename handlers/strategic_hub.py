from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.client import get_main_menu_keyboard

router = Router()

def build_step2_prompt(step1_prompt: str, step2_prompt: str) -> str:
    """
    Step2 prompt ichiga Step1 promptni kontekst sifatida qo‘shib beradi.
    Step2 doimo asosiy instruktsiya bo‘lib qoladi.
    """
    return (
        "ВАЖНО: Ниже приведены инструкции Шага 1 (для контекста), "
        "затем инструкции Шага 2 (основные). Следуй Шагу 2.\n\n"
        "=== ШАГ 1: ИСХОДНЫЙ ПРОМПТ (КОНТЕКСТ) ===\n"
        f"{step1_prompt}\n\n"
        "=== ШАГ 2: ОСНОВНОЙ ПРОМПТ ===\n"
        f"{step2_prompt}"
    )


@router.callback_query(F.data == "iterative_ideas")
async def iterative_ideas_handler(cb: CallbackQuery):
    await cb.message.answer("🧠 Запуск итеративного генератора идей...")

    try:
        from services.iterative_ideas_service import optimizer
        from database.crud import get_user_analysis_history
        
        history = await get_user_analysis_history(cb.from_user.id)
        
        if len(history) < 5:
            await cb.message.answer(
                "❌ Недостаточно данных.\n\n"
                "📊 Требуется минимум 5 углубленных анализов.\n"
                f"✅ У вас: {len(history)}\n\n"
                "Проведите больше анализов своих видео для использования этой функции.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        from database.crud import get_evolution_prompts
        prompts = await get_evolution_prompts("iterative_ideas")
        
        if not all([
            prompts.get('evaluator_creative'),
            prompts.get('evaluator_analytical'),
            prompts.get('evaluator_practical'),
            prompts.get('improver')
        ]):
            await cb.message.answer(
                "❌ Система не настроена.\n\n"
                "Обратитесь к администратору для настройки промптов.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        

        initial_ideas = history[:10]  
        
        optimized_ideas = await optimizer.run_optimization_pipeline(
            initial_ideas=initial_ideas,
            prompts=prompts,
            max_iterations=3
        )
        
        report = optimizer.generate_optimization_report(optimized_ideas)
        
        await cb.message.answer(report, parse_mode="HTML")
        
    except ValueError as e:
        await cb.message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        await cb.message.answer(
            f"❌ Непредвиденная ошибка: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data == "audience_map")
async def audience_map_handler(cb: CallbackQuery):
    await cb.message.answer("🗺️ Анализ аудитории...")

    try:
        from database.crud import get_user_analysis_history, get_evolution_prompts
        from services.ai_service import analyze_comments_with_prompt
        
        history = await get_user_analysis_history(cb.from_user.id)
        
        if len(history) < 3:
            await cb.message.answer(
                "❌ Недостаточно данных.\n\n"
                "📊 Требуется минимум 3 анализа.\n"
                f"✅ У вас: {len(history)}",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        prompts = await get_evolution_prompts("audience_map")
        
        if not prompts.get('step1') or not prompts.get('step2'):
            await cb.message.answer(
                "❌ Промпты не настроены.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        combined_data = "\n\n=== РАЗДЕЛИТЕЛЬ ===\n\n".join(history)
        
        step1_result = await analyze_comments_with_prompt(
            combined_data,
            prompts['step1'].prompt_text
        )
        

        step2_prompt = build_step2_prompt(
            prompts['step1'].prompt_text,
            prompts['step2'].prompt_text
        )

        final_result = await analyze_comments_with_prompt(
            step1_result,
            step2_prompt
        )
            
        await cb.message.answer(final_result, parse_mode="HTML")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        await cb.message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data == "content_prediction")
async def content_prediction_handler(cb: CallbackQuery):
    await cb.message.answer("🔮 Прогнозируем лучший контент...")

    try:
        from database.crud import get_user_analysis_history, get_evolution_prompts
        from services.ai_service import analyze_comments_with_prompt
        
        history = await get_user_analysis_history(cb.from_user.id)
        
        if len(history) < 5:
            await cb.message.answer(
                "❌ Недостаточно данных.\n\n"
                "📊 Требуется минимум 5 анализов.\n"
                f"✅ У вас: {len(history)}",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        prompts = await get_evolution_prompts("content_prediction")
        
        if not prompts.get('step1') or not prompts.get('step2'):
            await cb.message.answer(
                "❌ Промпты не настроены.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        combined_data = "\n\n=== РАЗДЕЛИТЕЛЬ ===\n\n".join(history)
        
        step1_result = await analyze_comments_with_prompt(
            combined_data,
            prompts['step1'].prompt_text
        )
        
        step2_prompt = build_step2_prompt(
            prompts['step1'].prompt_text,
            prompts['step2'].prompt_text
        )

        final_result = await analyze_comments_with_prompt(
            step1_result,
            step2_prompt
        )
        
        await cb.message.answer(final_result, parse_mode="HTML")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        await cb.message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data == "channel_diagnostics")
async def channel_diagnostics_handler(cb: CallbackQuery):
    await cb.message.answer("📊 Диагностика канала...")

    try:
        from database.crud import get_user_analysis_history, get_evolution_prompts
        from services.ai_service import analyze_comments_with_prompt
        
        history = await get_user_analysis_history(cb.from_user.id)
        
        if len(history) < 5:
            await cb.message.answer(
                "❌ Недостаточно данных.\n\n"
                "📊 Требуется минимум 5 анализов.\n"
                f"✅ У вас: {len(history)}",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        prompts = await get_evolution_prompts("channel_diagnostics")
        
        if not prompts.get('step1') or not prompts.get('step2'):
            await cb.message.answer(
                "❌ Промпты не настроены.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        combined_data = "\n\n=== РАЗДЕЛИТЕЛЬ ===\n\n".join(history)
        
        step1_result = await analyze_comments_with_prompt(
            combined_data,
            prompts['step1'].prompt_text
        )
        
        step2_prompt = build_step2_prompt(
            prompts['step1'].prompt_text,
            prompts['step2'].prompt_text
        )

        final_result = await analyze_comments_with_prompt(
            step1_result,
            step2_prompt
        )
        
        await cb.message.answer(final_result, parse_mode="HTML")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        await cb.message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data == "content_ideas")
async def content_ideas_handler(cb: CallbackQuery):
    await cb.message.answer("💡 Генерируем идеи...")

    try:
        from database.crud import get_user_analysis_history, get_evolution_prompts
        from services.ai_service import analyze_comments_with_prompt
        
        history = await get_user_analysis_history(cb.from_user.id)
        
        if len(history) < 3:
            await cb.message.answer(
                "❌ Недостаточно данных.\n\n"
                "📊 Требуется минимум 3 анализа.\n"
                f"✅ У вас: {len(history)}",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        prompts = await get_evolution_prompts("content_ideas")
        
        if not prompts.get('step1') or not prompts.get('step2'):
            await cb.message.answer(
                "❌ Промпты не настроены.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        combined_data = "\n\n=== РАЗДЕЛИТЕЛЬ ===\n\n".join(history)
        
        step1_result = await analyze_comments_with_prompt(
            combined_data,
            prompts['step1'].prompt_text
        )
        
        step2_prompt = build_step2_prompt(
            prompts['step1'].prompt_text,
            prompts['step2'].prompt_text
        )

        final_result = await analyze_comments_with_prompt(
            step1_result,
            step2_prompt
        )
        
        await cb.message.answer(final_result, parse_mode="HTML")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        await cb.message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data == "viral_potential")
async def viral_potential_handler(cb: CallbackQuery):
    await cb.message.answer("⚡ Анализ виральности...")

    try:
        from database.crud import get_user_analysis_history, get_evolution_prompts
        from services.ai_service import analyze_comments_with_prompt
        
        history = await get_user_analysis_history(cb.from_user.id)
        
        if len(history) < 5:
            await cb.message.answer(
                "❌ Недостаточно данных.\n\n"
                "📊 Требуется минимум 5 анализов.\n"
                f"✅ У вас: {len(history)}",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        prompts = await get_evolution_prompts("viral_potential")
        
        if not prompts.get('step1') or not prompts.get('step2'):
            await cb.message.answer(
                "❌ Промпты не настроены.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        combined_data = "\n\n=== РАЗДЕЛИТЕЛЬ ===\n\n".join(history)
        
        step1_result = await analyze_comments_with_prompt(
            combined_data,
            prompts['step1'].prompt_text
        )
        
        step2_prompt = build_step2_prompt(
            prompts['step1'].prompt_text,
            prompts['step2'].prompt_text
        )

        final_result = await analyze_comments_with_prompt(
            step1_result,
            step2_prompt
        )
        
        await cb.message.answer(final_result, parse_mode="HTML")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        await cb.message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )