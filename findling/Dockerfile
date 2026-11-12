# Fest auf einen geprüften Stand gezeigt, damit der Bau nichts Unerwartetes holt.
FROM ghcr.io/home-assistant/base:3.24@sha256:58422480a299b16b6ea376c2167463206d430619ed02b40cd687c8bd6875519e

COPY requirements.lock /tmp/requirements.lock

# Nur fertige Pakete mit geprüfter Prüfsumme und nur von PyPI. Das Installationswerkzeug bleibt nicht im Image.
RUN apk add --no-cache python3 openssl su-exec \
    && apk add --no-cache --virtual .build py3-pip \
    && env -u PIP_EXTRA_INDEX_URL -u UV_EXTRA_INDEX_URL \
        python3 -m pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore \
        --index-url https://pypi.org/simple --only-binary=:all: --no-deps --require-hashes \
        --target /opt/findling/lib -r /tmp/requirements.lock \
    && apk del --no-network .build \
    && rm -f /tmp/requirements.lock \
    && test -x /usr/bin/python3.14 \
    && addgroup -S findling \
    && adduser -S -D -H -h /data -s /sbin/nologin -G findling findling

COPY app /opt/findling/app
COPY run.sh /run.sh
COPY spiegel.sh /spiegel.sh

# Der Programmcode gehört root. Das Programm selbst kann ihn nicht ändern.
RUN chown -R root:root /opt/findling /run.sh /spiegel.sh \
    && chmod -R a-w,a+rX /opt/findling \
    && chmod 0500 /run.sh /spiegel.sh \
    && python3 -m compileall -q /opt/findling

WORKDIR /opt/findling/app
CMD [ "/run.sh" ]
