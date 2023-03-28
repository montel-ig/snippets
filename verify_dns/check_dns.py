import time
import json
import logging
import requests
import os
import sys
import dns.resolver

logging.basicConfig(level=logging.INFO)


class DNSVerifier:
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
    DEFAULT_MESSAGE = 'ALARM: "DNS issue on node"'
    ALERT_PRIORITY = 'P1'
    MONTEL_CARE_EMAIL = 'doesnotreply@montel.fi'
    EMAIL_RECIPIENTS = ['arslan@montel.fi', 'toni@montel.fi', 'alvaro@packagemedia.fi']
    DESCRIPTION = 'Node cannot resolve DNS on node with IP: {node_ip}'

    def __init__(self):
        self.machine_ip = None

    def verify_dns(self, dns_list: str) -> None:
        dns_resolver = dns.resolver.Resolver()
        names = dns_list.split(',')

        for name in names:
            logging.info('Checking....{}'.format(name))
            try:
                answers = dns_resolver.resolve(name)
                logging.info(answers.rrset)
            except (dns.resolver.NoAnswer, dns.resolver.LifetimeTimeout, dns.resolver.NoNameservers):
                for i in range(3):
                    try:
                        dns_resolver.resolve(name)
                        time.sleep(60)
                    except (dns.resolver.NoAnswer, dns.resolver.LifetimeTimeout, dns.resolver.NoNameservers):
                        if i == 2:
                            logging.error('Error: ', name)
                            self.post_alert()
                            self.send_email()

    def post_alert(self) -> None:
        logging.info(f'Posting alert on opsgenie...')
        headers = {'Content-Type': 'application/json', 'Authorization': f'GenieKey {self.GENIE_KEY}'}
        resp = requests.post(
            self.GENIE_URL,
            data=json.dumps(dict(
                message=self.DEFAULT_MESSAGE,
                priority=self.ALERT_PRIORITY,
                description=self.DESCRIPTION.format(node_ip=os.environ.get('NODE_IP')),
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
                'text': self.DESCRIPTION.format(node_ip=os.environ.get('NODE_IP')),
            }
        )
        logging.info(
            f'Request to mail gun API completed with Status code: {resp.status_code} and Response: {resp.text}'
        )


def run(dns_list: str) -> None:
    verifier = DNSVerifier()
    verifier.verify_dns(dns_list)


if __name__ == '__main__':
    dns_list = sys.argv[1]
    run(dns_list)
