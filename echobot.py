#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import os

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ApplicationBuilder

IMAGE_FOLDER="images"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Use /help command for usage.",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_html(
        """The bot expects to receive two images and sends result of <a href="https://en.wikipedia.org/wiki/Neural_style_transfer">NST</a> in return. The first image will be used as a content image, the second - as a style one."""
        )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)

async def nst(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Perform NST using images in the message."""
    file_path = await download_image(update, context)
    await update.message.reply_text("NST triggered")

async def download_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Helper for downloading images"""
    bot = context.bot
    image = await bot.getFile(update.message.photo[-1].file_id)
    extenstion = os.path.splitext(image.file_path)[-1]
    file_path = f"{IMAGE_FOLDER}/{image.file_unique_id}{extenstion}"
    await image.download_to_drive(custom_path=file_path)
    return file_path


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    token = os.environ["TG_BOT_TOKEN"]
    application = Application.builder().token(token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command text messages - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # on messages containing an image - perform NST
    application.add_handler(MessageHandler(filters.PHOTO, nst))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()