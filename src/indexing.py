# handles construction and manipulation of indicies
from base64 import b64encode, b64decode
from io import StringIO
from string import punctuation
from typing import Any, Dict, List, Tuple, Union
from urllib.parse import unquote, quote
import nltk

from config import config
from data_manager import get_data_manager, sep, ListPathException, LoadOjbectException
from models import Campaign, User
from utils import gen_random

nltk.download("stopwords")
from nltk.corpus import stopwords

datamgr = get_data_manager()


class InvalidIndexKwargException(Exception):
    pass


class InvalidIndexArgumentException(Exception):
    pass


class Index:
    required_kwargs: List[str] = []
    partition_scheme: int = 0
    encode_ref_id: bool = False
    target_model_name: str = ""

    @classmethod
    def build_path(
        cls,
        ref_id: str,
        target_id: str = "",  # if not target_id, just return parent path
        **kwargs: Dict[str, Any],
    ) -> str:
        cls._validate(kwargs)
        if len(ref_id) < cls.partition_scheme:
            raise InvalidIndexArgumentException(
                f"The ref_id argument '{ref_id}' must be > {cls.partition_scheme} characters"
            )
        parts = [cls.__name__]
        if kwargs and kwargs.values():
            parts.extend([y for x, y in kwargs.items() if x in cls.required_kwargs])

        _ref_id = ref_id
        if cls.encode_ref_id:
            _ref_id = b64encode(_ref_id.encode()).decode()
        parts.append(_ref_id)

        def prep_str(s: str) -> str:
            return f'{s.replace("=", ""):03}'

        if cls.partition_scheme in [1, 2]:
            _ref_id = prep_str(_ref_id)
            parts.insert(1, _ref_id[-3:])
            if cls.partition_scheme == 2:
                parts.insert(1, _ref_id[-2:])

        parts.append(cls.target_model_name)
        if target_id:
            parts.append(f"{target_id}._")
        return sep.join(parts)

    @classmethod
    def _validate(cls, kwargs):
        for field in cls.required_kwargs:
            if field not in kwargs:
                raise InvalidIndexKwargException(
                    f"Argument {field} was expected but not found"
                )


class UserCampaignIndex(Index):
    partition_scheme = 1
    target_model_name: str = "Campaigns"


class EmailUserIndex(Index):
    partition_scheme: int = 2
    encode_ref_id: bool = True
    target_model_name: str = "Users"


class CategoryCampaignIndex(Index):
    target_model_name: str = "Campaigns"


class WordCampaignIndex(Index):
    target_model_name: str = "Campaigns"
    partition_scheme = 2
    encode_ref_id = True


class CampaignBestIndex(Index):
    target_model_name: str = "BestCampaigns"


class CampaignWorstIndex(Index):
    target_model_name: str = "WorstCampaigns"


class LatestCampaignIndex(Index):
    target_model_name: str = "LatestCampaigns"


