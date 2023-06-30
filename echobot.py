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
import uuid

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

import matplotlib.pyplot as plt
from torchvision.utils import save_image
import torch.optim as optim
import torchvision.models as models
import torch.nn as nn
from PIL import Image
import torchvision.transforms as transforms
import torch
IMAGE_SIZE = os.getenv('IMAGE_SIZE', 128)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO)
logger = logging.getLogger(__name__)


device_tag = 'cuda' if torch.cuda.is_available() else 'cpu'
logger.info(f"Using device={device_tag}.")
device = torch.device(device_tag)

IMAGE_FOLDER = "images"
logger.info(f"Using IMAGE_FOLDER={IMAGE_FOLDER}.")

EPOCHS = 500
LR = 0.004
ALPHA = 8
BETA = 70
logger.info(f"Using EPOCHS={EPOCHS}, LR={LR}, ALPHA={ALPHA}, BETA={BETA}.")


def calc_content_loss(gen_feat, orig_feat):
    # calculating the content loss of each layer by calculating the MSE
    # between the content and generated features and adding it to content loss
    content_l = torch.mean((gen_feat - orig_feat)**2)  # *0.5
    return content_l


def calc_style_loss(gen, style):
    # Calculating the gram matrix for the style and the generated image
    batch_size, channel, height, width = gen.shape

    G = torch.mm(
        gen.view(
            channel,
            height *
            width),
        gen.view(
            channel,
            height *
            width).t())
    A = torch.mm(
        style.view(
            channel,
            height *
            width),
        style.view(
            channel,
            height *
            width).t())

    # Calcultating the style loss of each layer by calculating the MSE between
    # the gram matrix of the style image and the generated image and adding it
    # to style loss
    style_l = torch.mean((G - A)**2)  # /(4*channel*(height*width)**2)
    return style_l


def calculate_loss(gen_features, orig_feautes, style_featues):
    style_loss = content_loss = 0
    for gen, cont, style in zip(gen_features, orig_feautes, style_featues):
        # extracting the dimensions from the generated image
        content_loss += calc_content_loss(gen, cont)
        style_loss += calc_style_loss(gen, style)

    # calculating the total loss of e th epoch
    total_loss = ALPHA * content_loss + BETA * style_loss
    return total_loss


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

    def __repr__(self) -> str:
        return f"""status={self.status}, content_image_path={self.content_image_path}, style_image_path={self.style_image_path}, generated_image_path={self.generated_image_path}\n"""

    async def assign_image(self, image_path) -> None:
        if not self.is_eligible_for_image_assignment():
            raise RuntimeError("assign_image was called when not eligible")

        if self.status == NST_REQUEST_NEW:
            self.content_image_path = image_path
            self.status = NST_REQUEST_CONTENT_IMAGE_ASSIGNED

        elif self.status == NST_REQUEST_CONTENT_IMAGE_ASSIGNED:
            self.style_image_path = image_path
            self.status = NST_REQUEST_STYLE_IMAGE_ASSIGNED

    async def transfer_style(self) -> None:
        if not self.is_eligible_for_transfer():
            raise RuntimeError(
                "transfer_style was called on not NST_REQUEST_STYLE_IMAGE_ASSIGNED")

        self.status = NST_REQUEST_IN_TRANSFER
        self.generated_image_path = f"{IMAGE_FOLDER}/{uuid.uuid1()}.png"

        # do style transfer and assign self.generated_image_path
        content_image = image_loader(self.content_image_path)
        style_image = image_loader(self.style_image_path)
        generated_image = content_image.clone().requires_grad_(True)
        optimizer = optim.Adam([generated_image], lr=LR)
        model = VGG().to(device).eval()

        for e in range(EPOCHS):
            # extracting the features of generated, content and the style required
            # for calculating the loss
            gen_features = model(generated_image)
            content_feautes = model(content_image)
            style_featues = model(style_image)

            # iterating over the activation of each layer and calculate the loss and
            # add it to the content and the style loss
            total_loss = calculate_loss(
                gen_features, content_feautes, style_featues)
            # optimize the pixel values of the generated image and backpropagate the
            # loss
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()

            # print the image and save it after each 100 epoch
            if (not (e % 100)):
                logger.info(total_loss)

                save_image(generated_image, self.generated_image_path)

            save_image(generated_image, self.generated_image_path)
            self.status = NST_REQUEST_DONE

    def get_generated_image_path(self) -> str:
        if not self.is_done():
            raise RuntimeError(
                "get_generated_image_path was called on not NST_REQUEST_DONE")
        return self.generated_image_path

    def is_eligible_for_image_assignment(self) -> bool:
        return (self.status == NST_REQUEST_NEW) or (
            self.status == NST_REQUEST_CONTENT_IMAGE_ASSIGNED)

    def is_done(self) -> bool:
        return self.status == NST_REQUEST_DONE

    def is_eligible_for_transfer(self) -> bool:
        return self.status == NST_REQUEST_STYLE_IMAGE_ASSIGNED


# [0,5,10,19,28] are the index of the layers we will be using to calculate the loss as per
# the paper of NST.
class VGG(nn.Module):
    def __init__(self):
        super(VGG, self).__init__()
        self.req_features = ['0', '5', '10', '19', '28']
        self.model = models.vgg19(weights="IMAGENET1K_V1").features[:29]

    def forward(self, x):
        features = []
        for layer_num, layer in enumerate(self.model):
            x = layer(x)
            if (str(layer_num) in self.req_features):
                features.append(x)

        return features


# defing a function that will load the image and perform the required
# preprocessing
def image_loader(path):
    image = Image.open(path)
    loader = transforms.Compose([transforms.CenterCrop(
        (IMAGE_SIZE, IMAGE_SIZE)), transforms.ToTensor()])
    image = loader(image).unsqueeze(0)
    return image.to(device, torch.float)


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
    await update.message.reply_text(f"""IMAGE_SIZE={IMAGE_SIZE}, EPOCHS={EPOCHS}, LR={LR}, ALPHA={ALPHA}, BETA={BETA},
USERS_REQUESTS={USERS_REQUESTS}""")


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

    if not last_eligible_user_request.is_eligible_for_transfer():
        return

    await update.message.reply_text(f"Starting NST, it may take a while...")
    await last_eligible_user_request.transfer_style()
    generated_image_path = last_eligible_user_request.get_generated_image_path()
    await update.message.reply_photo(generated_image_path)


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
