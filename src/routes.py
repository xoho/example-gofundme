from collections import OrderedDict
from functools import wraps
import json
from datetime import datetime
import logging
import random
from string import ascii_uppercase
import textwrap
import time
from typing import List
from urllib.parse import unquote
from flask import (
    render_template,
    url_for,
    redirect,
    request,
    session,
    send_file,
    abort,
    jsonify,
)
from jinja2 import environment
import arrow
from passlib.hash import pbkdf2_sha256

from app import app, config
from forms import (
    CountryCategoryForm,
    CampaignTypeForm,
    CampaignAmountForm,
    CampaignDetailsForm,
    LoginForm,
    SignupForm,
    DonationForm,
    SearchForm,
)
from crud import Crud
from indexing import IndexManager
from models import Campaign, User, MiniCampaign
from tasks import index_post_words, get_campaign_sentiment
from utils import is_image_file, is_explicit_content, scrub_explicit

FIRST_NAMES = Crud.retrieve_first_names()
MESSAGE_BANK = Crud.retrieve_message_bank()
DONATION_DISTRIBUTION = Crud.retreive_donation_distribution()


# ##############
# jinja2 filters
# ##############
def time_since(dt):
    try:
        return arrow.get(dt, tzinfo="utc").humanize()
    except Exception as exp:
        return "long, long ago"


def contributions_with_messages(contributions):
    res = sorted(
        [x for x in contributions if x.get("message")],
        key=lambda x: x.get("date"),
        reverse=True,
    )
    return res[0:25]


def separate_number(number):
    s = [x for x in str(number)]
    r = []
    rr = []
    while len(s) > 0:
        r.append(s.pop(-1))
        if len(r) == 3:
            rr.extend(r)
            rr.append(" ")
            r = []
    rr.extend(r)
    rr.reverse()
    return "".join(rr).strip()


# Register the filters
app.jinja_env.filters["time_since"] = time_since
app.jinja_env.filters["contributions_with_messages"] = contributions_with_messages
app.jinja_env.filters["separate_number"] = separate_number


def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if "user_id" not in session:
            # Redirect to the login page if user is not authenticated
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return decorated_view


