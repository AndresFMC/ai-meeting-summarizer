# 🚀 AI Meeting Summarizer & Action Item Extractor

A serverless AWS application that transcribes meetings, generates executive summaries, and automatically extracts actionable tasks using Generative AI.

---

## 🎯 The Business Problem

In today's fast-paced business environment, countless hours of virtual meetings are recorded. However, the value within these recordings is often lost as no one has the time to re-watch them. Manually extracting key decisions, assigned tasks, and next steps is a tedious, error-prone process that consumes valuable time that could be spent on more productive work.

## ✨ The Solution

This project is a fully serverless API that automates this process. A user can upload an audio file (e.g., `.mp3`, `.wav`) and receive a structured analysis of the meeting, including:

* **Executive Summary:** A concise paragraph covering the most important points of the discussion.
* **Action Items:** A clear, bulleted list of tasks, with the assigned owner if mentioned in the conversation.
* **Key Decisions:** A list of the most relevant decisions made during the meeting.

The application is designed from the ground up to be **scalable, secure, and cost-effective**, leveraging AWS cloud-native best practices.

---

## 🛠️ Architecture & Tech Stack

This project is built on a 100% serverless architecture, ensuring zero cost at low traffic levels (within the AWS Free Tier) and infinite scalability.

`[Architecture Diagram]`

### Core Components:

* **Frontend:** A simple static web interface (HTML + Vanilla JS) hosted on **Amazon S3** and delivered globally via **Amazon CloudFront**.
* **API:** A RESTful endpoint managed by **Amazon API Gateway**, secured with a Usage Plan and API Key to prevent abuse.
* **Compute:** An **AWS Lambda** function (Python 3.11 runtime) that orchestrates the entire workflow:
    1.  Generates a presigned S3 URL for secure, direct file uploads from the client.
    2.  Triggers **Amazon Transcribe** to start the audio-to-text transcription job.
    3.  Processes the transcription output with **Amazon Bedrock** (using the Claude 3 Sonnet model) for analysis (summarization, extraction, etc.).
* **Storage:**
    * **Amazon S3** for storing the input audio files and the output text results.
    * **Amazon DynamoDB** as the NoSQL database for storing job metadata and the final analysis results.

### Key Libraries & Tools:

* **`Boto3`**: The AWS SDK for Python to interact with AWS services.
* **`FastAPI`**: Used within the Lambda function for clean, predictable request/response handling.
* **`LangChain`**: For orchestrating prompts and interactions with the language model on Bedrock.

---

## ⚙️ Local Setup & Deployment

### Local Setup
To run a similar setup locally, you would typically follow these steps:

1.  Clone the repository: `git clone https://github.com/your-username/ai-meeting-summarizer.git`
2.  Create and activate a virtual environment: `python -m venv .venv && source .venv/bin/activate`
3.  Install dependencies: `pip install -r requirements.txt`
4.  Configure your local AWS credentials.

### AWS Deployment
The infrastructure is deployed on AWS. The core components (Lambda, API Gateway, S3, DynamoDB) are configured to work together in an event-driven fashion. This can be done via the AWS Management Console or, for best practices, defined as Infrastructure as Code using AWS SAM or Serverless Framework.

---
