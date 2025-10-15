import sqlite3 # Added missing import for subscription requests DB
from datetime import datetime # Added missing import for datetime

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from services.subscription_service import SubscriptionService
from config.config import ADMIN_USER_ID # Import ADMIN_USER_ID

# Optional imports (Keep original structure)
try:
    from services.auth_service import AuthService
    HAS_AUTH_SERVICE = True
except ImportError:
    HAS_AUTH_SERVICE = False
from services.group_service import GroupService
from services.posting_service import PostingService
try:
    from services.response_service import ResponseService
    HAS_RESPONSE_SERVICE = True
except ImportError:
    HAS_RESPONSE_SERVICE = False
try:
    from services.referral_service import ReferralService
    HAS_REFERRAL_SERVICE = True
except ImportError:
    HAS_REFERRAL_SERVICE = False

logger = logging.getLogger(__name__) # Define logger

# Helper function to escape MarkdownV2 characters
def escape_markdown_v2(text: str) -> str:
    if not isinstance(text, str): # Ensure input is a string
        text = str(text)
    # In MarkdownV2, characters _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., ! must be escaped
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    # Escape characters one by one
    for char in escape_chars:
        text = text.replace(char, '\\' + char)
    return text


class StartHelpHandlers:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.subscription_service = SubscriptionService()
        # Keep original service initializations
        if HAS_AUTH_SERVICE:
            self.auth_service = AuthService()
        else:
            self.auth_service = None
        self.group_service = GroupService()
        self.posting_service = PostingService()
        if HAS_RESPONSE_SERVICE:
            self.response_service = ResponseService()
        else:
            self.response_service = None
        if HAS_REFERRAL_SERVICE:
            self.referral_service = ReferralService()
        else:
            self.referral_service = None

        # Register handlers
        self.register_handlers()

    def register_handlers(self):
        # Register start command
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("api_info", self.api_info_command)) # Keep api_info command handler

        # Register callback queries - MODIFIED: Remove help_ pattern
        self.dispatcher.add_handler(CallbackQueryHandler(self.start_help_callback, pattern=r'^(start_|referral_)'))

    # Keep original start_command
    async def start_command(self, update: Update, context: CallbackContext):
        """Handle the /start command with interactive buttons"""
        user = update.effective_user
        user_id = user.id

        # Get or create user in database
        db_user = self.subscription_service.get_user(user_id)
        is_new_user = False # Flag to check if user is new
        if not db_user:
            is_new_user = True # Mark as new user
            db_user = self.subscription_service.create_user(
                user_id,
                user.username,
                user.first_name,
                user.last_name
            )
            # Refetch user data after creation
            db_user = self.subscription_service.get_user(user_id)
        # Check if admin
        is_admin = db_user and db_user.is_admin

        # Welcome message
        welcome_text = f"👋 مرحباً {user.first_name}!\n\n"

        if is_admin:
            welcome_text += "🔰 أنت مسجل كمشرف في النظام.\n\n"

        welcome_text += "🤖 أنا بوت احترافي للنشر التلقائي في مجموعات تيليجرام.\n\n"

        # Check subscription status
        has_subscription = db_user.has_active_subscription()

        # Create keyboard with options (Keep original)
        keyboard = []

        # Always add referral button
        keyboard.append([
            InlineKeyboardButton("🔗 الإحالة", callback_data="start_referral")
        ])

        # Always add trial button
        keyboard.append([
            InlineKeyboardButton("🎁 الحصول على تجربة مجانية (يوم واحد)", callback_data="start_trial")
        ])

        if has_subscription:
            # For subscribed users, add subscription info to text
            if db_user.subscription_end:
                end_date = db_user.subscription_end.strftime("%Y-%m-%d")
                welcome_text += f"✅ لديك اشتراك نشط حتى: {end_date}\n\n"
            else:
                welcome_text += f"✅ لديك اشتراك نشط غير محدود المدة\n\n"
            
            # Add login status check
            session_string = None
            if self.auth_service is not None:
                session_string = self.auth_service.get_user_session(user_id)
            
            if session_string:
                welcome_text += "✅ أنت مسجل يمكنك استعمال بوت\n\n" # User is logged in
            else:
                welcome_text += "⚠️ أنت لم تسجل ولا يمكنك استعمال بوت\n\n" # User is not logged in

        else:
            # For non-subscribed users, add message and subscription request button
            welcome_text += "⚠️ ليس لديك اشتراك نشط.\n\n"
            trial_claimed = db_user.trial_claimed if hasattr(db_user, "trial_claimed") else False
            if trial_claimed:
                 welcome_text += "لقد استخدمت الفترة التجريبية المجانية بالفعل.\n"
            
            # Add subscription request button (linking to admin)
            try:
                admin_chat = await context.bot.get_chat(ADMIN_USER_ID)
                admin_username = admin_chat.username
                button_text = f"🔔 طلب اشتراك (تواصل مع @{admin_username})" if admin_username else "🔔 طلب اشتراك (تواصل مع المشرف)"
            except Exception as e:
                logger.error(f"Error fetching admin username: {e}") # Use logger
                button_text = "🔔 طلب اشتراك (تواصل مع المشرف)" # Fallback on error
            
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data="start_subscription")
            ])

        # Add Usage Info button
        keyboard.append([
            InlineKeyboardButton("ℹ️ معلومات الاستخدام", callback_data="start_usage_info")
        ])

        # Add Posting Commands button
        keyboard.append([
            InlineKeyboardButton("📝 أوامر النشر", callback_data="start_posting_commands")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Use reply_text for commands (Keep original logic)
        if update.message:
             await update.message.reply_text(
                 text=welcome_text,
                 reply_markup=reply_markup
             )
        # Use edit_message_text for callbacks (like start_back)
        elif update.callback_query:
             # This part might be needed if start_command is called from a callback
             await update.callback_query.edit_message_text(
                 text=welcome_text,
                 reply_markup=reply_markup
             )

    async def posting_commands_menu(self, update: Update, context: CallbackContext):
        """Display the posting commands menu."""
        user = update.effective_user
        user_id = user.id
        db_user = self.subscription_service.get_user(user_id)
        is_admin = db_user and db_user.is_admin

        posting_text = "📝 أوامر النشر المتاحة:\n\n"
        keyboard = [
            [InlineKeyboardButton("🔑 أوامر الحساب", callback_data="help_account")],
            [InlineKeyboardButton("👥 أوامر المجموعات", callback_data="help_groups")],
            [InlineKeyboardButton("📝 أوامر النشر", callback_data="help_posting")],
            [InlineKeyboardButton("🤖 أوامر الردود", callback_data="help_responses")],
            [InlineKeyboardButton("🔗 أوامر الإحالات", callback_data="help_referrals")]
        ]

        if is_admin:
            keyboard.append([
                InlineKeyboardButton("👨‍💼 أوامر المشرف", callback_data="help_admin")
            ])

        keyboard.append([
            InlineKeyboardButton("🔙 العودة للبداية", callback_data="start_back")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=posting_text,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=posting_text,
                reply_markup=reply_markup
            )

    async def api_info_command(self, update: Update, context: CallbackContext):
         """Handle the /api_info command to show API session status."""
         info_message = (
             "ℹ️ *معلومات حول API ID و API Hash:*\n\n"
             "للاستفادة من بعض ميزات البوت المتقدمة \\(مثل تسجيل الدخول بحسابك الخاص\\)، ستحتاج إلى `API ID` و `API Hash` الخاصين بك من تيليجرام\\.\n\n"
             "*كيفية الحصول عليها:*\n"
             "1\\. اذهب إلى موقع تيليجرام الرسمي لإدارة التطبيقات: [https://my\\.telegram\\.org/apps](https://my.telegram.org/apps)\n"
             "2\\. قم بتسجيل الدخول باستخدام رقم هاتفك\\.\n"
             "3\\. املأ نموذج 'Create New Application' \\(يمكنك إدخال أي اسم ووصف قصير، مثل 'MyBotApp'\\)\\.\n"
             "4\\. بعد إنشاء التطبيق، ستظهر لك قيم `api_id` و `api_hash`\\. احتفظ بها في مكان آمن ولا تشاركها مع أحد\\.\n\n"
         )

         if self.auth_service is not None:
             info_message += "\\n✅ يدعم هذا البوت تسجيل الدخول باستخدام هذه البيانات عبر الأوامر مثل `/login` أو `/generate_session`\\."
         else:
             info_message += "\\n⚠️ لا يدعم هذا البوت حاليًا تسجيل الدخول المباشر باستخدام API\\."

         await update.message.reply_text(
             info_message,
             parse_mode="MarkdownV2",
             disable_web_page_preview=True
         )

    async def start_help_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "start_back":
            await self.start_command(update, context)
        elif data == "start_posting_commands":
            await self.posting_commands_menu(update, context)
        elif data == "start_referral":
            user = update.effective_user
            user_id = user.id
            referral_link = self.referral_service.generate_referral_link(user_id) if self.referral_service else ""
            referral_count = self.referral_service.get_referral_count(user_id) if self.referral_service else 0

            message_text = (
                f"🔗 *رابط الإحالة الخاص بك:*\n`{referral_link}`\n\n"
                f"عدد الإحالات النشطة: {referral_count}\n\n"
                "شارك هذا الرابط مع أصدقائك للحصول على مزايا إضافية!"
            )
            keyboard = [
                [InlineKeyboardButton("🔙 العودة", callback_data="start_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=escape_markdown_v2(message_text),
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )
        elif data == "start_trial":
            user = update.effective_user
            user_id = user.id
            db_user = self.subscription_service.get_user(user_id)

            if db_user and db_user.trial_claimed:
                admin_username_mention = "المشرف"
                admin_link = ""
                try:
                    admin_chat = await context.bot.get_chat(ADMIN_USER_ID)
                    if admin_chat.username:
                        admin_username_mention = f"@{admin_chat.username}"
                        admin_link = f"https://t.me/{admin_chat.username}"
                    elif admin_chat.first_name:
                        admin_username_mention = admin_chat.first_name
                        admin_link = f"tg://user?id={ADMIN_USER_ID}"
                except Exception as e:
                    logger.error(f"Error fetching admin username: {e}")

                message_text = (
                    f"⚠️ *لقد استمتعت بالفعل بفترتك التجريبية المجانية!* نأمل أنها نالت إعجابك.\n\n"
                    f"للاستمرار في استخدام جميع ميزات البوت، يرجى طلب اشتراك مدفوع.\n\n"
                    f"👇 اضغط على الزر أدناه للتواصل مع المشرف."
                )

                keyboard = []
                if admin_link:
                    keyboard.append([InlineKeyboardButton(f"👇💬 تواصل مع {admin_username_mention}", url=admin_link)])
                else:
                    # If admin link couldn't be fetched, add a note to the message
                    message_text += "\n\n(تعذر جلب رابط التواصل مع المشرف)"

                keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="start_back")])
                reply_markup = InlineKeyboardMarkup(keyboard)

                try:
                    await query.edit_message_text(
                        text=message_text,
                        reply_markup=reply_markup,
                        parse_mode="Markdown" # Use Markdown for bold/italics
                    )
                except Exception as edit_err:
                     logger.error(f"Failed to edit message for trial claimed (Markdown): {edit_err}")
                     # Fallback to plain text if Markdown fails
                     plain_text = (
                         f"⚠️ لقد استمتعت بالفعل بفترتك التجريبية المجانية! نأمل أنها نالت إعجابك.\n\n"
                         f"للاستمرار في استخدام جميع ميزات البوت، يرجى طلب اشتراك مدفوع.\n\n"
                         f"👇 تواصل مع {admin_username_mention}."
                     )
                     # Add note if link failed in plain text too
                     if not admin_link:
                         plain_text += "\n\n(تعذر جلب رابط التواصل مع المشرف)"
                     await query.edit_message_text(
                        text=plain_text,
                        reply_markup=reply_markup # Keep the buttons
                    )

            else:
                # Grant trial
                self.subscription_service.grant_trial(user_id)
                message_text = "✅ تم تفعيل الفترة التجريبية المجانية لمدة يوم واحد! استمتع بميزات البوت.\n\n"
                keyboard = [
                    [InlineKeyboardButton("🔙 العودة", callback_data="start_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text=message_text,
                    reply_markup=reply_markup
                )
        # MODIFIED: start_subscription logic to add request to DB and send two messages
        elif data == "start_subscription":
            user_info = update.effective_user
            user_id = user_info.id
            username = user_info.username
            first_name = user_info.first_name
            last_name = user_info.last_name

            try:
                # 1. Add request to SQLite database
                conn = sqlite3.connect("data/user_statistics.sqlite")
                cursor = conn.cursor()

                # Check for existing pending request
                cursor.execute("SELECT * FROM subscription_requests WHERE user_id = ? AND status = \"pending\"", (user_id,))
                existing_request = cursor.fetchone()

                if existing_request:
                    await query.edit_message_text(
                        text="⚠️ لديك بالفعل طلب اشتراك معلق. يرجى الانتظار حتى يتم معالجته.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]])
                    )
                    conn.close()
                    return
                else:
                    # REMOVED request_time column
                    cursor.execute(
                        """
                        INSERT INTO subscription_requests 
                        (user_id, username, first_name, last_name, status) 
                        VALUES (?, ?, ?, ?, 'pending')
                        """,
                        (user_id, username, first_name, last_name) # Added missing arguments
                    )
                conn.commit()
                conn.close()
                logger.info(f"Subscription request added to DB for user {user_id} via start_handler.")

                # 2. Send first confirmation message (edit)
                await query.edit_message_text(
                    text="✅ تم إرسال طلب الاشتراك الخاص بك إلى المشرف. سيتم التواصل معك قريباً."
                    # Keep the back button from the original logic if needed, or remove reply_markup
                    # reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="start_back")]]) 
                )

                # 3. Fetch admin details for the second message
                admin_username_mention = "المشرف" # Default
                admin_link = ""
                try:
                    admin_chat = await context.bot.get_chat(ADMIN_USER_ID)
                    if admin_chat.username:
                        admin_username_mention = f"@{admin_chat.username}"
                        admin_link = f"https://t.me/{admin_chat.username}"
                    elif admin_chat.first_name:
                        admin_username_mention = admin_chat.first_name
                        admin_link = f"tg://user?id={ADMIN_USER_ID}"
                except Exception as e:
                    logger.error(f"Could not fetch admin details for ID {ADMIN_USER_ID}: {e}")

                # 4. Send the second message (send_message)
                second_message_text = f"يرجى التواصل مع المشرف {admin_username_mention} لأخذ الاشتراك."
                keyboard = None
                reply_markup_second = None # Use a different variable name
                if admin_link:
                    keyboard = [
                        [InlineKeyboardButton(f"👇💬 تواصل مع {admin_username_mention}", url=admin_link)],
                        [InlineKeyboardButton("🔙 العودة", callback_data="start_back")]
                    ]
                    reply_markup_second = InlineKeyboardMarkup(keyboard)
                else:
                    second_message_text += "\n\n(تعذر جلب رابط التواصل مع المشرف)"
                    keyboard = [
                        [InlineKeyboardButton("🔙 العودة", callback_data="start_back")]
                    ]
                    reply_markup_second = InlineKeyboardMarkup(keyboard)

                await context.bot.send_message(
                    chat_id=user_id,
                    text=second_message_text,
                    reply_markup=reply_markup_second,
                    parse_mode="MarkdownV2" # Use MarkdownV2 for consistent parsing
                )

            except Exception as e:
                logger.error(f"Error handling start_subscription callback for user {user_id}: {e}")
                await query.edit_message_text("حدث خطأ أثناء معالجة طلب الاشتراك. يرجى المحاولة مرة أخرى.")

        elif data == "start_usage_info":
            info_text = (
                "ℹ️ *معلومات الاستخدام:*\n\n"
                "هذا البوت مصمم لأتمتة نشر الرسائل في مجموعات تيليجرام.\n\n"
                "*الميزات الرئيسية:*\n"
                "- نشر الرسائل المجدولة\n"
                "- إدارة المجموعات\n"
                "- إحصائيات الاستخدام\n"
                "- دعم الإحالات\n\n"
                "*كيفية البدء:*\n"
                "1. تأكد من أن لديك اشتراكًا نشطًا.\n"
                "2. استخدم `/login` لتسجيل الدخول إلى حساب تيليجرام الخاص بك (إذا لزم الأمر).\n"
                "3. استخدم `/add_group` لإضافة المجموعات التي تريد النشر فيها.\n"
                "4. استخدم `/schedule_post` لجدولة رسائلك.\n\n"
                "*الأوامر المتاحة (يمكنك العثور عليها في قائمة 'أوامر النشر'):*\n"
                "- `/login`: تسجيل الدخول بحساب تيليجرام.\n"
                "- `/logout`: تسجيل الخروج من حساب تيليجرام.\n"
                "- `/check_login`: للتحقق مما إذا كنت مسجلاً للدخول حالياً.\n"
                "- `/add_group`: إضافة مجموعة للنشر فيها.\n"
                "- `/list_groups`: عرض المجموعات المضافة.\n"
                "- `/remove_group`: إزالة مجموعة.\n"
                "- `/schedule_post`: جدولة رسالة للنشر.\n"
                "- `/list_posts`: عرض الرسائل المجدولة.\n"
                "- `/cancel_post`: إلغاء رسالة مجدولة.\n"
                "- `/set_response`: تعيين رد تلقائي.\n"
                "- `/list_responses`: عرض الردود التلقائية.\n"
                "- `/remove_response`: إزالة رد تلقائي.\n"
                "- `/my_referrals`: عرض رابط الإحالة الخاص بك وعدد المستخدمين الذين قاموا بالتسجيل من خلاله.\n"
                "- `/api_info`: معلومات حول API ID و API Hash.\n"
                "- `/broadcast`: (للمشرفين) إرسال رسالة لجميع المستخدمين.\n"
                "- `/stats`: (للمشرفين) عرض إحصائيات البوت.\n"
                "- `/grant_trial`: (للمشرفين) منح فترة تجريبية لمستخدم.\n"
                "- `/grant_subscription`: (للمشرفين) منح اشتراكاً مدفوعاً لمستخدم.\n"
                "- `/revoke_subscription`: (للمشرفين) إلغاء اشتراك مستخدم.\n"
                "- `/list_users`: (للمشرفين) عرض قائمة المستخدمين.\n"
                "- `/list_requests`: (للمشرفين) عرض طلبات الاشتراك المعلقة.\n"
                "- `/approve_request`: (للمشرفين) الموافقة على طلب اشتراك.\n"
                "- `/deny_request <معرف_الطلب>`: لرفض طلب اشتراك.\n"
            )
            keyboard = [
                [InlineKeyboardButton("🔙 العودة", callback_data="start_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=escape_markdown_v2(info_text),
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )

        elif data == "help_account":
            account_help_text = (
                "🔑 *أوامر الحساب:*\n\n"
                "- `/login`: لتسجيل الدخول إلى حساب تيليجرام الخاص بك. هذا يسمح للبوت بالنشر نيابة عنك في المجموعات.\n"
                "- `/logout`: لتسجيل الخروج من حساب تيليجرام الخاص بك.\n"
                "- `/check_login`: للتحقق مما إذا كنت مسجلاً للدخول حالياً.\n"
            )
            keyboard = [
                [InlineKeyboardButton("🔙 العودة لأوامر النشر", callback_data="start_posting_commands")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=escape_markdown_v2(account_help_text),
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )

        elif data == "help_groups":
            groups_help_text = (
                "👥 *أوامر المجموعات:*\n\n"
                "- `/add_group <معرف_المجموعة>`: لإضافة مجموعة للنشر فيها. يمكنك الحصول على معرف المجموعة من خلال إعادة توجيه رسالة من المجموعة إلى @RawDataBot.\n"
                "- `/list_groups`: لعرض جميع المجموعات التي أضفتها.\n"
                "- `/remove_group <معرف_المجموعة>`: لإزالة مجموعة من قائمة النشر.\n"
            )
            keyboard = [
                [InlineKeyboardButton("🔙 العودة لأوامر النشر", callback_data="start_posting_commands")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=escape_markdown_v2(groups_help_text),
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )

        elif data == "help_posting":
            posting_help_text = (
                "📝 *أوامر النشر:*\n\n"
                "- `/schedule_post <معرف_المجموعة> <وقت_النشر> <الرسالة>`: لجدولة رسالة ليتم نشرها في مجموعة محددة في وقت معين. مثال: `/schedule_post -1001234567890 2025-12-31 14:30 مرحباً بكم في مجموعتنا!`\n"
                "- `/list_posts`: لعرض جميع الرسائل المجدولة.\n"
                "- `/cancel_post <معرف_الرسالة>`: لإلغاء رسالة مجدولة باستخدام معرف الرسالة.\n"
            )
            keyboard = [
                [InlineKeyboardButton("🔙 العودة لأوامر النشر", callback_data="start_posting_commands")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=escape_markdown_v2(posting_help_text),
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )

        elif data == "help_responses":
            responses_help_text = (
                "🤖 *أوامر الردود التلقائية:*\n\n"
                "- `/set_response <الكلمة_المفتاحية> <الرد>`: لتعيين رد تلقائي عندما يذكر المستخدم كلمة مفتاحية معينة في مجموعة. مثال: `/set_response مرحباً أهلاً بك!`\n"
                "- `/list_responses`: لعرض جميع الردود التلقائية المعينة.\n"
                "- `/remove_response <الكلمة_المفتاحية>`: لإزالة رد تلقائي.\n"
            )
            keyboard = [
                [InlineKeyboardButton("🔙 العودة لأوامر النشر", callback_data="start_posting_commands")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=escape_markdown_v2(responses_help_text),
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )

        elif data == "help_referrals":
            referrals_help_text = (
                "🔗 *أوامر الإحالات:*\n\n"
                "- `/my_referrals`: لعرض رابط الإحالة الخاص بك وعدد المستخدمين الذين قاموا بالتسجيل من خلاله.\n"
                "- `/set_referral_bonus <المبلغ>`: (للمشرفين) لتعيين مكافأة الإحالة.\n"
            )
            keyboard = [
                [InlineKeyboardButton("🔙 العودة لأوامر النشر", callback_data="start_posting_commands")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=escape_markdown_v2(referrals_help_text),
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )

        elif data == "help_admin":
            admin_help_text = (
                "👨‍💼 *أوامر المشرف:*\n\n"
                "- `/broadcast <الرسالة>`: لإرسال رسالة لجميع مستخدمي البوت.\n"
                "- `/stats`: لعرض إحصائيات استخدام البوت.\n"
                "- `/grant_trial <معرف_المستخدم>`: لمنح مستخدم فترة تجريبية مجانية.\n"
                "- `/grant_subscription <معرف_المستخدم> <المدة_بالأيام>`: لمنح مستخدم اشتراكاً مدفوعاً.\n"
                "- `/revoke_subscription <معرف_المستخدم>`: لإلغاء اشتراك مستخدم.\n"
                "- `/list_users`: لعرض قائمة بجميع مستخدمي البوت.\n"
                "- `/list_requests`: لعرض طلبات الاشتراك المعلقة.\n"
                "- `/approve_request <معرف_الطلب>`: للموافقة على طلب اشتراك.\n"
                "- `/deny_request <معرف_الطلب>`: لرفض طلب اشتراك.\n"
            )
            keyboard = [
                [InlineKeyboardButton("🔙 العودة لأوامر النشر", callback_data="start_posting_commands")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=escape_markdown_v2(admin_help_text),
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )

