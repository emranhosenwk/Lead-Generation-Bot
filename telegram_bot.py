import os
import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from groq import Groq

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID", "")  # Your Telegram ID to receive leads

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
groq_client = Groq(api_key=GROQ_API_KEY)

# ===== CUSTOMIZE FOR CLIENT =====
BUSINESS = {
    "name": "Digital Growth Agency",
    "type": "digital marketing agency",
    "services": ["SEO Optimization", "Social Media Marketing", "Web Design", "PPC Advertising", "Content Marketing"],
    "offer": "FREE Website Audit worth $200",
    "contact": "+1-800-GROW-BIZ",
    "email": "hello@digitalgrowth.com",
    "response_time": "2 hours",
}
# ================================

leads_db = []
user_data = {}
user_histories = {}

async def notify_owner(context, lead):
    if not OWNER_CHAT_ID:
        return
    text = f"🎯 *NEW LEAD RECEIVED!*\n\n"
    text += f"👤 Name: {lead.get('name', 'N/A')}\n"
    text += f"📧 Email: {lead.get('email', 'N/A')}\n"
    text += f"📞 Phone: {lead.get('phone', 'N/A')}\n"
    text += f"🎯 Service: {lead.get('service', 'N/A')}\n"
    text += f"💬 Message: {lead.get('message', 'N/A')}\n"
    text += f"🕐 Time: {lead.get('time', 'N/A')}"
    try:
        await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=text, parse_mode="Markdown")
    except:
        pass

