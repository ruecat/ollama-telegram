FROM python:3.12-alpine

ARG APPHOMEDIR=code
ARG USERNAME=user
ARG USER_UID=1001
ARG USER_GID=1001
ARG PYTHONPATH_=${APPHOMEDIR}

WORKDIR /${APPHOMEDIR}

COPY requirements.txt requirements.txt
COPY ./bot /${APPHOMEDIR}

# Configure app home directory
RUN \
    addgroup -g "$USER_GID" "$USERNAME" \
    && adduser --disabled-password -u "$USER_UID" -G "$USERNAME" -h /"$APPHOMEDIR" "$USERNAME" \
    && chown "$USERNAME:$USERNAME" -R /"$APPHOMEDIR"

# Install dependency packages, upgrade pip and then install requirements
RUN \
    apk add --no-cache gcc g++ \
    && python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del --no-cache gcc g++

USER ${USERNAME}

CMD [ "python3", "-u", "run.py"]
