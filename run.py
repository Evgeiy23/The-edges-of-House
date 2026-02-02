import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Launcher for The Edges of House")
    parser.add_argument("--wc", "--with-cheats", action="store_true", help="Enable cheats")
    parser.add_argument("--wom", "--without-music", action="store_true", help="Disable music")
    args = parser.parse_args()

    # Определяем директорию, где находится этот скрипт
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Меняем текущую рабочую директорию на директорию скрипта
    os.chdir(script_dir)
    
    # Путь к файлу main.py
    main_script = os.path.join(script_dir, "src", "main.py")
    
    # Проверяем, существует ли main.py
    if not os.path.exists(main_script) and not getattr(sys, 'frozen', False):
        # print(f"Ошибка: {main_script} не найден.")
        sys.exit(1)
        
    # Запускаем main.py используя текущий интерпретатор Python
    # В замороженном режиме (Nuitka/PyInstaller), импортируем main напрямую, чтобы избежать проблем с подпроцессами
    if getattr(sys, 'frozen', False):
        # Добавляем src в sys.path, чтобы можно было импортировать main
        src_path = os.path.join(script_dir, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
            
        try:
            from src.main import main as game_main
            # Реконструируем sys.argv для игры
            sys.argv = [sys.argv[0]]
            if args.wc:
                sys.argv.append("--wc")
            if args.wom:
                sys.argv.append("--wom")
                
            game_main()
        except Exception:
            import traceback
            traceback.print_exc()
            print("\n" + "="*60)
            print("КРИТИЧЕСКАЯ ОШИБКА: Не удалось запустить приложение.")
            print("Пожалуйста, сообщите об этой ошибке разработчику.")
            print("="*60 + "\n")
            input("Нажмите Enter для выхода...")
            sys.exit(1)
    else:
        # Используем subprocess, чтобы гарантировать запуск в той же среде
        import subprocess
        
        cmd = [sys.executable, main_script]
        if args.wc:
            cmd.append("--wc")
        if args.wom:
            cmd.append("--wom")
            
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            # print(f"Ошибка запуска игры: {e}")
            sys.exit(e.returncode)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        print("\n" + "="*60)
        print("КРИТИЧЕСКАЯ ОШИБКА ЛАУНЧЕРА")
        print("="*60 + "\n")
        input("Нажмите Enter для выхода...")
