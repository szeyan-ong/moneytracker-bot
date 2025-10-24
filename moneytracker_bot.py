from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
from datetime import date, timedelta
import json
import os

from dotenv import load_dotenv
import os

load_dotenv()  # loads .env file automatically
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ Telegram bot token not found. Check your .env file.")

# -------------------- Data storage --------------------
DATA_FILE = "expenses.json"

# Structure: {user_id: {date_str: [(name, amount, category), ...]}}
expenses = {}

# Load expenses from file if exists
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        expenses = json.load(f)
        # JSON stores numbers as float but keys are strings, we may need conversion later

# Categories
CATEGORIES = ["Food", "Drinks", "Entertainment", "Misc.", "Transport", "Travel", "Housing"]

# -------------------- Helper functions --------------------
def save_expenses():
    with open(DATA_FILE, "w") as f:
        json.dump(expenses, f)

def get_user_data(user_id):
    today_str = str(date.today())
    user_data = expenses.get(str(user_id), {})
    return user_data.get(today_str, [])

def format_summary(expense_list):
    total = sum(amount for _, amount, _ in expense_list)
    lines = [f"{name}: ${amount:.2f} ({category})" for name, amount, category in expense_list]
    return "\n".join(lines) + f"\n\n💰 Total: ${total:.2f}"

def add_expense_to_data(user_id, name, amount, category):
    user_id = str(user_id)
    today_str = str(date.today())
    if user_id not in expenses:
        expenses[user_id] = {}
    if today_str not in expenses[user_id]:
        expenses[user_id][today_str] = []
    expenses[user_id][today_str].append((name, amount, category))
    save_expenses()

# -------------------- Command Handlers --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to MoneyTracker Bot!\n\n"
        "Send me an expense like:\ncoffee 5\nlunch 12.50\n\n"
        "Commands:\n"
        "/summary - Today's expenses\n"
        "/week - Weekly summary\n"
        "/month - Monthly daily totals\n"
        "/month_category - Monthly category summary\n"
        "/undo - Remove last entry"
    )

# -------------------- Add Expense --------------------
async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip().split()
    if len(text) < 2:
        await update.message.reply_text("⚠️ Please enter in format: name amount")
        return
    try:
        name = " ".join(text[:-1])
        amount = float(text[-1])
    except ValueError:
        await update.message.reply_text("⚠️ Amount must be a number.")
        return

    # Save temporarily in context
    context.user_data['pending_expense'] = (name, amount)

    # Show category buttons
    keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in CATEGORIES]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Select a category for \"{name} - ${amount:.2f}\":", reply_markup=reply_markup)

async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data

    if 'pending_expense' not in context.user_data:
        await query.edit_message_text("⚠️ No pending expense found.")
        return

    name, amount = context.user_data.pop('pending_expense')
    user_id = query.from_user.id
    add_expense_to_data(user_id, name, amount, category)

    today_expenses = get_user_data(user_id)
    summary_text = format_summary(today_expenses)
    await query.edit_message_text(
        f"✅ Recorded: {name} - ${amount:.2f} ({category})\n\n🧾 Today's summary:\n{summary_text}"
    )

# -------------------- Undo --------------------
async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    today_str = str(date.today())
    today_expenses = expenses.get(user_id, {}).get(today_str, [])
    if not today_expenses:
        await update.message.reply_text("⚠️ No expenses to undo today.")
        return
    removed = today_expenses.pop()
    save_expenses()
    summary_text = format_summary(today_expenses) if today_expenses else "No expenses today."
    await update.message.reply_text(
        f"✅ Removed last entry: {removed[0]} - ${removed[1]:.2f} ({removed[2]})\n\n🧾 Updated summary:\n{summary_text}"
    )

# -------------------- Summaries --------------------
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    today_expenses = get_user_data(user_id)
    if not today_expenses:
        await update.message.reply_text("No expenses today.")
        return
    summary_text = format_summary(today_expenses)
    await update.message.reply_text(f"🧾 Today's summary:\n{summary_text}")

async def week_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_data = expenses.get(user_id, {})
    lines = []
    total_week = 0
    for i in range(7):
        day = date.today() - timedelta(days=i)
        day_str = str(day)
        day_expenses = user_data.get(day_str, [])
        day_total = sum(amount for _, amount, _ in day_expenses)
        total_week += day_total
        lines.append(f"{day}: ${day_total:.2f}")
    summary_text = "\n".join(lines) + f"\n\n💰 Total week: ${total_week:.2f}"
    await update.message.reply_text(f"🧾 Weekly summary:\n{summary_text}")

