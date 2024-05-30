import logging
import re
from typing import Any, Dict
from urllib.parse import quote

from celery import Celery
import requests

from config import config
from crud import Crud
from indexing import IndexManager

app = Celery("tasks", broker=config.CELERY_BROKER, backend=config.CELERY_BACKEND)


@app.task
def index_post_words(campaign_id: str):
    campaign = Crud.retrieve_campaign(campaign_id)
    words = (campaign.title + campaign.description).split()
    for word in cls.clean_words(words=words, language="english"):
        IndexManager.create_word_campaign_index(word=word, campaign_id=campaign.id)


@app.task
def get_campaign_sentiment(campaign_id):
    campaign = Crud.retrieve_campaign(campaign_id)
    sentiment = None
    try:
        res = requests.get(
            f"{config.SENTIMENT_URL}?text='{quote(campaign.description)}"
        )
        res.raise_for_status()
        data = res.data()
        if (
            "output" not in data
            or not data.get("output")
            or "label" not in data.get("output")[0]
        ):
            logging.error(f"Invalid sentiment data returned for campaign {campaign_id}")
            return
        sentiment = data.get("output")[0].get("label")
    except Exception as exp:
        logging.error(f"Could not get sentiment for campaign {campaign_id} - {exp}")
        return

    campaign.sentiment = sentiment
    Crud.update_campaign(campaign=campaign)


if __name__ == "__main__":
    app.start()
    print("Celery started")
