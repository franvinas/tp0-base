FROM alpine:latest

RUN apk add --no-cache netcat-openbsd

COPY test_server.sh test_server.sh

CMD ["sh", "test_server.sh"]
