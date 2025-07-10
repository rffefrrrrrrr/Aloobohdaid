import os
import sys

# Add current directory to sys.path to allow importing config and bot
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'config'))

def fix_bot_token_import(token):
    config_py_path = os.path.join(current_dir, 'config.py')
    config_config_py_path = os.path.join(current_dir, 'config', 'config.py')

    # Update config.py with the provided token
    if os.path.exists(config_py_path):
        with open(config_py_path, 'w', encoding='utf-8') as f:
            f.write(f'# تكوين البوت\n')
            f.write(f'BOT_TOKEN = "{token}"  # قم بتغيير هذا إلى رمز البوت الخاص بك\n')
        print(f"تم تحديث BOT_TOKEN في {config_py_path}")

    # Update config/config.py with the provided token (if it uses os.getenv)
    if os.path.exists(config_config_py_path):
        with open(config_config_py_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        with open(config_config_py_path, 'w', encoding='utf-8') as f:
            for line in lines:
                if line.strip().startswith('BOT_TOKEN = os.getenv("BOT_TOKEN"'):
                    f.write(f'BOT_TOKEN = os.getenv("BOT_TOKEN", "{token}")\n')
                else:
                    f.write(line)
        print(f"تم تحديث BOT_TOKEN في {config_config_py_path}")

    # Modify main.py to ensure correct import and usage
    main_py_path = os.path.join(current_dir, 'main.py')
    if os.path.exists(main_py_path):
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the import_modules function and replace its content
        start_marker = "def import_modules():"
        end_marker = "# إعداد سجل الأخطاء"

        start_index = content.find(start_marker)
        end_index = content.find(end_marker)

        if start_index != -1 and end_index != -1:
            # Define the exact block to replace to avoid syntax errors
            old_block_str = '''    # التحقق من وجود BOT_TOKEN في ملف config/config.py
    check_and_create_bot_token()
    
    try:
        # محاولة استيراد مباشرة من ملف config.py في المجلد الرئيسي
        import config
        from bot import Bot
        # from keep_alive_http import keep_alive # REMOVED
        print("تم استيراد BOT_TOKEN من config.py في المجلد الرئيسي")
        return Bot, config.BOT_TOKEN
    except (ImportError, AttributeError) as e:
        print(f"خطأ في استيراد الوحدات من config.py: {e}")
        
        try:
            # محاولة استيراد من config/config.py
            from config.config import BOT_TOKEN
            from bot import Bot
            # from keep_alive_http import keep_alive # REMOVED
            print("تم استيراد BOT_TOKEN من config/config.py")
            return Bot, BOT_TOKEN # REMOVED keep_alive
        except (ImportError, AttributeError) as e2:
            print(f"خطأ في استيراد الوحدات من config/config.py: {e2}")
            
            try:
                # محاولة إنشاء ملف config.py في المجلد الرئيسي
                root_config_path = os.path.join(current_dir, 'config.py')
                with open(root_config_path, 'w', encoding='utf-8') as f:
                    f.write('# تكوين البوت\n')
                    f.write('BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # قم بتغيير هذا إلى رمز البوت الخاص بك\n')
                print(f"تم إنشاء ملف {root_config_path}")
                print("يرجى تعديل الملف وإضافة رمز البوت الخاص بك")
                
                # محاولة استيراد مرة أخرى
                import importlib
                import config
                importlib.reload(config)
                from bot import Bot
                # from keep_alive_http import keep_alive # REMOVED
                print("تم استيراد BOT_TOKEN من config.py بعد إنشائه")
                return Bot, config.BOT_TOKEN # REMOVED keep_alive
            except Exception as e3:
                print(f"فشلت جميع محاولات الاستيراد: {e3}")
                sys.exit(1)'''

            new_block_str = '''    # التحقق من وجود BOT_TOKEN في ملف config/config.py
    check_and_create_bot_token()
    
    TELEGRAM_BOT_TOKEN = None
    Bot = None

    try:
        # محاولة استيراد مباشرة من ملف config.py في المجلد الرئيسي
        import config
        from bot import Bot
        TELEGRAM_BOT_TOKEN = config.BOT_TOKEN
        print("تم استيراد BOT_TOKEN من config.py في المجلد الرئيسي")
    except (ImportError, AttributeError) as e:
        print(f"خطأ في استيراد الوحدات من config.py: {e}")
        
        try:
            # محاولة استيراد من config/config.py
            from config.config import BOT_TOKEN
            from bot import Bot
            TELEGRAM_BOT_TOKEN = BOT_TOKEN
            print("تم استيراد BOT_TOKEN من config/config.py")
        except (ImportError, AttributeError) as e2:
            print(f"خطأ في استيراد الوحدات من config/config.py: {e2}")
            
            try:
                # محاولة إنشاء ملف config.py في المجلد الرئيسي
                root_config_path = os.path.join(current_dir, 'config.py')
                with open(root_config_path, 'w', encoding='utf-8') as f:
                    f.write('# تكوين البوت\n')
                    f.write('BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # قم بتغيير هذا إلى رمز البوت الخاص بك\n')
                print(f"تم إنشاء ملف {root_config_path}")
                print("يرجى تعديل الملف وإضافة رمز البوت الخاص بك")
                
                import importlib
                import config
                importlib.reload(config)
                from bot import Bot
                TELEGRAM_BOT_TOKEN = config.BOT_TOKEN
                print("تم استيراد BOT_TOKEN من config.py بعد إنشائه")
            except Exception as e3:
                print(f"فشلت جميع محاولات الاستيراد: {e3}")
                sys.exit(1)
    
    if Bot is None or TELEGRAM_BOT_TOKEN is None:
        print("فشل استيراد BOT_TOKEN أو Bot. يرجى التحقق من ملفات التكوين.")
        sys.exit(1)

    return Bot, TELEGRAM_BOT_TOKEN'''

            # Replace the content within the function
            content = content.replace(old_block_str, new_block_str)
            
            with open(main_py_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"تم تحديث دالة import_modules في {main_py_path}")
        else:
            print("لم يتم العثور على دالة import_modules في main.py.")

if __name__ == '__main__':
    bot_token = os.environ.get('BOT_TOKEN_FROM_USER')
    if bot_token:
        fix_bot_token_import(bot_token)
    else:
        print("لم يتم توفير رمز البوت. يرجى تشغيل السكربت مع متغير بيئة BOT_TOKEN_FROM_USER.")


