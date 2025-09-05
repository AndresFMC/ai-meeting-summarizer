# src/lambda_function.py

import json
import boto3
import requests
import time
import uuid
import os
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
from langsmith import Client
from langchain.callbacks.tracers.langchain import LangChainTracer

# --- Clientes de AWS (se definen fuera del handler para reutilización) ---
# Esto es una optimización de rendimiento para Lambda.
s3_client = boto3.client('s3')
transcribe_client = boto3.client('transcribe')
cloudwatch = boto3.client('cloudwatch')

# Configuración de LangSmith (opcional)
langsmith_api_key = os.environ.get('LANGSMITH_API_KEY')
if langsmith_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = "ai-meeting-summarizer"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://eu.api.smith.langchain.com"
    langsmith_enabled = True
    try:
        langsmith_client = Client()
        print("✅ LangSmith configurado correctamente")
    except Exception as e:
        langsmith_enabled = False
        print(f"⚠️ Error configurando LangSmith: {e}")
else:
    langsmith_enabled = False
    print("ℹ️ LangSmith no configurado - funcionando normalmente")

# --- Funciones Lógicas (las mismas que antes) ---
# Estas funciones no cambian, ya que son modulares.

def start_transcription_job(object_name, bucket_name):
    """Inicia un trabajo de transcripción en Amazon Transcribe."""
    job_name = f"transcription-job-{uuid.uuid4()}"
    job_uri = f"s3://{bucket_name}/{object_name}"
    
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': job_uri},
        MediaFormat='mp3',
        LanguageCode='en-GB' 
    )
    return job_name

def get_transcription_result(job_name):
    """Espera y obtiene el resultado de un trabajo de transcripción."""
    while True:
        status_response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        job_status = status_response['TranscriptionJob']['TranscriptionJobStatus']
        
        if job_status in ['COMPLETED', 'FAILED']:
            if job_status == 'COMPLETED':
                transcript_uri = status_response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                response = requests.get(transcript_uri)
                response.raise_for_status()
                result = response.json()
                return result['results']['transcripts'][0]['transcript']
            else:
                failure_reason = status_response.get('FailureReason')
                raise Exception(f"El trabajo de transcripción falló: {failure_reason}")
        
        time.sleep(5) # Reducimos la espera para la Lambda

def get_summary_from_bedrock_with_tracking(transcript, request_id):
    """Envía la transcripción a Bedrock con tracking opcional de LangSmith."""
    
    callbacks = []
    
    # Solo usar LangSmith si está disponible y configurado
    if langsmith_enabled:
        try:
            tracer = LangChainTracer(
                project_name="ai-meeting-summarizer",
                client=langsmith_client
            )
            callbacks = [tracer]
            print("🔍 Tracking con LangSmith activo")
        except Exception as e:
            print(f"⚠️ Error configurando LangSmith tracer: {e}")
    
    # Configurar LLM
    llm = ChatBedrock(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        model_kwargs={"temperature": 0.1},
        callbacks=callbacks
    )
    
    prompt = f"""
    Human: Basado en la siguiente transcripción de una reunión, por favor, genera un análisis estructurado con tres secciones claras: "Resumen Ejecutivo", "Puntos de Acción" (con la persona asignada si se menciona), y "Decisiones Clave". Si alguna sección no tiene contenido, indícalo.

    Aquí está la transcripción:
    <transcripcion>
    {transcript}
    </transcripcion>

    Assistant:
    """
    
    start_time = time.time()
    
    # Ejecutar con metadata para LangSmith
    message = HumanMessage(content=prompt)
    response = llm.invoke(
        [message],
        config={
            "metadata": {
                "request_id": request_id,
                "transcript_length": len(transcript),
                "use_case": "meeting_summarization"
            },
            "tags": ["production", "meeting-analysis"]
        }
    )
    
    processing_time = time.time() - start_time
    
    # Calcular costos con datos precisos de Bedrock
    bedrock_costs = calculate_bedrock_costs_precise(prompt, response.content)
    
    if langsmith_enabled:
        print(f"📊 LangSmith: {bedrock_costs['input_tokens']} tokens in, {bedrock_costs['output_tokens']} tokens out")
    
    return response.content, bedrock_costs, processing_time

# --- El Handler Principal de Lambda ---
# Esta es la función que AWS Lambda ejecutará.

# --- El Handler Principal de Lambda (VERSIÓN FINAL Y ROBUSTA) ---