# -------------------- Monthly daily totals --------------------
async def month_daily_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_data = expenses.get(user_id, {})
    today = date.today()
    
    daily_totals = []
    total_month = 0
    for day_str, day_expenses in sorted(user_data.items()):
        day_date = date.fromisoformat(day_str)
        if day_date.month == today.month and day_date.year == today.year:
            day_total = sum(amount for _, amount, _ in day_expenses)
            daily_totals.append(f"{day_str}: ${day_total:.2f}")
            total_month += day_total

    if not daily_totals:
        await update.message.reply_text("No expenses recorded this month.")
        return

    summary_text = "\n".join(daily_totals)
    summary_text += f"\n\n💰 Total month: ${total_month:.2f}"
    await update.message.reply_text(f"🧾 Monthly daily summary:\n{summary_text}")

# -------------------- Monthly category summary --------------------
async def month_category_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_data = expenses.get(user_id, {})
    today = date.today()

    category_totals = {}
    total_month = 0
    for day_str, day_expenses in user_data.items():
        day_date = date.fromisoformat(day_str)
        if day_date.month == today.month and day_date.year == today.year:
            for _, amount, category in day_expenses:
                category_totals[category] = category_totals.get(category, 0) + amount
                total_month += amount

    if total_month == 0:
        await update.message.reply_text("No expenses recorded this month.")
        returnpy

    lines = []
    for cat, amt in category_totals.items():
        percent = (amt / total_month) * 100
        lines.append(f"{cat}: ${amt:.2f} ({percent:.1f}%)")

    summary_text = "\n".join(lines)
    summary_text += f"\n\n💰 Total month: ${total_month:.2f}"
    await update.message.reply_text(f"🧾 Monthly category summary:\n{summary_text}")

