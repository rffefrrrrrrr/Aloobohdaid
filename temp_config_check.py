import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN_FROM_ENV = os.getenv("BOT_TOKEN")

if BOT_TOKEN_FROM_ENV:
    print(f"BOT_TOKEN تم قراءته من المتغيرات البيئية: {BOT_TOKEN_FROM_ENV[:5]}...{BOT_TOKEN_FROM_ENV[-5:]}")
else:
    print("BOT_TOKEN لم يتم العثور عليه في المتغيرات البيئية. سيتم استخدام القيمة الافتراضية من الملف.")

# يمكنك إضافة المزيد من التحقق هنا إذا لزم الأمر


