from io import BytesIO, StringIO
import json
from typing import Any, Dict, List, Tuple, Union

from config import config
from data_manager import get_data_manager, sep, ListPathException, LoadOjbectException
from models import User, Campaign
from indexing import IndexManager
from utils import gen_random, resize_and_center_crop

datamgr = get_data_manager()


class RecordExistsException(Exception):
    pass


class NoUserExistsException(Exception):
    pass


class NoThreadExistsException(Exception):
    pass


class DoesNotExistException(Exception):
    pass


class AuthenticationCodeException(Exception):
    pass


class NoCountryCodeExistsException(Exception):
    pass


class NoLatLonExistsException(Exception):
    pass


class NoCampaignTypeExistsException(Exception):
    pass


class NoCategoryExistsException(Exception):
    pass


class Crud:
    @classmethod
    def load_country_currency_data(cls):
        return json.load(open(config.COUNTRY_CURRENCY_DATA))

    @classmethod
    def retrieve_countries(cls):
        return [
            (x.get("id"), x.get("country")) for x in cls.load_country_currency_data()
        ]

    @classmethod
    def retrieve_country_currency(cls, country_id: int):
        if not isinstance(country_id, int):
            country_id = int(country_id)
        cc = next(
            (x for x in cls.load_country_currency_data() if x.get("id") == country_id),
            None,
        )
        return cc

    @classmethod
    def retreive_categories(cls):
        return json.load(open(config.CATEGORIES_DATA))

    @classmethod
    def retreive_donation_distribution(cls):
        return json.load(open(config.DONATION_DISTRIBUTION_DATA))

    @classmethod
    def retrieve_first_names(cls):
        return json.load(open(config.FIRST_NAMES_DATA))

    @classmethod
    def retrieve_message_bank(cls):
        return json.load(open(config.MESSAGE_BANK_DATA))

    @classmethod
    def retrieve_category_name(cls, category_id: int) -> str:
        if not isinstance(category_id, int):
            category_id = int(category_id)
        category = next(
            (x for x in cls.retreive_categories() if x.get("id") == category_id), None
        )
        if category is None:
            raise NoCategoryExistsException(f"No category with id {category_id} found")
        return category["name"]

    @classmethod
    def retreive_campaign_types(cls):
        return json.load(open(config.CAMPAIGN_TYPES_DATA))

    @classmethod
    def retreive_campaign_type_name(cls, campaign_type_id: int) -> str:
        campaign_type = next(
            (
                x
                for x in cls.retreive_campaign_types()
                if x.get("id") == campaign_type_id
            ),
            None,
        )
        if campaign_type is None:
            raise NoCampaignTypeExistsException(
                f"No campaign type with id {campaign_type_id} found"
            )
        return campaign_type["name"]

    # ######
    # user
    # ######
    @classmethod
    def update_user(cls, user: User):
        datamgr.save(user)
        IndexManager.update_user_indicies(user)

    @classmethod
    def retrieve_user(cls, user_id: str) -> User:
        path = User.build_path(oid=user_id)
        if not datamgr.exists(path):
            return None
        return User(**json.load(datamgr.get(path=path)))

    # ########
    # campaign
    # ########
    @classmethod
    def update_campaign(cls, campaign: Campaign, img: Any = None):
        path = campaign.get_relative_path()
        update_indicies = True
        if datamgr.exists(path=path):
            # delete existing word index if necessary
            update_indicies = False
            old_campaign_data = json.load(datamgr.get(path=path))
            old_words = set(
                (
                    old_campaign_data.get("title")
                    + old_campaign_data.get("description")
                ).split()
            )
            new_words = set((campaign.title + campaign.description).split())
            diff = old_words - new_words
            if diff:
                update_indicies = True
                for word in diff:
                    IndexManager.delete_word_campaign_id(
                        word=word, campaign_id=campaign.id
                    )
            campaign.created = old_campaign_data.get("created")

        if img:
            _img = resize_and_center_crop(img, (650, 450))
            img_path = sep.join([campaign.get_parent_path(), f"{gen_random(32)}.png"])
            datamgr.put(path=img_path, obj=_img)
            campaign.image_path = img_path

        datamgr.save(campaign)
        if update_indicies:
            print("updating indicies")
            IndexManager.update_campaign_indicies(campaign)

    @classmethod
    def retrieve_campaign(cls, campaign_id: str) -> Campaign:
        path = Campaign.build_path(oid=campaign_id)
        if not datamgr.exists(path):
            return None
        campaign_data = json.load(datamgr.get(path=path))
        campaign = Campaign(**campaign_data)
        campaign.created = campaign_data.get("created")
        return campaign

    @classmethod
    def delete_campaign(cls, campaign_id: str):
        path = Campaign.build_path(oid=campaign_id)
        campaign = cls.retrieve_campaign(campaign_id=campaign_id)
        IndexManager.delete_campaign_indicies(campaign)
        datamgr.rm(path=path)

    @classmethod
    def retrieve_image(cls, path: str) -> BytesIO:
        if not datamgr.exists(path):
            raise DoesNotExistException()
        return datamgr.get(path)