# -------------------- Main --------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense))
    app.add_handler(CallbackQueryHandler(category_selected))
    app.add_handler(CommandHandler("undo", undo))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("week", week_summary))
    app.add_handler(CommandHandler("month", month_daily_summary))
    app.add_handler(CommandHandler("month_category", month_category_summary))

    print("✅ MoneyTracker Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()





# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
# from datetime import date, timedelta
# import json
# import os

# # -------------------- Data storage --------------------
# DATA_FILE = "expenses.json"

# # Structure: {user_id: {date_str: [(name, amount, category), ...]}}
# expenses = {}

# # Load expenses from file if exists
# if os.path.exists(DATA_FILE):
#     with open(DATA_FILE, "r") as f:
#         expenses = json.load(f)
#         # JSON stores numbers as float but keys are strings, we may need conversion later

# # Categories
# CATEGORIES = ["Food", "Drinks", "Entertainment", "Misc.", "Transport", "Travel", "Housing"]

# # -------------------- Helper functions --------------------
# def save_expenses():
#     with open(DATA_FILE, "w") as f:
#         json.dump(expenses, f)

# def get_user_data(user_id):
#     today_str = str(date.today())
#     user_data = expenses.get(str(user_id), {})
#     return user_data.get(today_str, [])

# def format_summary(expense_list):
#     total = sum(amount for _, amount, _ in expense_list)
#     lines = [f"{name}: ${amount:.2f} ({category})" for name, amount, category in expense_list]
#     return "\n".join(lines) + f"\n\n💰 Total: ${total:.2f}"

# def add_expense_to_data(user_id, name, amount, category):
#     user_id = str(user_id)
#     today_str = str(date.today())
#     if user_id not in expenses:
#         expenses[user_id] = {}
#     if today_str not in expenses[user_id]:
#         expenses[user_id][today_str] = []
#     expenses[user_id][today_str].append((name, amount, category))
#     save_expenses()

# # -------------------- Command Handlers --------------------
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text(
#         "👋 Welcome to MoneyTracker Bot!\n\n"
#         "Send me an expense like:\ncoffee 5\nlunch 12.50\n\n"
#         "Commands:\n"
#         "/summary - Today's expenses\n"
#         "/week - Weekly summary\n"
#         "/month - Monthly daily totals\n"
#         "/month_category - Monthly category summary\n"
#         "/undo - Remove last entry"
#     )

# # -------------------- Add Expense --------------------
# async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_id = update.message.from_user.id
#     text = update.message.text.strip().split()
#     if len(text) < 2:
#         await update.message.reply_text("⚠️ Please enter in format: name amount")
#         return
#     try:
#         name = " ".join(text[:-1])
#         amount = float(text[-1])
#     except ValueError:
#         await update.message.reply_text("⚠️ Amount must be a number.")
#         return

#     # Save temporarily in context
#     context.user_data['pending_expense'] = (name, amount)

#     # Show category buttons
#     keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in CATEGORIES]
#     reply_markup = InlineKeyboardMarkup(keyboard)
#     await update.message.reply_text(f"Select a category for \"{name} - ${amount:.2f}\":", reply_markup=reply_markup)

# async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()
#     category = query.data

#     if 'pending_expense' not in context.user_data:
#         await query.edit_message_text("⚠️ No pending expense found.")
#         return

#     name, amount = context.user_data.pop('pending_expense')
#     user_id = query.from_user.id
#     add_expense_to_data(user_id, name, amount, category)

#     today_expenses = get_user_data(user_id)
#     summary_text = format_summary(today_expenses)
#     await query.edit_message_text(
#         f"✅ Recorded: {name} - ${amount:.2f} ({category})\n\n🧾 Today's summary:\n{summary_text}"
#     )

# # -------------------- Undo --------------------
# async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_id = str(update.message.from_user.id)
#     today_str = str(date.today())
#     today_expenses = expenses.get(user_id, {}).get(today_str, [])
#     if not today_expenses:
#         await update.message.reply_text("⚠️ No expenses to undo today.")
#         return
#     removed = today_expenses.pop()
#     save_expenses()
#     summary_text = format_summary(today_expenses) if today_expenses else "No expenses today."
#     await update.message.reply_text(
#         f"✅ Removed last entry: {removed[0]} - ${removed[1]:.2f} ({removed[2]})\n\n🧾 Updated summary:\n{summary_text}"
#     )

# # -------------------- Summaries --------------------
# async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_id = update.message.from_user.id
#     today_expenses = get_user_data(user_id)
#     if not today_expenses:
#         await update.message.reply_text("No expenses today.")
#         return
#     summary_text = format_summary(today_expenses)
#     await update.message.reply_text(f"🧾 Today's summary:\n{summary_text}")

# async def week_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_id = str(update.message.from_user.id)
#     user_data = expenses.get(user_id, {})
#     lines = []
#     total_week = 0
#     for i in range(7):
#         day = date.today() - timedelta(days=i)
#         day_str = str(day)
#         day_expenses = user_data.get(day_str, [])
#         day_total = sum(amount for _, amount, _ in day_expenses)
#         total_week += day_total
#         lines.append(f"{day}: ${day_total:.2f}")
#     summary_text = "\n".join(lines) + f"\n\n💰 Total week: ${total_week:.2f}"
#     await update.message.reply_text(f"🧾 Weekly summary:\n{summary_text}")

# # -------------------- Monthly daily totals --------------------
# async def month_daily_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_id = str(update.message.from_user.id)
#     user_data = expenses.get(user_id, {})
#     today = date.today()
    
#     daily_totals = []
#     total_month = 0
#     for day_str, day_expenses in sorted(user_data.items()):
#         day_date = date.fromisoformat(day_str)
#         if day_date.month == today.month and day_date.year == today.year:
#             day_total = sum(amount for _, amount, _ in day_expenses)
#             daily_totals.append(f"{day_str}: ${day_total:.2f}")
#             total_month += day_total

#     if not daily_totals:
#         await update.message.reply_text("No expenses recorded this month.")
#         return

#     summary_text = "\n".join(daily_totals)
#     summary_text += f"\n\n💰 Total month: ${total_month:.2f}"
#     await update.message.reply_text(f"🧾 Monthly daily summary:\n{summary_text}")

# # -------------------- Monthly category summary --------------------
# async def month_category_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_id = str(update.message.from_user.id)
#     user_data = expenses.get(user_id, {})
#     today = date.today()

#     category_totals = {}
#     total_month = 0
#     for day_str, day_expenses in user_data.items():
#         day_date = date.fromisoformat(day_str)
#         if day_date.month == today.month and day_date.year == today.year:
#             for _, amount, category in day_expenses:
#                 category_totals[category] = category_totals.get(category, 0) + amount
#                 total_month += amount

#     if total_month == 0:
#         await update.message.reply_text("No expenses recorded this month.")
#         return

#     lines = []
#     for cat, amt in category_totals.items():
#         percent = (amt / total_month) * 100
#         lines.append(f"{cat}: ${amt:.2f} ({percent:.1f}%)")

#     summary_text = "\n".join(lines)
#     summary_text += f"\n\n💰 Total month: ${total_month:.2f}"
#     await update.message.reply_text(f"🧾 Monthly category summary:\n{summary_text}")

# # -------------------- Main --------------------
# def main():
#     app = ApplicationBuilder().token("8286131877:AAFZ2QnfQTdkATXPaiT-Q1lJbSFK9uELhps").build()

#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense))
#     app.add_handler(CallbackQueryHandler(category_selected))
#     app.add_handler(CommandHandler("undo", undo))
#     app.add_handler(CommandHandler("summary", summary))
#     app.add_handler(CommandHandler("week", week_summary))
#     app.add_handler(CommandHandler("month", month_daily_summary))
#     app.add_handler(CommandHandler("month_category", month_category_summary))

#     print("✅ MoneyTracker Bot is running...")
#     app.run_polling()

# if __name__ == "__main__":
#     main()