async def get_ai_response(user_id, message):
    if user_id not in user_histories:
        user_histories[user_id] = []

    system = f"""You are a friendly sales assistant for {BUSINESS['name']}, a {BUSINESS['type']}.

Services: {', '.join(BUSINESS['services'])}
Special Offer: {BUSINESS['offer']}

Your goals:
1. Answer questions about the business and services
2. Build rapport and understand the visitor's needs
3. Gently guide them toward leaving contact info
4. Be friendly, helpful and professional
5. Keep responses concise (2-3 sentences)
6. Respond in same language as the user"""

    user_histories[user_id].append({"role": "user", "content": message})
    if len(user_histories[user_id]) > 10:
        user_histories[user_id] = user_histories[user_id][-10:]

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system}, *user_histories[user_id]],
        max_tokens=256,
        temperature=0.7,
    )

    reply = response.choices[0].message.content
    user_histories[user_id].append({"role": "assistant", "content": reply})
    return reply

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("💼 Our Services", callback_data="services"),
         InlineKeyboardButton("💰 Get Pricing", callback_data="pricing")],
        [InlineKeyboardButton("🎁 Free Audit", callback_data="free_offer"),
         InlineKeyboardButton("📞 Contact Us", callback_data="contact")],
        [InlineKeyboardButton("💬 Ask a Question", callback_data="ask")],
    ]

    await update.message.reply_text(
        f"👋 *Hi {user.first_name}! Welcome to {BUSINESS['name']}!*\n\n"
        f"We help businesses grow with:\n" +
        "\n".join([f"✅ {s}" for s in BUSINESS['services']]) +
        f"\n\n🎁 *Special Offer:* {BUSINESS['offer']}\n\n"
        f"_How can I help you today?_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "services":
        text = f"💼 *Our Services*\n\n"
        for s in BUSINESS['services']:
            text += f"✅ *{s}*\n"
        text += f"\n_Which service interests you most?_"
        keyboard = [[InlineKeyboardButton(s[:30], callback_data=f"svc_{s}")] for s in BUSINESS['services']]
        keyboard.append([InlineKeyboardButton("🎁 Get Free Consultation", callback_data="free_offer")])
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("svc_"):
        service = data.replace("svc_", "")
        user_data[user_id] = {"service": service}
        keyboard = [
            [InlineKeyboardButton("🎁 Yes! Get Free Audit", callback_data="free_offer")],
            [InlineKeyboardButton("💬 Ask a Question", callback_data="ask")],
        ]
        await query.message.edit_text(
            f"Great choice! 🚀\n\n*{service}* is one of our most popular services!\n\n"
            f"We've helped 500+ businesses with {service}.\n\n"
            f"Want a *FREE audit* of your current {service} strategy?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "pricing":
        keyboard = [
            [InlineKeyboardButton("🎁 Get Custom Quote", callback_data="free_offer")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")],
        ]
        await query.message.edit_text(
            f"💰 *Our Pricing*\n\n"
            f"We offer custom pricing based on your specific needs and goals.\n\n"
            f"To give you an accurate quote:\n"
            f"✅ It's completely FREE\n"
            f"✅ No obligation\n"
            f"✅ Response within {BUSINESS['response_time']}\n\n"
            f"Click below to get your free quote! 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "free_offer":
        user_data[user_id] = user_data.get(user_id, {})
        user_data[user_id]['stage'] = 'collecting_name'
        await query.message.edit_text(
            f"🎁 *{BUSINESS['offer']}*\n\n"
            f"Just a few quick questions to get started!\n\n"
            f"👤 *What's your name?*",
            parse_mode="Markdown"
        )

    elif data == "contact":
        keyboard = [
            [InlineKeyboardButton("🎁 Get Free Consultation", callback_data="free_offer")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")],
        ]
        await query.message.edit_text(
            f"📞 *Contact {BUSINESS['name']}*\n\n"
            f"📱 Phone: {BUSINESS['contact']}\n"
            f"📧 Email: {BUSINESS['email']}\n"
            f"⏰ Response time: Within {BUSINESS['response_time']}\n\n"
            f"Or let us contact you! Get a FREE consultation 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "ask":
        user_data[user_id] = user_data.get(user_id, {})
        user_data[user_id]['stage'] = 'chatting'
        await query.message.reply_text(
            "💬 *Ask me anything!*\n\nI'm here to help 👇",
            parse_mode="Markdown"
        )

    elif data == "back_home":
        keyboard = [
            [InlineKeyboardButton("💼 Our Services", callback_data="services"),
             InlineKeyboardButton("💰 Get Pricing", callback_data="pricing")],
            [InlineKeyboardButton("🎁 Free Audit", callback_data="free_offer"),
             InlineKeyboardButton("📞 Contact Us", callback_data="contact")],
            [InlineKeyboardButton("💬 Ask a Question", callback_data="ask")],
        ]
        await query.message.edit_text(
            f"🏠 *{BUSINESS['name']} — Main Menu*\n\n_How can I help you?_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text.strip()
    data = user_data.get(user_id, {})
    stage = data.get('stage', 'chatting')

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Lead collection flow
    if stage == 'collecting_name':
        user_data[user_id]['name'] = message
        user_data[user_id]['stage'] = 'collecting_email'
        await update.message.reply_text(
            f"Nice to meet you, *{message}*! 😊\n\n📧 *What's your email address?*",
            parse_mode="Markdown"
        )

    elif stage == 'collecting_email':
        user_data[user_id]['email'] = message
        user_data[user_id]['stage'] = 'collecting_phone'
        await update.message.reply_text(
            f"Perfect! 📱 *What's your phone number?*\n\n_(Optional — type 'skip' to skip)_",
            parse_mode="Markdown"
        )

    elif stage == 'collecting_phone':
        user_data[user_id]['phone'] = message if message.lower() != 'skip' else 'Not provided'
        user_data[user_id]['stage'] = 'collecting_message'
        await update.message.reply_text(
            f"Almost done! 💬 *Briefly describe what you need help with:*",
            parse_mode="Markdown"
        )

    elif stage == 'collecting_message':
        user_data[user_id]['message'] = message
        user_data[user_id]['stage'] = 'done'
        user_data[user_id]['time'] = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Save lead
        lead = user_data[user_id].copy()
        leads_db.append(lead)

        # Notify owner
        await notify_owner(context, lead)

        keyboard = [
            [InlineKeyboardButton("💬 Ask a Question", callback_data="ask")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back_home")],
        ]

        await update.message.reply_text(
            f"🎉 *Thank you, {lead.get('name')}!*\n\n"
            f"✅ Your request has been received!\n"
            f"📧 We'll email you at: {lead.get('email')}\n"
            f"⏰ Expected response: within *{BUSINESS['response_time']}*\n\n"
            f"Is there anything else I can help you with?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    else:
        # General AI chat
        try:
            reply = await get_ai_response(user_id, message)
            keyboard = [
                [InlineKeyboardButton("🎁 Get Free Consultation", callback_data="free_offer")],
            ]
            await update.message.reply_text(
                reply,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            await update.message.reply_text("Sorry, something went wrong. Please try again!")

# Leads command (for owner)
async def view_leads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not leads_db:
        return await update.message.reply_text("📊 No leads yet!")

    text = f"📊 *All Leads ({len(leads_db)})*\n\n"
    for i, lead in enumerate(leads_db, 1):
        text += f"{i}. *{lead.get('name')}*\n"
        text += f"   📧 {lead.get('email')}\n"
        text += f"   📞 {lead.get('phone')}\n"
        text += f"   🎯 {lead.get('service', 'General')}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leads", view_leads))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🎯 Lead Generation Bot running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
