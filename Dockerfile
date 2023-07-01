# syntax=docker/dockerfile:1

FROM python:3.11.4-bookworm

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
RUN python3 -c 'import torchvision.models as models; model = models.vgg19(weights="IMAGENET1K_V1")'
RUN mkdir images

COPY . .

CMD ["python3", "app.py"]