@app.route("/")
def index():
    return render_template(
        "index.html",
        app_name=config.APP_NAME,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    error = None
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user_ids = IndexManager.retrieve_user_ids_by_email(email)

        if not user_ids:
            error = "No user with that email found. Please signup!"
            return render_template("login.html", form=form, error=error)

        user = Crud.retrieve_user(user_id=user_ids[0])
        if pbkdf2_sha256.verify(form.password.data, user.password_hash):
            session["user_id"] = user.id
            session["user_first_name"] = user.first_name
            session["user_last_name"] = user.first_name
            if "next_url" in session and session["next_url"]:
                return redirect(session.pop("next_url"))
            return redirect(url_for("my_campaigns"))

        error = "Password incorrect"

    return render_template("login.html", form=form, error=error)


@app.route("/logout")
def logout():
    for key in [x for x in session if not x.startswith("_")]:
        session.pop(key)
    return redirect(url_for("index"))


@app.route("/img/<string:filename>")
def show_asset_image(filename: str):
    return send_file(f"assets/images/{filename}")


@app.route("/create", methods=["GET", "POST"])
def create():
    form = CountryCategoryForm()
    form.country.choices = Crud.retrieve_countries()
    form.category.choices = [
        (x.get("id"), x.get("name")) for x in Crud.retreive_categories()
    ]

    if form.validate_on_submit():
        country = None if not form.country.data.isnumeric() else int(form.country.data)
        if country not in [x[0] for x in form.country.choices]:
            logging.error(f"Posted value for country '{country}' is not a valid choice")
            country = None
        category = (
            None if not form.category.data.isnumeric() else int(form.category.data)
        )
        if category not in [x[0] for x in form.category.choices]:
            logging.error(
                f"Posted value for category '{category}' is not a valid choice"
            )
        if country is not None and category is not None:
            session["create"] = dict(country_id=int(country), category_id=int(category))
            return redirect(url_for("select_types"))

    return render_template(
        "onboard/step1.html", form=form, next_url=url_for("select_types")
    )


@app.route("/create/types", methods=["GET", "POST"])
def select_types():
    if not session["create"]:
        return redirect(url_for("create"))
    form = CampaignTypeForm(request.form)
    form.campaign_type.choices = [
        (x.get("id"), x.get("name")) for x in Crud.retreive_campaign_types()
    ]
    if form.validate_on_submit():
        campaign_type_id = (
            None
            if not form.campaign_type.data.isnumeric()
            else int(form.campaign_type.data)
        )
        if campaign_type_id is not None:
            session["create"]["recipient"] = form.recipient.data or "self"
            session["create"]["campaign_type_id"] = campaign_type_id
            return redirect(url_for("create_target"))

    return render_template(
        "onboard/step2.html", form=form, next_url=url_for("create_target")
    )


@app.route("/create/target", methods=["GET", "POST"])
def create_target():
    if "create" not in session:
        return redirect(url_for("create"))

    form = CampaignAmountForm(request.form)
    if form.validate_on_submit():
        session["create"]["goal"] = max(1, form.goal.data)

        if "user_id" not in session:
            session["next_url"] = url_for("create_campaign")
            return redirect(url_for("signup"))

        return redirect(url_for("create_campaign"))

    country_id = session["create"].get("country_id", None)
    if country_id is None:
        logging.error(f"No country id in session")
        return redirect(url_for("create"))

    cc = Crud.retrieve_country_currency(country_id)
    if not cc:
        logging.error(
            f"Could not find country/currency for country code {country_code}"
        )
        return redirect(url_for("create"))
    session["create"]["currency_code"] = cc.get("code")
    session["create"]["currency_symbol"] = cc.get("symbol")

    return render_template(
        "onboard/step3.html",
        form=form,
        currency_symbol=cc.get("symbol"),
        currency_code=cc.get("code"),
    )


@app.route("/create/campaign", methods=["GET", "POST"])
@login_required
def create_campaign():
    if "create" not in session:
        return redirect(url_for("create"))

    form = CampaignDetailsForm(request.form)

    if form.validate_on_submit():
        kwargs = dict()
        for key in [
            "category_id",
            "country_id",
            "campaign_type_id",
            "goal",
            "currency_code",
            "currency_symbol",
            "recipient",
        ]:
            if key not in session["create"]:
                logging.error(f"create_campaign- {key} not found in session")
                return redirect(url_for("create"))
            kwargs[key] = session["create"][key]

            if isinstance(kwargs[key], str) and kwargs[key].isnumeric():
                kwargs[key] = int(kwargs[key])

        for key in ["title", "description"]:
            kwargs[key] = scrub_explicit(getattr(form, key).data)
        kwargs["user_id"] = session["user_id"]

        post_files = request.files.getlist("file")
        img = None
        if post_files and post_files[0]:
            img = post_files[0]
            if is_image_file(img):
                if config.ENABLE_EXPLICIT_IMAGE_CHECKING and is_explicit_content(img):
                    return render_template(
                        "4xx.html",
                        message="The image you uploaded has explicit content and was not added.",
                    )
            else:
                img = None

        campaign = Campaign(**kwargs)
        Crud.update_campaign(campaign, img=img)

        index_post_words.delay(campaign_id=campaign.id)
        get_campaign_sentiment.delay(campaign_id=campaign.id)

        return redirect(url_for("get_campaign", campaign_id=campaign.id))

    return render_template("onboard/step4.html", form=form)


def date_to_string(date):
    return str(date).replace("-", "").replace(":", "").split(".")[0]


def populate_contributions(campaign: Campaign):
    """artifically populated contributions"""
    goal = campaign.goal

    n = max(
        1, int(goal / config.DIVISOR_UPDATES_PER_TIME_PERIOD)
    )  # number of updates per time period
    p = config.UPDATE_TIME_PERIOD_IN_MINUTES  # update time period in minutes
    updates = []

    anchor = arrow.get(campaign.created, tzinfo="utc")
    if campaign.last_contribution_datetime:
        anchor = arrow.get(campaign.last_contribution_datetime, tzinfo="utc")

    if not campaign.sentiment:
        campaign.sentiment = "neutral"
    anchor = anchor.shift(minutes=random.randrange(p * 0.2, p))
    utc_now = arrow.utcnow()
    # calculate the contribution slots
    contribution_slots = []
    while anchor < utc_now:
        contrib_count = random.randrange(0, n)
        for i in range(0, contrib_count):
            contribution_slots.append(anchor)
        anchor = anchor.shift(minutes=random.randrange(p * 0.2, p))

    this_run_amount = 0
    total_contribution_slots_count = len(contribution_slots)

    if total_contribution_slots_count < 1:
        # no updates, just return
        return

    if total_contribution_slots_count < 100:
        campaign.contributions = campaign.contributions[
            -100 - total_contribution_slots_count :
        ]
    else:
        campaign.contributions = []

    # just update the last slots
    for anchor in contribution_slots[-100:]:
        name = (
            "Anonymous"
            if random.random() < config.ANONYMOUS_POST_PERCENT
            else f"{random.choice(FIRST_NAMES)} {random.choice(ascii_uppercase)}."
        )
        message = ""
        if random.random() < config.MESSAGE_POST_PERCENT:
            message = random.choice(MESSAGE_BANK.get(campaign.sentiment))
        amount = random.choice(DONATION_DISTRIBUTION)
        this_run_amount += amount
        campaign.amount_reached += amount
        campaign.contributions.append(
            dict(
                name=name,
                amount=amount,
                date=str(anchor),
                message=message,
            )
        )

    # artifically adjust for amount increase
    if total_contribution_slots_count > 100:
        avg_amount = int(this_run_amount / 100)
        unfulfilled_slots = total_contribution_slots_count - 100
        campaign.amount_reached += avg_amount * unfulfilled_slots

    campaign.contribution_count += total_contribution_slots_count

    campaign.last_contribution_datetime = date_to_string(
        str(anchor if anchor < arrow.utcnow() else arrow.utcnow())
    )
    Crud.update_campaign(campaign=campaign)


@app.route("/campaign/<string:campaign_id>", methods=["GET"])
def get_campaign(campaign_id: str):
    campaign = Crud.retrieve_campaign(campaign_id=campaign_id)
    if not campaign:
        return render_template(
            "4xx.html", message=f"A campaign with id {campaign_id} does not exist"
        )

    # artifically populate contributions
    populate_contributions(campaign=campaign)

    category_name = Crud.retrieve_category_name(category_id=campaign.category_id)
    cc = Crud.retrieve_country_currency(country_id=campaign.country_id)
    top_contribution = first_contribution = last_contribution = None
    if campaign.contributions:
        top_contribution = sorted(
            campaign.contributions, key=lambda x: x.get("amount")
        )[-1]
        contributions_date_sorted = sorted(
            campaign.contributions, key=lambda x: x.get("date")
        )
        first_contribution = contributions_date_sorted[0]
        last_contribution = contributions_date_sorted[-1]

    return render_template(
        "campaign.html",
        campaign=campaign,
        category_name=category_name,
        currency_symbol=campaign.currency_symbol or "$",
        progress=100 * min(1, campaign.amount_reached / max(1, campaign.goal)),
        top_contribution=top_contribution,
        first_contribution=first_contribution,
        last_contribution=last_contribution,
    )


@app.route("/donate/<string:campaign_id>", methods=["GET", "POST"])
def donate(campaign_id):
    campaign = Crud.retrieve_campaign(campaign_id=campaign_id)
    if not campaign:
        return render_template(
            "4xx.html", message=f"A campaign with id {campaign_id} does not exist"
        )

    form = DonationForm(request.form)
    if form.validate_on_submit():
        contribution = dict(
            message=form.message.data,
            amount=form.amount.data,
            name=form.donor.data if not form.anonymous.data else "Anonymous",
            date=date_to_string(arrow.utcnow()),
        )
        campaign.contributions.append(contribution)
        Crud.update_campaign(campaign)
        return redirect(url_for("get_campaign", campaign_id=campaign.id))

    if "user_first_name" in session and "user_last_name" in session:
        form.donor.data = f"{session['user_first_name']} {session['user_last_name']}"
    return render_template(
        "donation.html",
        campaign=campaign,
        form=form,
        currency_symbol=campaign.currency_symbol,
        currency_code=campaign.currency_code,
    )


@app.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm(request.form)
    errors = []
    if form.validate_on_submit():
        existing_users = IndexManager.retrieve_user_ids_by_email(email=form.email.data)
        if existing_users:
            errors.append("User with this email already exists")
            return render_template("signup.html", form=form, errors=errors)
        kwargs = dict()
        for key in ["first_name", "last_name", "email"]:
            kwargs[key] = getattr(form, key).data
        kwargs["password_hash"] = pbkdf2_sha256.hash(form.password.data)
        user = User(**kwargs)
        Crud.update_user(user=user)
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["user_first_name"] = user.first_name

        if "next_url" in session:
            next_url = session.pop("next_url")
            return redirect(next_url)

        return redirect(url_for("index"))

    return render_template("signup.html", form=form, errors=errors)


@app.route("/img/campaign/<string:campaign_id>")
def get_campaign_image(campaign_id):
    campaign = Crud.retrieve_campaign(campaign_id)
    if not campaign or not campaign.image_path:
        return redirect(
            url_for("show_asset_image", filename="campaign-placeholder.png")
        )
    return send_file(Crud.retrieve_image(campaign.image_path), mimetype="image/png")


@app.route("/search", methods=["GET", "POST"])
def search():
    form = SearchForm(request.form)
    campaigns = []
    if form.validate_on_submit():
        search_terms = form.terms.data.split()

        campaign_ids = []
        for word in search_terms:
            campaign_ids.extend(IndexManager.retrieve_word_campaign_ids(word=word))
        campaign_ids = list(set(campaign_ids))[0:100]
        campaigns = [y for y in [Crud.retrieve_campaign(x) for x in campaign_ids] if y]
        if campaigns:
            campaigns = sorted(
                campaigns, key=lambda x: x.last_contribution_datetime, reverse=True
            )
            for campaign in campaigns:
                populate_contributions(campaign=campaign)
    return render_template("campaigns.html", form=form, campaigns=campaigns)


@app.route("/latest", methods=["GET"])
def latest():
    campaign_ids = IndexManager.retrieve_lastest_campaign_index_ids()[0:25]
    campaigns = [Crud.retrieve_campaign(x) for x in campaign_ids]
    for campaign in campaigns:
        populate_contributions(campaign=campaign)
    form = None
    return render_template(
        "campaigns.html", form=None, campaigns=campaigns, page_title="Latest"
    )


@app.route("/mycampaigns")
@login_required
def my_campaigns():
    campaign_ids = IndexManager.retrieve_campaign_ids_by_user_id(session["user_id"])
    campaigns = [Crud.retrieve_campaign(x) for x in campaign_ids]
    for campaign in campaigns:
        populate_contributions(campaign=campaign)
    minified_campaigns = sorted(
        [MiniCampaign(x) for x in campaigns],
        key=lambda x: x.created,
    )
    page_title = "My Campaigns"

    return render_template(
        "campaigns.html", campaigns=minified_campaigns, page_title=page_title
    )


# ####
# apis
# ####
@app.route("/api/fix/campaign/<string:campaign_id>")
def fix_campaign(campaign_id):
    operation = request.args.get("operation", default=None)
    campaign = Crud.retrieve_campaign(campaign_id=campaign_id)
    if operation == "scrub_contributions":
        campaign.contributions = []
        campaign.last_contribution_datetime = campaign.created

    if operation == "stats":
        return jsonify(dict(contribution_count=len(campaign.contributions)))

    if operation == "delete":
        Crud.delete_campaign(campaign_id=campaign.id)
        return "ok"

    Crud.update_campaign(campaign)
    return "ok"


# @app.route("")

# @app.route("/img/<path:path>")
# def show_image(path: str):
#     try:
#         return send_file(Crud.retrieve_image(path), mimetype="image/png")
#     except DoesNotExistException:
#         abort(404, "Image does not exist")
#     except Exception as exp:
#         logging.error(f"Could not load image at {path} - {exp} ({type(exp)})")
#         abort(400, "Could not load image")
