FROM python:3.12

ARG APPHOMEDIR=code
ARG USERNAME=user
ARG USER_UID=1001
ARG USER_GID=1001
ARG PYTHONPATH_=${APPHOMEDIR}

WORKDIR /${APPHOMEDIR}

COPY requirements.txt requirements.txt
COPY ./bot /${APPHOMEDIR}

RUN \
    apt update -y && apt upgrade -y \
    && python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid "$USER_GID" "$USERNAME" \
    && useradd --uid "$USER_UID" --gid "$USER_GID" -m "$USERNAME" -d /"$APPHOMEDIR" \
    && chown "$USERNAME:$USERNAME" -R /"$APPHOMEDIR"

USER ${USERNAME}

CMD [ "python3", "-u", "run.py"]
