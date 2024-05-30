import json
import os
from box import Box
from csv import DictReader
from rich import print

data = dict()
fn = "message_bank.json"
if os.path.exists(fn):
    os.remove(fn)
for comment_type in ["positive", "negative", "neutral"]:
    if comment_type not in data:
        data[comment_type] = []
    for line in [
        x for x in open(f"comment_bank_{comment_type}.txt").read().split("\n") if x
    ]:
        _line = line.strip().replace('"', "")
        data[comment_type].append(_line)

json.dump(data, open(fn, "w"), indent=4)

# fn = "all_countries.json"
# src = "countries.json"
# data = json.load(open(src))

# _data = sorted([[x.id, x.en] for x in [Box(y) for y in data]], key=lambda x: x[1])

# json.dump(_data, open(fn, "w"), indent=4)

# data = dict()

# currencies = dict()
# for row in DictReader(
#     open("currencies.txt"),
#     fieldnames=["currency", "unit_text", "symbol"],
# ).reader:
#     currencies[row[0]] = row[2] if row[2] else row[1]

# country_currencies = []
# for row in DictReader(
#     open("country_currency.txt"),
# ).reader:
#     country_currencies.append(row)
# # print(country_currencies)

# for row in country_currencies:
#     code = row[2]
#     if code not in data:
#         data[code] = dict(
#             country=row[0].title(),
#             code=code,
#             currency_name=row[1],
#             symbol=currencies.get(code, code),
#         )


# data = list(data.values())
# json.dump(data, open("country_currency.json", "w"), indent=4)

# cc = json.load(open("country_currency.json"))

# duplicates = []
# for c in cc:
#     country = c.get("country")
#     if len([x.get("country") for x in cc if x.get("country") == country]) > 1:
#         duplicates.append(c)

# duplicates = sorted(duplicates, key=lambda x: x["country"])
# print(duplicates[0:10])

# categories = [
#     x.strip()
#     for x in """
# Animals
# Business
# Community
# Creative
# Education
# Emergencies
# Environment
# Events
# Faith
# Family
# Funeral & Memorial
# Medical
# Monthly Bills
# Newlyweds
# Other
# Sports
# Travel
# Ukraine Relief
# Volunteer
# Wishes""".split(
#         "\n"
#     )
#     if x
# ]
# data = []
# fn = "campaign_types.json"
# for idx, c in enumerate(categories):
#     data.append(dict(mood="postiive", name=c, id=idx))

# json.dump(data, open(fn, "w"), indent=4)


# fn = "country_currency.json"
# data = sorted(json.load(open(fn)), key=lambda x: x.get("country"))
# json.dump(data, open(fn, "w"), indent=4)

# fn = "campaign_types.json"
# data = sorted(json.load(open(fn)), key=lambda x: x.get("name"))
# json.dump(data, open(fn, "w"), indent=4)

# fn = "country_currency.json"
# data = json.load(open(fn))
# for idx in range(0, len(data)):
#     data[idx]["id"] = idx
# json.dump(data, open(fn, "w"), indent=4)

# data = []
# for row in DictReader(
#     open("interall.csv"),
#     fieldnames=["name", "a", "b", "c"],
# ).reader:
#     data.append(row[0])

# data = list(set(data))
# json.dump(data, open("names.json", "w"))


# fn = "first_names.json"
# json.dump([x.title() for x in json.load(open(fn))], open(fn, "w"))
