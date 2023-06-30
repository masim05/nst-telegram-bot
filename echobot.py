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
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html")

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ApplicationBuilder


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO)
logger = logging.getLogger(__name__)


IMAGE_FOLDER = "images"
logger.info(f"Using IMAGE_FOLDER={IMAGE_FOLDER}.")


NST_REQUEST_NEW = "NEW"
NST_REQUEST_CONTENT_IMAGE_ASSIGNED = "CONTENT_IMAGE_ASSIGNED"
NST_REQUEST_STYLE_IMAGE_ASSIGNED = "STYLE_IMAGE_ASSIGNED"
NST_REQUEST_IN_TRANSFER = "IN_TRANSFER"
NST_REQUEST_DONE = "DONE"


class NSTRequest():
    status = NST_REQUEST_NEW
    content_image_path = ""
    style_image_path = ""
    generated_image_path = ""

    async def assign_image(self, image_path) -> None:
        print("assign_image")
        if not self.is_eligible_for_image_assignment():
            raise RuntimeError("assign_image was called when not eligible")

        if self.status == NST_REQUEST_NEW:
            self.content_image_path = image_path
            self.status = NST_REQUEST_CONTENT_IMAGE_ASSIGNED

        elif self.status == NST_REQUEST_CONTENT_IMAGE_ASSIGNED:
            self.style_image_path = image_path
            self.status = NST_REQUEST_STYLE_IMAGE_ASSIGNED
            await self.transfer_style()

    async def transfer_style(self):
        print("transfer_style")
        if self.status != NST_REQUEST_STYLE_IMAGE_ASSIGNED:
            raise RuntimeError(
                "transfer_style was called on not NST_REQUEST_STYLE_IMAGE_ASSIGNED")
        self.status = NST_REQUEST_IN_TRANSFER
        # do style transfer and assign self.generated_image_path

    def get_generated_image_path(self) -> str:
        print("get_generated_image_path")
        if self.status != NST_REQUEST_DONE:
            raise RuntimeError(
                "transfer_style was called on not NST_REQUEST_DONE")
        return self.generated_image_path

    def is_eligible_for_image_assignment(self) -> bool:
        print("get_generated_image_path")
        return (self.status == NST_REQUEST_NEW) or (
            self.status == NST_REQUEST_CONTENT_IMAGE_ASSIGNED)


USERS_REQUESTS = {}


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Use /help command for usage. Use /debug command for checking parameters.",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_html(
        """The bot expects to receive two images and sends result of <a href="https://en.wikipedia.org/wiki/Neural_style_transfer">NST</a> in return. The first image will be used as a content image, the second - as a style one."""
    )

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /debug is issued."""
    await update.message.reply_text(f"IMAGE_SIZE={IMAGE_SIZE}, USERS_REQUESTS={USERS_REQUESTS}")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)


async def nst(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Perform NST using images in the message."""
    image_path = await download_image(update, context)
    key = update.effective_user.id

    if not USERS_REQUESTS.get(key):
        USERS_REQUESTS[key] = [NSTRequest()]

    if not USERS_REQUESTS.get(key)[-1].is_eligible_for_image_assignment():
        USERS_REQUESTS[key].append(NSTRequest())

    last_eligible_user_request = USERS_REQUESTS[key][-1]
    await last_eligible_user_request.assign_image(image_path)

    await update.message.reply_text(f"Your request is in {last_eligible_user_request.status} status")


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
    application.add_handler(CommandHandler("debug", debug_command))

    # on non command text messages - echo the message on Telegram
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            echo))

    # on messages containing an image - perform NST
    application.add_handler(MessageHandler(filters.PHOTO, nst))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
