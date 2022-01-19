import urllib.request
import json


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

	def get_text(self):
		return self.text

	def intro_text(self, region):
		self.text['blocks'].append({
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": ":globe_with_meridians: *" + region + "*"
			}
		})
		self.text['blocks'].append({
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": self.message
			}
		})

	def outro_text(self):
		self.text['blocks'].append({
			"text": {
				"text": ":robot_face: *Tag your resources with `" + self.tag_key + "=" + self.tag_value +
				"` if you want them to live!*" + "\n:robot_face: *You can also tag your resources with `" + self.lifetime_tag_key +
				"=x` with x a number of days, which means that your resources will live at least x days.*",
				"type": "mrkdwn"
			},
			"type": "section"
		})

	def no_resources_text(self):
		self.text['blocks'].append({
			"text": {
				"text": ":robot_face: No untagged resource here, good job!",
				"type": "mrkdwn"
			},
			"type": "section"
		})

	def section_header_text(self, name):
		self.text['blocks'].append({
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": name
			}
		})
		self.text['blocks'].append({
			"type": "divider"
		})

	def append_blocks(self, obj):
		self.text['blocks'].append(obj)

	def clean_blocks(self):
		self.text['blocks'] = []

	def request(self):
		req = urllib.request.Request(self.webhook_url, json.dumps(self.text).encode())
		urllib.request.urlopen(req)
