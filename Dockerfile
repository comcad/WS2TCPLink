FROM alpine:latest
RUN apk add --no-cache nginx python3 py3-pip py3-flask apache2-utils procps
RUN pip3 install websockify --break-system-packages flask websockets

WORKDIR /app
RUN mkdir -p /app/data /run/nginx
COPY app.py /app/app.py
COPY nginx.conf /etc/nginx/http.d/default.conf

RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'htpasswd -bc /etc/nginx/.htpasswd "${ADMIN_USER:-admin}" "${ADMIN_PASS:-password}"' >> /entrypoint.sh && \
    echo 'nginx' >> /entrypoint.sh && \
    echo 'python3 /app/app.py' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
