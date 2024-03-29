import logging
import urllib.request
import json


def section_header_text_fmt(name):
    return [{
        'type': 'header',
        'text': {
            'type': 'plain_text',
            'text': name
        }
    }, {
        'type': 'divider'
    }]


class Slack:
    _instance = None

    @staticmethod
    def get_instance(webhook_url=None, message=None, tag_key=None, tag_value=None, lifetime_tag_key=None):
        if Slack._instance is None:
            if message is None or tag_key is None or tag_value is None or lifetime_tag_key is None:
                raise Exception('Slack Instance need to be instantiated once')
            Slack._instance = Slack(webhook_url, message, tag_key, tag_value, lifetime_tag_key)
        return Slack._instance

    def __init__(self, webhook_url, message, tag_key, tag_value, lifetime_tag_key):
        self.webhook_url = webhook_url
        self.message = message
        self.tag_key = tag_key
        self.tag_value = tag_value
        self.lifetime_tag_key = lifetime_tag_key
        self.text = {"blocks": []}

    def not_persistent_resources_request(self, region):
        self.clean_blocks()
        self.text["blocks"].append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f':globe_with_meridians: *{region}*'
            }
        })
        self.text["blocks"].append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': "Every resources are correctly tagged for this region, well done!"
            }
        })
        if self.webhook_url:
            req = urllib.request.Request(self.webhook_url, json.dumps(self.text).encode())
            urllib.request.urlopen(req)
        else:
            logging.info('Slack Webhook URL not found.')

    def get_text(self):
        return self.text

    def intro_text(self, region):
        self.text["blocks"].append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f':globe_with_meridians: *{region}*'
            }
        })
        self.text["blocks"].append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': self.message
            }
        })

    def outro_text(self):
        self.text["blocks"].append({
            'text': {
                'text': f':robot_face: *Tag your resources with `{self.tag_key}={self.tag_value}`'
                        f'if you want them to live!*\n'
                        f':robot_face: *You can also tag your resources with `{self.lifetime_tag_key}=x`'
                        f'with x a number of days, which means that your resources will live at least x days or '
                        f'`{self.lifetime_tag_key}=yyyy-mm-dd` to define an expiration date for the resource.*\n',
                'type': 'mrkdwn'
            },
            'type': 'section'
        })

    def no_resources_text(self):
        self.text["blocks"].append({
            'text': {
                'text': ':robot_face: No untagged resource here, good job!',
                'type': 'mrkdwn'
            },
            'type': 'section'
        })

    def section_header_text(self, name):
        self.text["blocks"].append({
            'type': 'header',
            'text': {
                'type': 'plain_text',
                'text': name
            }
        })
        self.text["blocks"].append({
            'type': 'divider'
        })

    def append_blocks(self, obj):
        self.text["blocks"].append(obj)

    def extend_blocks(self, objs):
        self.text["blocks"].extend(objs)

    def clean_blocks(self):
        self.text["blocks"] = []

    def request(self):
        if self.webhook_url:
            req = urllib.request.Request(self.webhook_url, json.dumps(self.text).encode())
            urllib.request.urlopen(req)
        else:
            logging.info('Slack Webhook URL not found.')
