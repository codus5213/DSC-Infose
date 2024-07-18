import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import io # 메모리 내에서 데이터를 처리하기 위해 사용
import soundfile as sf # 오디오 파일 형식을 읽고 쓰기 위해 사용
import test1

TOKEN = "7111083943:AAGWgpkg1tAGQyEiVmNa35fEVosktgI_aWo"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

CHOOSING = 0
BACK = 1

bot = test1.chatbot_init()

keyboard = [
        [InlineKeyboardButton("질문하기", callback_data='question'),InlineKeyboardButton("종료하기", callback_data='end')],
    ]

markup = InlineKeyboardMarkup(keyboard)

# voice 형식 변환과 데이터와 타입 반환
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.voice: # 음성 파일 일때 wav로 변환 후 파일과 0반환
        try:
            # voice 메시지를 저장
            file_id = update.message.voice.file_id # 음성 파일의 id 얻고
            new_file = await context.bot.get_file(file_id) # 해당 음성 파일을 얻기

            ogg_file = io.BytesIO() # 실제 파일을 열지 않고 메모리 내에서 데이터를 읽고 쓸 수 있게 해줌
            await new_file.download_to_memory(ogg_file)  # 파일을 메모리에 다운로드
            ogg_file.seek(0)  # 파일 포인터를 처음으로 이동

            # ogg 파일을 wav 형식으로 변환
            data, samplerate = sf.read(ogg_file) # 음성 파일의 data, samplerate를 얻고
            wav_file = io.BytesIO() # wav로 변환한 파일을 넣을 메모리를 만들고
            sf.write(wav_file, data, samplerate, format='WAV') # wav형식으로 변환
            wav_file.seek(0) # 파일 포인터를 처음으로 이동

            return wav_file, 0
        except Exception as e: # 처리중 문제가 생기면 에러반환
            logger.error(f"Failed to process voice message: {e}")
            await update.message.reply_text("음성 메시지를 처리하는데 문제가 발생했습니다.")
            return None, -1

    elif update.message.text: # 텍스트일 때 텍스트와 1반환
        text = update.message.text
        print(text)
        return text, 1

    else:
        return None, -1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "안녕? 나는 helpme!야. 궁금한 것이 있니? 나에게 물어봐죵~",
        reply_markup=markup,
    )

    return BACK

async def searching_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    question_path, num = await handle_message(update, context) # 질문 데이터와 형식
    if num != -1:
        query = test1.totext(question_path, num) #검색 키워드 추출
        response, subtopics = bot.respond(query)
        
        if response:
            await update.message.reply_text(response, reply_markup=markup)
        if len(subtopics) > 0:
            sub_keyboard = [[InlineKeyboardButton(subtopic, callback_data=subtopic) for subtopic in subtopics],
                        [InlineKeyboardButton('다른 질문 하기', callback_data='other_question')]]
            reply_markup = InlineKeyboardMarkup(sub_keyboard)
            await update.message.reply_text(
                f"'{bot.selected_topic}'에 대한 더 자세한 설명을 원하시면 추가 키워드를 선택하세요:",
                reply_markup=reply_markup
            )
    else: # 파일이 음성이나 텍스트가 아닐 때
        await update.message.reply_text(
            "음성 메시지나 텍스트를 보내주세요.",
            reply_markup=markup
        )
    return BACK

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_option = query.data
    if selected_option == 'question':
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([]))
        await query.message.reply_text(text="질문을 입력해주세요:", reply_markup=ReplyKeyboardRemove())
        return CHOOSING
    elif selected_option == 'end':
        bot.reset()
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([]))
        await query.message.reply_text(text="궁금증이 잘 해결되었길 바랍니다. 다음에 또 찾아주세요.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    elif selected_option == 'other_question':
        bot.state = 'INITIAL'
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([]))
        await query.message.reply_text(text="다른 질문을 입력해주세요:", reply_markup=ReplyKeyboardRemove())
        return CHOOSING
    else:
        response, _ = bot.respond(selected_option)
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([]))
        await query.message.reply_text(text=response, reply_markup=markup)
        return BACK

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    bot.reset()
    await update.message.reply_text(
        "궁금증이 잘 해결되었길 바라~. 다음에 또 만나",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("helpme", start)],
        states={
            CHOOSING: [
                MessageHandler((filters.TEXT | filters.VOICE) & ~filters.Regex("^(질문하기|종료하기)$"), searching_answer)
            ],
            BACK: [
                CallbackQueryHandler(button)
            ],
        },
        fallbacks=[CallbackQueryHandler(button, pattern='^end$')],
    )

    application.add_handler(conv_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
