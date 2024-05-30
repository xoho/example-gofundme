import json
from flask_wtf import FlaskForm
from wtforms import (
    DecimalField,
    EmailField,
    StringField,
    SelectField,
    TextAreaField,
    SubmitField,
    BooleanField,
    HiddenField,
    RadioField,
    IntegerField,
    PasswordField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Email


class CountryCategoryForm(FlaskForm):
    country = SelectField(
        "Country",
        choices=[],  #  (cat, cat) for cat in categories.keys()],
        validators=[DataRequired()],
    )
    category = SelectField("Category", choices=[], validators=[DataRequired()])


class CampaignTypeForm(FlaskForm):
    campaign_type = SelectField(
        "Campaign Type", choices=[], validators=[DataRequired()]
    )
    recipient = StringField("Recipient")


class CampaignAmountForm(FlaskForm):
    goal = IntegerField("Goal", validators=[DataRequired()])


class CampaignDetailsForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired()])


class SignupForm(FlaskForm):
    first_name = StringField("First name", validators=[DataRequired()])
    last_name = StringField("Last name", validators=[DataRequired()])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign up")


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


class DonationForm(FlaskForm):
    amount = IntegerField("Enter your donation pledge", validators=[DataRequired()])
    message = StringField("Write an optional message")
    anonymous = BooleanField("Make this donation pledge anonymously", default="n")
    donor = StringField("Donor name")
    submit = SubmitField("Pledge this amount")


class SearchForm(FlaskForm):
    terms = StringField("Search", validators=[DataRequired()])
    submit = SubmitField("Search")
