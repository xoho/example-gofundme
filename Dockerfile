FROM python:3.11.3-bullseye
ARG GIT_VERSION_HASH=unspecified
RUN apt update && apt install -y gcc libc-dev python3-opencv libgl1 && pip install --upgrade pip

WORKDIR /app
COPY requirements.txt /app

RUN pip install -r requirements.txt

COPY src /app/
RUN echo ${GIT_VERSION_HASH} > /app/VERSION.txt
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