class IndexManager:
    @staticmethod
    def touch(path: str, ttl: str = ""):
        datamgr.put(path=path, obj=StringIO(""), ttl=ttl)

    @staticmethod
    def delete(path: str):
        if datamgr.exists(path):
            datamgr.rm(path=path)

    @staticmethod
    def retrieve_ids(path: str) -> List[str]:
        # ls returns id files with extension so we strip the extension
        # before sending the id
        if not datamgr.exists(path):
            return []
        ids = datamgr.ls(path)
        if not ids:
            return []
        return [x.split(".")[0] for x in ids]

    @classmethod
    def update_campaign_indicies(cls, campaign: Campaign):
        # user/campaign
        cls.touch(
            path=UserCampaignIndex.build_path(
                ref_id=campaign.user_id, target_id=campaign.id
            )
        )

        cls.touch(
            path=CategoryCampaignIndex.build_path(
                ref_id=campaign.category_id,
                target_id=campaign.id,
            )
        )

        # add to latest campaigns
        cls.create_latest_campaign_index(campaign_id=campaign.id)

        # full word index
        for word in cls.clean_words(
            list(set((campaign.title + campaign.description).split()))
        ):
            cls.create_word_campaign_index(word=word, campaign_id=campaign.id)

    @classmethod
    def clean_words(cls, words: List[str], language: str = "english") -> List[str]:
        stop_words = stopwords.words(language)

        res = []
        # remove stop words and words < 3 char and covert to lowercase
        for word in [x.lower() for x in words if x and len(x) > 2]:
            # remove puncuation
            word = "".join([x for x in word if x not in punctuation])
            if word in stop_words:
                continue
            res.append(word)
        return res

    @classmethod
    def retrieve_campaign_ids_by_user_id(cls, user_id: str) -> List[str]:
        return cls.retrieve_ids(UserCampaignIndex.build_path(ref_id=user_id))

    @classmethod
    def retrieve_campaign_ids_by_category(
        cls, category_id: str, subcategory_id: str
    ) -> List[str]:
        return cls.retrieve_ids(
            CategoryCampaignIndex.build_path(
                ref_id=subcategory_id, category_id=category_id
            )
        )

    @classmethod
    def delete_campaign_indicies(cls, campaign: Campaign):
        # user/campaign
        cls.delete(
            path=UserCampaignIndex.build_path(
                ref_id=campaign.user_id, target_id=campaign.id
            )
        )

        cls.delete(
            path=CategoryCampaignIndex.build_path(
                ref_id=campaign.category_id,
                target_id=campaign.id,
            )
        )

        # delete from latest campaign index
        cls.delete_latest_campaign_index(campaign_id=campaign.id)

        # delete from best/worst
        cls.delete_campaign_best_index(campaign_id=campaign.id)
        cls.delete_campaign_worst_index(campaign_id=campaign.id)

        # delete all word indicies
        for word in list(set((campaign.title + campaign.description).split())):
            cls.delete_word_campaign_id(word=word, campaign_id=campaign.id)

    @classmethod
    def delete_campaign_best_index(cls, campaign_id: str):
        cls.delete(CampaignBestIndex.build_path(ref_id=campaign_id))

    @classmethod
    def delete_campaign_worst_index(cls, campaign_id: str):
        cls.delete(CampaignWorstIndex.build_path(ref_id=campaign_id))

    @classmethod
    def retrieve_user_ids_by_email(cls, email: str) -> List[str]:
        return cls.retrieve_ids(EmailUserIndex.build_path(ref_id=email))

    @classmethod
    def update_user_indicies(cls, user: User):
        # email/user
        cls.touch(path=EmailUserIndex.build_path(ref_id=user.email, target_id=user.id))

    @classmethod
    def delete_user_indicies(cls, user: User):
        # email/user
        cls.delete(
            path=EmailUserIndex.build_path(ref_id=user.email, target_id=user.id),
        )
        cls.delete(path=UserFavoriteCampaignIndex.build_path(ref_id=campaign.user_id))

    @classmethod
    def retrieve_word_campaign_ids(cls, word: str) -> List[str]:
        _word = cls.clean_words([word])
        if not _word:
            return []
        _word = _word[0]
        if not _word:
            return []
        return cls.retrieve_ids(WordCampaignIndex.build_path(ref_id=_word))

    @classmethod
    def delete_word_campaign_id(cls, word: str, campaign_id: str):
        ids = cls.retrieve_word_campaign_ids(word=word)
        if campaign_id in ids:
            cls.delete(
                path=WordCampaignIndex.build_path(ref_id=word, target_id=campaign_id)
            )

    @classmethod
    def create_word_campaign_index(cls, word: str, campaign_id: str):
        cls.touch(WordCampaignIndex.build_path(ref_id=word, target_id=campaign_id))

    @classmethod
    def retrieve_lastest_campaign_index_ids(cls):
        return cls.retrieve_ids(LatestCampaignIndex.build_path(ref_id="latest"))

    @classmethod
    def delete_latest_campaign_index(cls, campaign_id: str):
        cls.delete(
            path=LatestCampaignIndex.build_path(ref_id="latest", target_id=campaign_id)
        )

    @classmethod
    def create_latest_campaign_index(cls, campaign_id: str):
        current_ids = cls.retrieve_lastest_campaign_index_ids()
        if campaign_id in current_ids:  # don't create if already exists
            return
        while len(current_ids) > config.MAX_LATEST_COUNT:
            earliest_campaign_id = current_ids.pop(0)
            cls.delete_latest_campaign_index(earliest_campaign_id)
        cls.touch(
            path=LatestCampaignIndex.build_path(ref_id="latest", target_id=campaign_id)
        )