def lambda_handler(event, context):
    start_time = time.time()
    request_id = context.aws_request_id
    print(f"Evento recibido: {event}")

    try:
        # 1. Parsear los datos de entrada
        body = json.loads(event.get('body', '{}'))
        bucket_name = body.get('bucket_name')
        object_name = body.get('object_name')

        if not bucket_name or not object_name:
            raise ValueError("Faltan los parámetros 'bucket_name' o 'object_name' en el body.")

        # 2. Verificación de Pre-condición: Asegurarse de que el objeto existe y es accesible
        # Esto no solo depura, sino que previene errores y parece solucionar un problema de timing de AWS.
        try:
            print(f"Verificando la existencia del objeto: s3://{bucket_name}/{object_name}")
            head_response = s3_client.head_object(Bucket=bucket_name, Key=object_name)
            file_size = head_response['ContentLength']
            print("Verificación exitosa. El objeto existe y es accesible.")
        except Exception as s3_error:
            print(f"Fallo en la verificación de S3: {s3_error}")
            raise Exception(f"El objeto S3 especificado no se encuentra o no se puede acceder: s3://{bucket_name}/{object_name}")

        # 3. Ejecutar el pipeline de IA
        print("Iniciando pipeline de IA...")
        transcription_job = start_transcription_job(object_name, bucket_name)
        final_transcript = get_transcription_result(transcription_job)
        summary, bedrock_costs, bedrock_time = get_summary_from_bedrock_with_tracking(final_transcript, request_id)
        
        # Calcular métricas finales
        processing_time = time.time() - start_time
        word_count = len(final_transcript.split())
        costs = calculate_estimated_costs(file_size, word_count, processing_time)
        # Reemplazar estimación de Bedrock con costo real
        costs['bedrock'] = bedrock_costs['total_bedrock_cost']
        costs['total'] = sum(costs.values())

        # Enviar métricas a CloudWatch
        send_metrics_to_cloudwatch(costs, processing_time, word_count, request_id)

        print(f"Análisis generado con éxito. Costo estimado: ${costs['total']:.6f}")

        # 4. Devolver una respuesta exitosa
        return {
            'statusCode': 200,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({ 
                'summary': summary, 
                'transcript': final_transcript,
                'metrics': {
                    'processing_time': round(processing_time, 2),
                    'bedrock_time': round(bedrock_time, 2),
                    'word_count': word_count,
                    'estimated_cost': round(costs['total'], 6),
                    'cost_breakdown': {k: round(v, 6) for k, v in costs.items()},
                    'file_size_mb': round(file_size / 1024 / 1024, 2),
                    'token_usage': {
                        'input_tokens': bedrock_costs['input_tokens'],
                        'output_tokens': bedrock_costs['output_tokens']
                    }
                }
})
        }

    except Exception as e:
        print(f"Error durante la ejecución: {e}")
        return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': str(e)})
        }
    

# Funciones para definir los costes usando CloudWatch
def calculate_estimated_costs(file_size_bytes, transcript_word_count, processing_time):
    """
    Calcula costos estimados basado en el uso real de servicios AWS.
    Precios de eu-central-1 (Enero 2025)
    """
    costs = {}
    
    # Lambda costs: $0.0000166667 por GB-segundo + $0.0000002 por request
    lambda_gb_seconds = (512 / 1024) * processing_time  # 512MB = 0.5GB
    costs['lambda'] = (lambda_gb_seconds * 0.0000166667) + 0.0000002
    
    # Transcribe costs: $0.024 por minuto de audio
    # Estimación: 1MB ≈ 1 minuto de audio MP3 calidad media
    audio_minutes = (file_size_bytes / 1024 / 1024)  # MB to minutes
    costs['transcribe'] = audio_minutes * 0.024
    
    # Bedrock costs (Claude 3 Sonnet)
    # Input: $0.003 per 1K tokens, Output: $0.015 per 1K tokens
    # Estimación: 1 palabra ≈ 1.3 tokens
    input_tokens = transcript_word_count * 1.3 + 200  # +200 tokens del prompt
    output_tokens = 300  # Estimación conservadora del resumen
    costs['bedrock'] = (input_tokens / 1000 * 0.003) + (output_tokens / 1000 * 0.015)
    
    # S3 costs (muy bajo para este caso)
    costs['s3'] = 0.0001
    
    # API Gateway: $3.50 per million requests
    costs['api_gateway'] = 0.0000035
    
    costs['total'] = sum(costs.values())
    return costs
    
def send_metrics_to_cloudwatch(costs, processing_time, word_count, request_id):
    """Envía métricas de costo y rendimiento a CloudWatch."""
    try:
        cloudwatch.put_metric_data(
            Namespace='MeetingSummarizer',
            MetricData=[
                {
                    'MetricName': 'TotalCost',
                    'Value': costs['total'],
                    'Unit': 'None',
                    'Dimensions': [{'Name': 'RequestId', 'Value': request_id}]
                },
                {
                    'MetricName': 'ProcessingTime',
                    'Value': processing_time,
                    'Unit': 'Seconds'
                },
                {
                    'MetricName': 'WordCount',
                    'Value': word_count,
                    'Unit': 'Count'
                }
            ]
        )
        print(f"Métricas enviadas a CloudWatch: ${costs['total']:.6f}")
    except Exception as e:
        print(f"Error enviando métricas: {e}")

def estimate_tokens(text):
    """Estima tokens de forma más precisa. 1 palabra ≈ 1.3 tokens para Claude."""
    return len(text.split()) * 1.3

def calculate_bedrock_costs_precise(input_text, output_text):
    """Calcula costos de Bedrock basado en texto real."""
    input_tokens = estimate_tokens(input_text)
    output_tokens = estimate_tokens(output_text)
    
    # Claude 3 Sonnet pricing eu-central-1
    input_cost = (input_tokens / 1000) * 0.003
    output_cost = (output_tokens / 1000) * 0.015
    
    return {
        'input_tokens': int(input_tokens),
        'output_tokens': int(output_tokens),
        'input_cost': input_cost,
        'output_cost': output_cost,
        'total_bedrock_cost': input_cost + output_cost
    }