# AWS-Clean Untagged Resources

This script will notify you on Slack and terminate/stop untagged EC2/RDS resources!

## 📚 Usage

The project is using Lambda to periodically check your AWS account for untagged or not persistent EC2, RDS & ECS with Fargate resources.
It has 3 possible behavior:
- *NOTIFY*: This mode will scan for untagged EC2/RDS instances and send a message on your Slack workspace
- *STOP*: This mode will scan for untagged EC2/RDS instances and stop them
- *TERMINATE*: This mode will scan for untagged EC2/RDS instances and terminate them

The Lambda will also check for resources tagged with a lifetime tag to be able to define from when a resource should be
terminated. For example if we have the tag `Lifetime`=`10`, it means that the resource should live at least 10 days and the
lambda won't stop/terminate this resource until the lifetime has been expired or `Lifetime`=`yyyy-mm-dd` to directly define
an expiration date for the resource.

### Package

Before deploying the lambda function you'll have to make a zip of your code like the following:

```sh
$ cd aws-clean-untagged-resources
```

Make sure that you've installed dependencies, if not you can use the following command:

```sh
$ pip3 install --target ./package -r requirements.txt
```

You're now able to zip your packages (you can skip this part if packages were already zipped:

```sh
cd package
zip -r ../../aws-clean-untagged-resources.zip .
cd ..
```

Now everytime you do some changes on your code you will have to zip your code like the following:

```sh
zip -g ../aws-clean-untagged-resources.zip *.py
```

Documentation sources: https://docs.aws.amazon.com/lambda/latest/dg/python-package.html#python-package-create-package-with-dependency

### 🚀 Deploy

You will need a S3 bucket in order to deploy the Lambda with Cloudformation
You will need to create a Slack webhook on your slack workspace

To deploy the function, replace the variables in the following commands:
```sh
$ aws cloudformation package --template-file template.yml --s3-bucket YOUR_DEPLOYMENT_BUCKET --s3-prefix YOUR_S3_PREFIX --output-template-file output.yaml
$ aws cloudformation deploy --template-file output.yaml --stack-name STACK_NAME --capabilities CAPABILITY_NAMED_IAM --parameter-overrides SlackWebHook=YOUR_SLACK_WEBHOOK_URL ScheduleExpression="cron(0 16 ? * THU *)" PersistentTagKey=MY_RESOURCE_TAG_NAME PersistentTagValue=MY_RESOURCE_TAG_VALUE Behavior=notify|stop|terminate AwsRegions=AWS_REGIONS
```
*Usage example*: If you want to notify on Slack about untagged resources on Thursday at 4pm and stop them on Sunday at 4pm you will need to deploy 2 stacks with the following:
```sh
$ aws cloudformation package --template-file template.yml --s3-bucket YOUR_DEPLOYMENT_BUCKET --s3-prefix YOUR_S3_PREFIX --output-template-file output.yaml
$ aws cloudformation deploy --template-file output.yaml --stack-name STACK_NAME-notify --capabilities CAPABILITY_NAMED_IAM --parameter-overrides SlackWebHook=YOUR_SLACK_WEBHOOK_URL ScheduleExpression="cron(0 16 ? * THU *)" PersistentTagKey=MY_RESOURCE_TAG_NAME PersistentTagValue=MY_RESOURCE_TAG_VALUE Behavior=notify AwsRegions=AWS_REGION1,AWS_REGION2 DesiredLifetimeTagKey=LIFETIME_TAG_NAME
$ aws cloudformation deploy --template-file output.yaml --stack-name STACK_NAME-stop --capabilities CAPABILITY_NAMED_IAM --parameter-overrides SlackWebHook=YOUR_SLACK_WEBHOOK_URL ScheduleExpression="cron(0 16 ? * SUN *)" PersistentTagKey=MY_RESOURCE_TAG_NAME PersistentTagValue=MY_RESOURCE_TAG_VALUE Behavior=stop AwsRegions=AWS_REGION1,AWS_REGION2 DesiredLifetimeTagKey=LIFETIME_TAG_NAME
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
