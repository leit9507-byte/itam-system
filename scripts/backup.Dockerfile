FROM alpine:3.20

RUN apk add --no-cache mysql-client tzdata tar gzip

COPY backup-cron.sh /usr/local/bin/backup-cron.sh
RUN chmod +x /usr/local/bin/backup-cron.sh

CMD ["/bin/sh", "/usr/local/bin/backup-cron.sh"]
