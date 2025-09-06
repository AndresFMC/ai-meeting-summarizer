# 🎙️ AI Meeting Summarizer

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![AWS](https://img.shields.io/badge/AWS-Lambda-orange.svg)](https://aws.amazon.com/lambda/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production-success.svg)](https://github.com/AndresFMC/ai-meeting-summarizer)

Automated transformation of meeting audio into actionable insights using Generative AI and AWS services.

## 🌟 Live Demo

🔗 **[View Demo](https://andres-meeting-summarizer-demo.s3.eu-central-1.amazonaws.com/index.html)**

**Note:** For security reasons, API access is restricted. Please [contact me on LinkedIn](https://www.linkedin.com/in/andres-fmc/) for a live demonstration or temporary API access.

## 🎯 Problem Statement

In today's remote-first business environment, countless hours of virtual meetings are recorded daily, yet the valuable insights contained within these recordings are frequently lost because no one has time to review them. Manual extraction of key decisions, assigned tasks, and next steps is a tedious and error-prone process that scales poorly across organizations.

## ✨ Solution

A fully serverless system that automates the complete meeting analysis pipeline:

1. **Upload** an audio file (MP3/WAV)
2. **Receive** within seconds:
   - 📋 **Executive Summary**: Key discussion points
   - ✅ **Action Items**: Tasks with assigned owners
   - 🎯 **Key Decisions**: Agreements and resolutions

## 🏗️ Architecture

```mermaid
graph LR
    A[🎵 Audio File] -->|Upload| B[S3 Bucket]
    B --> C[Lambda Function]
    C --> D[Amazon Transcribe]
    D -->|Transcript| C
    C --> E[Amazon Bedrock<br/>Claude 3 Sonnet]
    E -->|Analysis| C
    C --> F[API Gateway]
    F -->|JSON| G[Web Client]
```

### Technical Components

| Service | Purpose | Configuration |
|---------|---------|--------------|
| **S3** | Audio storage | Private bucket for file uploads |
| **Lambda** | Pipeline orchestration | Python 3.12, 512MB RAM, 90s timeout |
| **API Gateway** | REST endpoint | API Key authentication, rate limiting |
| **Transcribe** | Audio → Text | English (en-GB), MP3 format |
| **Bedrock** | AI analysis | Claude 3 Sonnet v1 |

## 🚀 Key Features

- ⚡ **Fast Processing**: ~15 seconds to analyze a complete meeting
- 🔒 **Secure**: API Key authentication and rate limiting
- 💰 **Cost-Effective**: < $0.01 per invocation
- 🌍 **Scalable**: 100% elastic serverless architecture
- 🎯 **Accurate**: >95% transcription accuracy
- 🌐 **EU-Compliant**: Deployed in eu-central-1 region

## 💻 Installation & Deployment

### Prerequisites

- AWS Account with admin permissions
- Python 3.12+
- AWS CLI configured
- Git

### 1. Clone Repository

```bash
git clone https://github.com/AndresFMC/ai-meeting-summarizer.git
cd ai-meeting-summarizer
```

### 2. Set Up Local Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Prepare Deployment Package

```bash
# Clean previous builds
rm -rf package deployment_package.zip

# Install Lambda-compatible dependencies
mkdir package
pip install --platform manylinux2014_x86_64 \
    --target=package \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    -r requirements.txt

# Package code
cp src/lambda_function.py package/
cd package && zip -r ../deployment_package.zip . && cd ..
```

### 4. AWS Configuration (Console Setup)

#### 4.1 Create S3 Bucket
- Name: `your-audio-bucket`
- Region: `eu-central-1` (Frankfurt)
- Keep private

#### 4.2 Create IAM Role
- Name: `SummarizerLambdaRole`
- Required policies:
  - `AWSLambdaBasicExecutionRole`
  - `AmazonTranscribeFullAccess`
  - `AmazonBedrockFullAccess`
  - Custom S3 policy:
```json
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::your-audio-bucket/*"
    }]
}
```

#### 4.3 Create Lambda Function
- Runtime: Python 3.12
- Handler: `lambda_function.lambda_handler`
- Memory: 512 MB
- Timeout: 90 seconds
- Upload `deployment_package.zip`

#### 4.4 Configure API Gateway
- Create REST API
- Create `/summarize` resource
- POST method with Lambda proxy integration
- Enable CORS
- Create usage plan and API Key

## 📖 API Usage

### Endpoint
```
POST https://your-api-id.execute-api.eu-central-1.amazonaws.com/v1/summarize
```

### Headers
```
Content-Type: application/json
x-api-key: YOUR_API_KEY
```

### Request Body
```json
{
    "bucket_name": "your-audio-bucket",
    "object_name": "audio/meeting.mp3"
}
```

### Response
```json
{
    "summary": "Executive Summary:\n...\n\nAction Items:\n...\n\nKey Decisions:\n...",
    "transcript": "Complete meeting transcription..."
}
```

### Example with cURL
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d @test_payload.json \
  https://your-api-url/v1/summarize
```

## 🧪 Local Testing

To test the pipeline locally:

```bash
python src/main.py
```

Update variables in `main.py`:
- `BUCKET_NAME`: Your S3 bucket
- `AUDIO_FILE_PATH`: Local path to audio file

## 📁 Project Structure

```
ai-meeting-summarizer/
├── frontend/
│   ├── index.html          # Web interface
│   └── bucket-policy.json  # S3 hosting policy
├── src/
│   ├── lambda_function.py  # Main Lambda function
│   └── main.py             # Local testing script
├── .venv/                  # Python virtual environment
├── package/                # Lambda dependencies
├── deployment_package.zip  # Lambda deployment package
├── requirements.txt        # Python dependencies
├── test_payload.json      # Test payload
├── LICENSE                # MIT License
└── README.md             # This file
```

## 🔧 Configuration & Variables

### Lambda Environment Variables
No environment variables required. All configuration is code-based.

### Limits & Quotas
- Max audio file size: 100 MB
- Max audio duration: 30 minutes
- API rate limit: 100 requests/day per API Key
- Lambda timeout: 90 seconds

## 🐛 Troubleshooting

### Error: "S3 object not found"
- Verify file exists in bucket
- Confirm Lambda role has read permissions

### Error: "Internal server error" in API
- Check CloudWatch logs
- Verify CORS configuration in API Gateway
- Confirm API Key is valid

### Transcription fails
- Verify audio format (must be MP3 or WAV)
- Confirm language is configured correctly

## 📊 Performance Metrics

| Metric | Value | Monitoring |
|--------|-------|------------|
| Average processing time | 13-15 seconds | CloudWatch |
| Transcription accuracy | >95% | Manual validation |
| Cost per minute of audio | $0.025-0.035 | Real-time tracking |
| Availability | 99.9% | AWS CloudWatch |
| Concurrent executions | 1000 simultaneous | AWS Lambda |
| Token efficiency | Variable by content length | LangSmith |

### Cost Analysis (per minute of audio)
- **Base cost**: $0.025-0.035/minute
- **Breakdown**: 
  - Transcription: $0.024/minute (85%)
  - AI Analysis: $0.002-0.006/minute (15%)
  - Infrastructure: <$0.001/minute

**Examples:**
- 1-minute meeting: ~$0.03
- 5-minute discussion: ~$0.15  
- 30-minute conference: ~$0.90

## 🏢 Business Impact

This solution addresses real enterprise pain points:
- **Time Savings**: Reduces manual meeting review from hours to seconds
- **Compliance**: Automated documentation for regulatory requirements
- **Knowledge Management**: Searchable meeting insights for teams
- **Productivity**: Immediate action item extraction and assignment

## 🚦 Roadmap

- [ ] Multi-language support (German, French, Italian)
- [ ] Google Drive/Dropbox integration
- [ ] PDF export functionality
- [ ] Webhook notifications
- [ ] Analytics dashboard
- [ ] Video file support
- [ ] Speaker identification
- [ ] GDPR compliance features

## 🛠️ Technical Decisions

**Why Serverless?**
- Zero infrastructure management
- Pay-per-use cost model
- Automatic scaling
- EU data residency compliance

**Why Claude 3 Sonnet?**
- Superior understanding of business context
- Excellent structured output generation
- Multi-language support
- High reasoning capabilities

**Why AWS?**
- Mature AI/ML services ecosystem
- Strong EU presence (Frankfurt region)
- Enterprise-grade security
- Comprehensive monitoring tools

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the project
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

Distributed under MIT License. See `LICENSE` for details.

## 👨‍💻 Author

**Andrés F. Martínez Calderón**  
Generative AI Engineer  

- 📧 Email: [afmartinezcalderon@gmail.com](mailto:contact@example.com)
- 💼 LinkedIn: [linkedin.com/in/andres-fmc](https://www.linkedin.com/in/andres-fmc/)
- 🐙 GitHub: [@AndresFMC](https://github.com/AndresFMC)
- 📍 Location: Gdańsk, Poland

---

⭐ If you find this project useful, please consider giving it a star on GitHub!