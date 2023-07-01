# nst-telegram-bot
A telegram bot providing neural style transfer service.

# Setup
Docker
```bash
git clone https://github.com/masim05/nst-telegram-bot.git
cd nst-telegram-bot
docker build -t nst-telegram-bot .
docker run -d -e TG_BOT_TOKEN=<YOUR_TOKEN> nst-telegram-bot
```

Native, tested with python 3.11.4
```bash
git clone https://github.com/masim05/nst-telegram-bot.git
cd nst-telegram-bot
pip3 install -r requirements.txt
IMAGE_SIZE=64 EPOCHS=500 LR=0.005 ALPHA=10 BETA=60 TG_BOT_TOKEN=<YOUR_TOKEN> python app.py
```

Supported environment variables:
 - IMAGE_SIZE - size of the result image
 - EPOCHS - number of epochs to learn
 - LR - learning rate
 - ALPHA and BETA - weights of content_loss and style_loss respectively
# Usage
Available commands:
 - /start - general greeting
 - /help - usage info
 - /debug - debug info

The bot expects to receive two images and sends result of <a href="https://en.wikipedia.org/wiki/Neural_style_transfer">NST</a> in return. The first image will be used as a content image, the second - as a style one.

# Credits
 - https://docs.python-telegram-bot.org/en/stable/examples.echobot.html
 - https://towardsdatascience.com/implementing-neural-style-transfer-using-pytorch-fd8d43fb7bfa
 - https://arxiv.org/pdf/1508.06576.pdf