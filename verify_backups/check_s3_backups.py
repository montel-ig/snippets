#!/usr/bin/env python
import json
import logging
import os

import boto3
import datetime
import pytz
import requests
import sys

logging.basicConfig(level=logging.INFO)

DB_POSTGRES = 'postgres'
DB_CASSANDRA = 'cassandra'


class SnapShotsVerifier:
    GENIE_KEY = os.environ.get('GENIE_KEY')
    GENIE_TEAM = os.environ.get('GENIE_TEAM', '24_7 MontelCare')
    MAIL_GUN_KEY = os.environ.get('MAIL_GUN_KEY')
    AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    MAIL_GUN_DOMAIN = os.environ.get('MAIL_GUN_DOMAIN')
    S3_BUCKET = os.environ.get('S3_BUCKET', 'iddatabase2backup')
    S3_REGION = 'eu-north-1'
    GENIE_URL = 'https://api.opsgenie.com/v2/alerts'
    GENIE_ALERT_TAGS = ['PM Customer']
    GENIE_ENTITY = 'PackageMedia'
    DEFAULT_MESSAGE = 'ALARM: "PM database snapshot is not updated on s3"'
    ALERT_PRIORITY = 'P1'
    MONTEL_CARE_EMAIL = 'doesnotreply@montel.fi'
    EMAIL_RECIPIENTS = ['arslan@montel.fi', 'toni@montel.fi', 'alvaro@packagemedia.fi']

    SNAPSHOTS_CONF = {
        DB_POSTGRES: {
            'folder': os.environ.get('POSTGRES_S3_PREFIX', 'iddatabase-pro/snapshots/'),
            'interval': datetime.timedelta(hours=1, minutes=15)
        },
        DB_CASSANDRA: {
            'folder': os.environ.get('CASSANDRA_S3_PREFIX', 'cassandra-pro/iddatabase/cassandra/pmid/97c9af/'),
            'interval': datetime.timedelta(days=1, minutes=15)
        }
    }

    def __init__(self):
        self.description = None
        self.s3_client = boto3.client(
            's3', aws_access_key_id=self.AWS_ACCESS_KEY, aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY,
            region_name=self.S3_REGION
        )
        self.paginator = self.s3_client.get_paginator('list_objects')

    def verify_snap_shots(self, db_type: str) -> None:
        """
        Check latest snaphosts on s3 and verify if there are getting updated as expected according to schedule.
        PS: Should be more simpler if it is sure that cleanup is working and snapshots won't cross 1000 mark:
                response = conn.list_objects_v2(Bucket=<bucket>, Prefix=<folder>)
                content = response['Contents']
                latest = max(content, key=lambda x: x['LastModified'])
        """
        logging.info(f'Going to check backups on s3...')
        page_iterator = self.paginator.paginate(
            Bucket=self.S3_BUCKET,
            Prefix=self.SNAPSHOTS_CONF[db_type]['folder']
        )
        latest = dict(LastModified=pytz.utc.localize(datetime.datetime.min))
        now = datetime.datetime.now(tz=pytz.utc)
        time_to_check = now - self.SNAPSHOTS_CONF[db_type]['interval']
        for page in page_iterator:
            for content in page['Contents']:
                if latest['LastModified'] < content['LastModified']:
                    latest = content
        if latest['LastModified'] < time_to_check:
            logging.info(f'Backup not updating, escalating the issue...')
            self.description = (f"{db_type} snapshot not updated on s3, "
                                f"last snapshot was updated at {latest['LastModified']}.")
            self.post_alert()
            self.send_email()
        else:
            logging.info(f'Backups are updated...')

    def post_alert(self) -> None:
        logging.info(f'Posting alert on opsgenie...')
        headers = {'Content-Type': 'application/json', 'Authorization': f'GenieKey {self.GENIE_KEY}'}
        resp = requests.post(
            self.GENIE_URL,
            data=json.dumps(dict(
                message=self.DEFAULT_MESSAGE,
                priority=self.ALERT_PRIORITY,
                description=self.description,
                tags=self.GENIE_ALERT_TAGS,
                entity=self.GENIE_ENTITY,
                responders=[{'name': self.GENIE_TEAM, 'type': 'team'}]
            )),
            headers=headers
        )
        logging.info(
            f'Request to opsgenie API completed with Status code: {resp.status_code} and Response: {resp.text}'
        )

    def send_email(self) -> None:
        logging.info(f'Sending email via mail gun API...')
        request_url = f'https://api.mailgun.net/v2/{self.MAIL_GUN_DOMAIN}/messages'
        resp = requests.post(
            request_url,
            auth=('api', self.MAIL_GUN_KEY),
            data={
                'from': self.MONTEL_CARE_EMAIL,
                'to': self.EMAIL_RECIPIENTS,
                'subject': self.DEFAULT_MESSAGE,
                'text': self.description
            }
        )
        logging.info(
            f'Request to mail gun API completed with Status code: {resp.status_code} and Response: {resp.text}'
        )


def run(db_type: str) -> None:
    verifier = SnapShotsVerifier()
    verifier.verify_snap_shots(db_type)


if __name__ == '__main__':
    database_type = sys.argv[1]

    if database_type == DB_POSTGRES:
        logging.info(f'Starting process for {DB_POSTGRES}')
        run(DB_POSTGRES)
    else:
        logging.info(f'Starting process for {DB_CASSANDRA}')
        run(DB_CASSANDRA)
