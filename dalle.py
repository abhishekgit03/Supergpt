import os
import requests
import base64
os.environ["OPENAI_API_KEY"] = "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"
from openai import OpenAI
client = OpenAI()

def imagegenerator(imageprompt):
    response = client.images.generate(
    model="dall-e-3",
    prompt=imageprompt,
    size="1024x1024",
    quality="standard",
    n=1,
    )
    image_url = response.data[0].url
    response = requests.get(image_url)
    image_base64 = base64.b64encode(response.content).decode('utf-8')
    return image_base64
    