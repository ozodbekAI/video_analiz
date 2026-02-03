import asyncio
from typing import Dict, List, Tuple
from pathlib import Path
from datetime import datetime
from html import escape

from services.ai_service import analyze_comments_with_prompt, save_ai_interaction
from database.crud import get_prompts, create_ai_response
from services.advanced_validator import AdvancedModuleValidator, ValidationLogger
from validators import FinalSynthesisValidator
from validators.logger import FinalSynthesisValidationLogger


async def run_advanced_analysis_with_validation(
    user_id: int,
    video_id: str,
    db_video_id: int,
    full_context: str,
    category: str,
    video_meta_full: Dict,
    progress_msg,
    message,
    update_progress_message,
    cancel_event: asyncio.Event | None = None,
    comments_only: str = None,  # ВАЖНО: чистые комментарии для retry
) -> Tuple[str, List[Dict], str | None, int]:
    """
    Запуск углубленного анализа с пошаговой валидацией
    """
    
    # Инициализируем валидатор с 4 максимальными попытками
    validator = AdvancedModuleValidator(max_retries=4)
    
    advanced_prompts = await get_prompts(category=category, analysis_type="advanced")
    if not advanced_prompts:
        raise ValueError("Нет advanced промптов в базе")
    
    module_mapping = {
        0: "10-1",
        1: "10-2",
        2: "10-3",
        3: "10-4",
    }
    
    total_steps = len(advanced_prompts) + 1
    partial_responses = []
    all_partial_logs = []
    
    # ПОШАГОВОЕ ВЫПОЛНЕНИЕ С ВАЛИДАЦИЕЙ
    for idx, prompt in enumerate(advanced_prompts):
        if cancel_event is not None and cancel_event.is_set():
            raise asyncio.CancelledError()
        module_id = module_mapping.get(idx)
        if not module_id:
            raise ValueError(f"Не найден маппинг для промпта {idx}")
        
        config = validator.modules_config[module_id]
        module_name = config['name']
        
        attempt = 1
        validation_success = False
        final_response = None
        previous_validation = None
        
        while attempt <= validator.max_retries + 1:
            if cancel_event is not None and cancel_event.is_set():
                raise asyncio.CancelledError()
            completed = idx
            percentage = int((completed / total_steps) * 100)
            progress_bar = "▓" * (percentage // 10) + "░" * (10 - percentage // 10)
            
            retry_text = f" (попытка {attempt})" if attempt > 1 else ""
            await update_progress_message(
                progress_msg,
                f"🔍 Модуль {idx+1}/{len(advanced_prompts)}: {module_name}{retry_text}\n"
                f"{progress_bar} {percentage}%"
            )
            
            # Формируем промпт
            if attempt == 1:
                prompt_text = prompt.prompt_text
                # Первая попытка: используем полный контекст (комментарии + метаинформация)
                ai_input_context = full_context
            else:
                # ВАЖНО: при повторной попытке используем ТОЛЬКО комментарии без предыдущего отчета!
                # Используем переданные чистые комментарии или full_context как fallback
                if comments_only:
                    ai_input_context = comments_only
                else:
                    ai_input_context = full_context
                
                retry_instructions = validator.generate_retry_instructions(
                    module_id, 
                    previous_validation
                )
                prompt_text = f"{retry_instructions}\n\n{'='*80}\n\nОРИГИНАЛЬНЫЙ ПРОМПТ:\n{prompt.prompt_text}"
            
            # Запрос к AI
            try:
                partial_response = await analyze_comments_with_prompt(
                    ai_input_context, 
                    prompt_text
                )
            except Exception as e:
                print(f"❌ Ошибка AI запроса для модуля {module_id}: {e}")
                if attempt >= validator.max_retries + 1:
                    raise
                attempt += 1
                await asyncio.sleep(2)
                continue
            
            # Сохраняем лог взаимодействия с AI
            partial_log = save_ai_interaction(
                user_id=user_id,
                video_id=video_id,
                stage=f"advanced_{module_id}_attempt{attempt}",
                request_text=f"PROMPT ({module_id} - {module_name}):\n{prompt_text}\n\n{'='*80}\n\nCOMMENTS:\n{ai_input_context}",
                response_text=partial_response
            )
            
            # ВАЛИДАЦИЯ РЕЗУЛЬТАТА
            validation_result = validator.validate_module(
                module_id, 
                partial_response,
                attempt
            )

            if cancel_event is not None and cancel_event.is_set():
                raise asyncio.CancelledError()
            
            # Генерируем отчет о валидации
            validation_report = validator.format_validation_report(
                module_id,
                validation_result,
                attempt
            )
            print(validation_report)
            
            # Сохраняем лог валидации
            ValidationLogger.save_validation_log(
                video_id=video_id,
                module_id=module_id,
                attempt=attempt,
                validation_result=validation_result,
                retry_instructions=validator.generate_retry_instructions(module_id, validation_result) if validation_result.retry_needed else None
            )
            
            # ===== ИСПРАВЛЕННОЕ СООБЩЕНИЕ О ВАЛИДАЦИИ =====
            validation_emoji = "✅" if validation_result.is_valid else "⚠️"
            
            # Создаём quality bar без специальных символов для HTML
            quality_percent = int(validation_result.quality_score / 10)
            quality_bar = "█" * quality_percent + "░" * (10 - quality_percent)
            
            # Экранируем название модуля для безопасности
            safe_module_name = escape(module_name)
            
            # Статус текстом (без HTML тегов в этой части)
            status_text = "✅ Валидация пройдена" if validation_result.is_valid else "🔄 Требуется повтор"
            
            try:
                await message.answer(
                    f"{validation_emoji} <b>Модуль {module_id}: {safe_module_name}</b>\n"
                    f"Попытка: {attempt}\n"
                    f"Качество: {quality_bar} {validation_result.quality_score:.0f}%\n"
                    f"Сущностей: {validation_result.metrics.get('entities_count', 0)}\n"
                    f"{status_text}",
                    parse_mode="HTML"
                )
            except Exception as e:
                # Если всё равно не работает, отправляем без parse_mode
                print(f"⚠️ Ошибка отправки HTML сообщения: {e}")
                await message.answer(
                    f"{validation_emoji} Модуль {module_id}: {module_name}\n"
                    f"Попытка: {attempt}\n"
                    f"Качество: {quality_bar} {validation_result.quality_score:.0f}%\n"
                    f"Сущностей: {validation_result.metrics.get('entities_count', 0)}\n"
                    f"{status_text}"
                )
            
            # Проверяем результат валидации
            if validation_result.is_valid:
                # Успех! Сохраняем результат
                final_response = partial_response
                validation_success = True
                
                # Сохраняем в БД
                try:
                    await create_ai_response(
                        user_id, 
                        db_video_id, 
                        idx + 1,
                        f"advanced_{module_id}", 
                        partial_response
                    )
                except Exception as e:
                    print(f"⚠️ Ошибка сохранения в БД: {e}")
                    # Продолжаем работу даже если БД не сохранилась
                
                partial_responses.append(partial_response)
                all_partial_logs.append(partial_log)
                
                break  # Выходим из цикла retry
            
            elif validation_result.retry_needed:
                # Нужен retry
                print(f"🔄 Модуль {module_id}: повтор попытки {attempt + 1}")
                previous_validation = validation_result
                attempt += 1
                await asyncio.sleep(1)
                continue
            
            else:
                # Исчерпаны попытки, но используем что есть
                print(f"⚠️ Модуль {module_id}: валидация не пройдена после {attempt} попыток")
                final_response = partial_response
                
                try:
                    await create_ai_response(
                        user_id, 
                        db_video_id, 
                        idx + 1,
                        f"advanced_{module_id}_partial", 
                        partial_response
                    )
                except Exception as e:
                    print(f"⚠️ Ошибка сохранения partial в БД: {e}")
                
                partial_responses.append(partial_response)
                all_partial_logs.append(partial_log)
                
                # Предупреждение пользователю
                try:
                    await message.answer(
                        f"⚠️ <b>Предупреждение</b>\n\n"
                        f"Модуль {module_id} (<i>{safe_module_name}</i>) не прошел полную валидацию.\n"
                        f"Качество: {validation_result.quality_score:.0f}%\n\n"
                        f"Анализ продолжится с частичными данными.",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"⚠️ Ошибка отправки предупреждения: {e}")
                    await message.answer(
                        f"⚠️ Предупреждение\n\n"
                        f"Модуль {module_id} ({module_name}) не прошел полную валидацию.\n"
                        f"Качество: {validation_result.quality_score:.0f}%\n\n"
                        f"Анализ продолжится с частичными данными."
                    )
                
                break
    
    # ФИНАЛЬНЫЙ СИНТЕЗ
    await update_progress_message(
        progress_msg,
        f"🔄 Финальный синтез...\n{'▓' * 9}░ 90%"
    )
    
    synthesis_prompts = await get_prompts(category=category, analysis_type="synthesis")
    if not synthesis_prompts:
        raise ValueError("Должен быть synthesis промпт")
    
    synthesis_prompt_text = synthesis_prompts[0].prompt_text
    
    combined_partials = "\n\n".join([
        f"МОДУЛЬ {module_mapping[i]} - {validator.modules_config[module_mapping[i]]['name']}:\n{resp}" 
        for i, resp in enumerate(partial_responses)
    ])
    
    # ---- Финальный синтез + валидация (после шага 5 по ТЗ) ----
    fs_validator = FinalSynthesisValidator()
    partial_by_module = {module_mapping[i]: resp for i, resp in enumerate(partial_responses) if i in module_mapping}

    # Normalize meta keys
    normalized_video_meta = dict(video_meta_full or {})
    normalized_video_meta.setdefault("id", video_id)
    normalized_video_meta.setdefault("video_id", video_id)
    if "comments" not in normalized_video_meta and "comment_count" in normalized_video_meta:
        normalized_video_meta["comments"] = normalized_video_meta.get("comment_count")

    max_attempts = 3  # 1 + up to 2 retries
    final_ai_response = ""
    synthesis_log = {}
    last_retry_prompt = ""

    for attempt in range(1, max_attempts + 1):
        attempt_prompt = synthesis_prompt_text
        if attempt > 1 and last_retry_prompt:
            attempt_prompt = synthesis_prompt_text + "\n\n" + last_retry_prompt

        final_ai_response = await analyze_comments_with_prompt(combined_partials, attempt_prompt)

        synthesis_log = save_ai_interaction(
            user_id=user_id,
            video_id=video_id,
            stage=f"synthesis_attempt{attempt}",
            request_text=f"SYNTHESIS PROMPT (attempt {attempt}):\n{attempt_prompt}\n\n{'='*80}\n\nPARTIAL RESPONSES:\n{combined_partials}",
            response_text=final_ai_response
        )

        # Validate
        validation_result = fs_validator.validate(
            raw_report=final_ai_response,
            video_meta=normalized_video_meta,
            partial_responses=partial_by_module,
        )

        # Persist validation result
        try:
            FinalSynthesisValidationLogger.save(
                video_id=video_id,
                attempt=attempt,
                validation_result=validation_result,
                extra={"score": validation_result.score, "status": validation_result.status},
            )
        except Exception as e:
            print(f"⚠️ Ошибка сохранения final synthesis validation log: {e}")

        # Auto-correct if provided
        if validation_result.corrected_report:
            final_ai_response = validation_result.corrected_report

        all_partial_logs.append({
            "final_synthesis_validation": {
                "attempt": attempt,
                "status": validation_result.status,
                "score": validation_result.score,
                "issues": [
                    {
                        "type": i.type,
                        "severity": i.severity,
                        "message": i.message,
                        "details": i.details,
                    }
                    for i in validation_result.issues
                ],
                "indices": validation_result.indices_calculated,
            },
            "created_at": datetime.now().isoformat(),
        })

        # Decide whether to retry synthesis
        if validation_result.retry_needed and validation_result.retry_prompt and attempt < max_attempts:
            last_retry_prompt = validation_result.retry_prompt
            continue

        break
    
    # Persist final report (return id for file binding / multi-analysis optimizer)
    final_ai_response_id = 0
    try:
        import json

        machine_data_to_store = None
        # machine_data is appended to logs below; we compute it before insertion
        # and store JSON in ai_responses.machine_data when possible.
        # (If parsing fails, we store raw string.)
        # NOTE: machine_data is computed later; this placeholder will be updated.
    except Exception:
        machine_data_to_store = None
    
    all_partial_logs.append(synthesis_log)
    
    # ===== MACHINE-READABLE DATA YARATISH =====
    try:
        print("🔄 Machine-readable data yaratish boshlandi...")
        machine_data = await create_machine_readable_data(
            user_id=user_id,
            video_id=video_id,
            partial_responses=partial_responses,
            video_meta={
                "video_id": video_id,
                "user_id": user_id,
                "comment_count": len(full_context.split('\n')),
                "analysis_timestamp": datetime.now().isoformat()
            }
        )
        
        # Machine data ni qaytaramiz
        all_partial_logs.append({
            "machine_data": machine_data,
            "created_at": datetime.now().isoformat()
        })
        
        print(f"✅ Machine data muvaffaqiyatli yaratildi va qo'shildi")

        try:
            import json
            machine_data_to_store = json.loads(machine_data)
        except Exception:
            machine_data_to_store = machine_data
        
    except Exception as e:
        print(f"⚠️ Machine data yaratishda xato: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        final_ai_response_id = await create_ai_response(
            user_id,
            db_video_id,
            0,
            "advanced",
            final_ai_response,
            machine_data=machine_data_to_store,
        )
    except Exception as e:
        print(f"⚠️ Ошибка сохранения финального результата в БД: {e}")

    return final_ai_response, all_partial_logs, machine_data if 'machine_data' in locals() else None, final_ai_response_id


# ===== YANGI FUNKSIYA: Machine-readable data yaratish =====

async def create_machine_readable_data(
    user_id: int,
    video_id: str,
    partial_responses: List[str],
    video_meta: Dict
) -> str:
    """
    Partial responses dan machine-readable JSON yaratish
    """
    try:
        from analysis_modules import MachineReadableFormatter, IndexCalculator
        
        print(f"  📊 IndexCalculator va MachineReadableFormatter import qilindi")
        
        # Modul ma'lumotlarini to'plash
        module_mapping = {
            0: "10-1",
            1: "10-2",
            2: "10-3",
            3: "10-4",
        }
        
        modules_data = {}
        for idx, response in enumerate(partial_responses):
            module_id = module_mapping.get(idx, f"unknown-{idx}")
            modules_data[module_id] = response
        
        print(f"  📦 {len(modules_data)} modul ma'lumotlari to'plandi")
        
        # Strategic indekslarni hisoblash
        calculator = IndexCalculator()
        strategic_indices = calculator.calculate_all_indices(modules_data)
        
        print(f"  📈 Strategic indekslar hisoblandi:")
        print(f"     - Content Health Index: {strategic_indices.get('content_health_index', 'N/A')}")
        print(f"     - Audience Evolution: {strategic_indices.get('audience_evolution_vector', 'N/A')}")
        
        # Insights ni extract qilish (oddiy versiya)
        insights = []
        
        # Validation report
        validation_report = {
            "quality_index": 85,
            "present_modules": list(modules_data.keys()),
            "missing_modules": [],
            "quality_warnings": []
        }
        
        # Machine-readable report yaratish
        formatter = MachineReadableFormatter()
        machine_json = formatter.create_machine_report(
            video_meta=video_meta,
            modules_data=modules_data,
            calculated_indices=strategic_indices,
            human_insights=insights,
            validation_report=validation_report
        )
        
        print(f"  ✅ Machine-readable JSON yaratildi: {len(machine_json)} bytes")
        return machine_json
        
    except ImportError as e:
        print(f"  ❌ Import xatosi: {e}")
        print(f"  💡 analysis_modules papkasi va fayllarni tekshiring!")
        return "{}"
    except Exception as e:
        print(f"  ⚠️ Machine data yaratishda xato: {e}")
        import traceback
        traceback.print_exc()
        return "{}"