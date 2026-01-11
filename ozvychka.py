import asyncio
import edge_tts

async def save_speech(text: str, output_file: str, voice: str = "ru-RU-DmitryNeural") -> None:
    """
    Сохраняет озвучку текста в файл
    
    Args:
        text: Текст для озвучки
        output_file: Путь к выходному файлу (например: 'output.mp3')
        voice: Голос (по умолчанию русский мужской)
    """
    try:
        # Создаем объект TTS
        communicate = edge_tts.Communicate(text, voice)
        
        # Сохраняем аудио в файл
        await communicate.save(output_file)
        print(f"✅ Аудио сохранено в: {output_file}")
        
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")

async def preview_male_voices():
    """Предпрослушивание разных мужских голосов"""
    male_voices = {
        "Dmitry (стандартный)": "ru-RU-DmitryNeural",
        "Mikhail (глубокий)": "ru-RU-MikhailNeural",
    }
    
    test_text = "В отчаянии Элиас находит старую карту, нарисованную его же рукой много лет назад."
    
    for voice_name, voice_code in male_voices.items():
        print(f"\n🎤 Тестирую голос: {voice_name}")
        print(f"Код голоса: {voice_code}")
        
        try:
            # Создаем временный файл для предпрослушивания
            temp_file = f"preview_{voice_name.replace(' ', '_')}.mp3"
            communicate = edge_tts.Communicate(test_text[:100], voice_code)  # Первые 100 символов для теста
            await communicate.save(temp_file)
            print(f"Создан файл для прослушивания: {temp_file}")
            
        except Exception as e:
            print(f"Ошибка: {e}")

# Основная функция
async def main():
    text_to_speak = """В отчаянии Элиас находит старую карту, нарисованную его же рукой много лет назад, но места на ней он не помнит. Карта ведёт в заброшенное подземелье под Валемаром, где, по легенде, хранится Сердце Камня — источник энергии, породивший Каменную Чуму."""

    # 🔥 ВЫБЕРИТЕ ОДИН ИЗ ЭТИХ ГОЛОСОВ:
    
    # 1. Дмитрий - самый популярный мужской голос, нейтральный и приятный
    voice_choice = "ru-RU-DmitryNeural"
    
    # 2. Михаил - более глубокий и драматичный, хорошо подходит для повествования
    # voice_choice = "ru-RU-MikhailNeural"
    
    # 3. Если хотите поэкспериментировать, можно попробовать и другие варианты:
    # voice_choice = "ru-RU-PavelNeural"  # Еще один мужской голос
    
    output_filename = "store3.mp3"
    
    # Сначала протестируем голоса (можно закомментировать после выбора)
    print("🎧 Тестирование мужских голосов...")
    await preview_male_voices()
    
    # Затем сохраняем основной текст
    print(f"\n📝 Сохраняю основной текст с голосом {voice_choice}...")
    await save_speech(text_to_speak, output_filename, voice_choice)

if __name__ == "__main__":
    asyncio.run(main())