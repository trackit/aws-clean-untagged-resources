# AWS-Clean Untagged Resources

This script will notify you on Slack and terminate/stop untagged EC2/RDS resources!

## 📚 Usage

The project is using Lambda to periodically check your AWS account for untagged EC2 and RDS instances.
It has 3 possible behavior:
- *NOTIFY*: This mode will scan for untagged EC2/RDS instances and send a message on your Slack workspace
- *STOP*: This mode will scan for untagged EC2/RDS instances and stop them
- *TERMINATE*: This mode will scan for untagged EC2/RDS instances and terminate them

### 🚀 Deploy

You will need a S3 bucket in order to deploy the Lambda with Cloudformation
You will need to create a Slack webhook on your slack workspace

To deploy the function, replace the variables in the following commands:
```sh
$ aws cloudformation package --template-file template.yml --s3-bucket YOUR_DEPLOYMENT_BUCKET --s3-prefix YOUR_S3_PREFIX --output-template-file output.yaml
$ aws cloudformation deploy --template-file output.yaml --stack-name STACK_NAME --capabilities CAPABILITY_NAMED_IAM --parameter-overrides SlackChannel=YOUR_SLACK_CHANNEL SlackWebHook=YOUR_SLACK_WEBHOOK_URL ScheduleExpression="cron(0 16 ? * THU *)" DesiredTagKey=MY_RESOURCE_TAG_NAME DesiredTagValue=MY_RESOURCE_TAG_VALUE Behavior=notify|stop|terminate AwsRegion=AWS_REGION
```
*Usage example*: If you want to notify on Slack about untagged resources on Thursday at 4pm and stop them on Sunday at 4pm you will need to deploy 2 stacks with the following:
```sh
$ aws cloudformation package --template-file template.yml --s3-bucket YOUR_DEPLOYMENT_BUCKET --s3-prefix YOUR_S3_PREFIX --output-template-file output.yaml
$ aws cloudformation deploy --template-file output.yaml --stack-name STACK_NAME-notify --capabilities CAPABILITY_NAMED_IAM --parameter-overrides SlackChannel=YOUR_SLACK_CHANNEL SlackWebHook=YOUR_SLACK_WEBHOOK_URL ScheduleExpression="cron(0 16 ? * THU *)" DesiredTagKey=MY_RESOURCE_TAG_NAME DesiredTagValue=MY_RESOURCE_TAG_VALUE Behavior=notify AwsRegion=AWS_REGION
$ aws cloudformation deploy --template-file output.yaml --stack-name STACK_NAME-stop --capabilities CAPABILITY_NAMED_IAM --parameter-overrides SlackChannel=YOUR_SLACK_CHANNEL SlackWebHook=YOUR_SLACK_WEBHOOK_URL ScheduleExpression="cron(0 16 ? * SUN *)" DesiredTagKey=MY_RESOURCE_TAG_NAME DesiredTagValue=MY_RESOURCE_TAG_VALUE Behavior=stop AwsRegion=AWS_REGION
```

### 💣 Destroy

```sh
$ aws cloudformation delete-stack STACK_NAME
```

## 🤝 Missing a specific feature?

Feel free to ask for the features you want! Our teams will be happy to add them!

## ❤️ Show your support

Give a ⭐️ if this project helped you!

## ✏️ Author

### 👤 Trackit
- Website: [trackit.io](www.trackit.io)

### 👥 About us

We are an Amazon Web Services Advanced Consulting Partner specializing in cloud management, consulting, and software development solutions based in Venice, CA.
