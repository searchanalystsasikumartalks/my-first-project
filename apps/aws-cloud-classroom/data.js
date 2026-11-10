'use strict';
const LESSONS = [
  {
    "id": "cloud",
    "name": "Cloud basics",
    "category": "Basics",
    "title": "What is the cloud?",
    "explanation": "Use computing resources over the internet when you need them. Instead of buying your own server, you can access resources on demand.",
    "analogy": "Think of using electricity from a utility instead of buying a generator for your home. You still need to monitor your cloud spending.",
    "caution": "The frontend is the screen a user sees. The backend handles requests, business logic and data access. This app is frontend only.",
    "url": "https://aws.amazon.com/what-is-cloud-computing/"
  },
  {
    "id": "regions",
    "name": "Regions & AZs",
    "category": "Basics",
    "title": "Where does your application run?",
    "explanation": "A Region is a separate geographical area containing multiple distinct Availability Zones. Deploying across multiple AZs can improve availability.",
    "analogy": "Think of keeping supplies in separate warehouses rather than storing everything in a single building.",
    "caution": "Multi-AZ does not automatically solve every failure. Plan your application architecture, replication and recovery.",
    "url": "https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"
  },
  {
    "id": "iam",
    "name": "IAM",
    "category": "Security",
    "title": "Who can do what?",
    "explanation": "Identity and Access Management controls permissions for AWS resources. Least privilege means granting only the permissions needed for a task.",
    "analogy": "Think of giving each employee an access card only for the rooms they need.",
    "caution": "Do not use the root account for everyday work. Use MFA, roles and temporary credentials. Never put secret access keys in frontend code.",
    "url": "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html"
  },
  {
    "id": "ec2",
    "name": "EC2",
    "category": "Compute",
    "title": "A virtual server in the cloud",
    "explanation": "An EC2 instance is a virtual server. You can manage its operating system, applications and updates. Choose an instance type to suit your workload.",
    "analogy": "Think of renting a shop and managing its stock, staff and maintenance yourself.",
    "caution": "Storage and other charges may continue after you stop an EC2 instance. Security groups control network traffic.",
    "url": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html"
  },
  {
    "id": "lambda",
    "name": "Lambda",
    "category": "Compute",
    "title": "Run code in response to events",
    "explanation": "Lambda runs code without requiring you to manage servers directly. Events such as HTTP requests or file uploads can trigger a function.",
    "analogy": "Think of a kitchen station that starts working when an order arrives.",
    "caution": "Serverless does not mean there are no servers. Learn about time limits, permissions, concurrency and cold starts.",
    "url": "https://docs.aws.amazon.com/lambda/latest/dg/welcome.html"
  },
  {
    "id": "s3",
    "name": "S3",
    "category": "Storage",
    "title": "Object storage for files",
    "explanation": "Amazon S3 stores objects in buckets. It is useful for images, backups and static assets.",
    "analogy": "Think of labelled file boxes: each object has a key that identifies it.",
    "caution": "S3 is not a relational database. Keep buckets private and grant only the access that is needed.",
    "url": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html"
  },
  {
    "id": "rds",
    "name": "RDS",
    "category": "Data",
    "title": "A managed relational database",
    "explanation": "RDS simplifies setting up, operating and scaling a relational database. It is useful for applications that need SQL and related tables.",
    "analogy": "Think of an accounting book with linked tables for customers, orders and payments.",
    "caution": "Managed does not mean responsibility-free. You still plan schemas, queries, access permissions, retention and recovery.",
    "url": "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html"
  },
  {
    "id": "dynamodb",
    "name": "DynamoDB",
    "category": "Data",
    "title": "Key-value and document data",
    "explanation": "DynamoDB is a serverless, fully managed NoSQL database. Partition keys and access patterns are important design choices.",
    "analogy": "Think of an organised shelf where the right reference code helps you find an item.",
    "caution": "DynamoDB is not always a replacement for RDS. Choose based on your data relationships, queries and workload.",
    "url": "https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html"
  },
  {
    "id": "api",
    "name": "API Gateway",
    "category": "Network",
    "title": "A gateway between frontend and backend",
    "explanation": "API Gateway lets you create HTTP, REST and WebSocket APIs. It can send client requests to backend integrations such as Lambda.",
    "analogy": "Think of a restaurant counter passing an order to the kitchen.",
    "caution": "Having an API does not provide authentication by itself. Configure authorization, validation, throttling and error handling.",
    "url": "https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html"
  },
  {
    "id": "vpc",
    "name": "VPC",
    "category": "Network",
    "title": "Your own virtual network",
    "explanation": "A VPC lets you define a virtual network for AWS resources. Use subnets, routes and gateways to manage its layout.",
    "analogy": "Think of the roads, entrances and separate areas within a campus.",
    "caution": "Being in a public subnet alone does not give a resource internet access. Routes, IP addresses and security rules must also be configured appropriately.",
    "url": "https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html"
  },
  {
    "id": "cdn",
    "name": "CloudFront & DNS",
    "category": "Network",
    "title": "A faster path for content",
    "explanation": "Route 53 DNS helps resolve a domain name to an endpoint. CloudFront can cache content at edge locations and serve it closer to users.",
    "analogy": "Think of DNS as an address book and a CDN as a nearby distribution centre.",
    "caution": "Plan cache expiry and invalidation. A CloudFront origin can be S3, an HTTP server or another supported source.",
    "url": "https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html"
  },
  {
    "id": "ops",
    "name": "Monitoring & cost",
    "category": "Security",
    "title": "Is it working? What does it cost?",
    "explanation": "Use CloudWatch metrics, logs and alarms to observe your application. AWS Budgets can alert you about cost or usage thresholds.",
    "analogy": "Think of a vehicle dashboard alongside a monthly spending tracker.",
    "caution": "A budget alert is not a hard spending cap. Under the shared responsibility model, AWS protects cloud infrastructure. Your responsibilities for data and configuration depend on the service.",
    "url": "https://aws.amazon.com/compliance/shared-responsibility-model/"
  }
];
const QUIZ = [
  {
    "q": "Which service is suitable for storing images and backup files?",
    "a": [
      "S3",
      "IAM",
      "Route 53"
    ],
    "correct": 0,
    "why": "S3 is object storage: files are stored as objects in buckets."
  },
  {
    "q": "Should you put an AWS secret access key in frontend JavaScript?",
    "a": [
      "Yes, if the code is minified",
      "No",
      "It is fine for a demo"
    ],
    "correct": 1,
    "why": "Users can inspect browser code. Never put secrets in the frontend."
  },
  {
    "q": "Which service runs event-driven code without requiring you to manage servers?",
    "a": [
      "Route 53",
      "S3",
      "Lambda"
    ],
    "correct": 2,
    "why": "Lambda runs code in response to events. AWS manages the servers."
  },
  {
    "q": "Does a budget alert automatically enforce a hard spending cap?",
    "a": [
      "Always",
      "No",
      "Only in the Free Tier"
    ],
    "correct": 1,
    "why": "An alert is a notification. It is not a hard spending cap."
  },
  {
    "q": "You need SQL and related tables. Which service should you evaluate first?",
    "a": [
      "CloudFront",
      "RDS",
      "IAM"
    ],
    "correct": 1,
    "why": "RDS provides managed relational databases. Choose an engine that suits your workload."
  },
  {
    "q": "What does least privilege mean?",
    "a": [
      "Admin access for everyone",
      "No permissions at all",
      "Only the permissions needed"
    ],
    "correct": 2,
    "why": "Granting only the access needed for a task reduces risk."
  }
];
if(typeof module!=='undefined') module.exports={LESSONS,QUIZ};
