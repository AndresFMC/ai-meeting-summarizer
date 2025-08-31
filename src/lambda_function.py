# src/lambda_function.py

import json
import boto3
import requests
import time
import uuid
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage

# --- Clientes de AWS (se definen fuera del handler para reutilización) ---
# Esto es una optimización de rendimiento para Lambda.
s3_client = boto3.client('s3')
transcribe_client = boto3.client('transcribe')

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
        LanguageCode='es-US' 
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

def get_summary_from_bedrock(transcript):
    """Envía la transcripción a Bedrock y obtiene un análisis."""
    llm = ChatBedrock(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        model_kwargs={"temperature": 0.1}
    )
    
    prompt = f"""
    Human: Basado en la siguiente transcripción de una reunión, por favor, genera un análisis estructurado con tres secciones claras: "Resumen Ejecutivo", "Puntos de Acción" (con la persona asignada si se menciona), y "Decisiones Clave". Si alguna sección no tiene contenido, indícalo.

    Aquí está la transcripción:
    <transcripcion>
    {transcript}
    </transcripcion>

    Assistant:
    """
    
    message = HumanMessage(content=prompt)
    response = llm.invoke([message])
    return response.content

# --- El Handler Principal de Lambda ---
# Esta es la función que AWS Lambda ejecutará.

def lambda_handler(event, context):
    """
    Función principal que se activa con un evento de API Gateway.
    Espera un body JSON con: {"bucket_name": "...", "object_name": "..."}
    """
    print(f"Evento recibido: {event}")

    try:
        # 1. Parsear los datos de entrada del evento de API Gateway
        # El body llega como un string, así que necesitamos convertirlo a un diccionario
        body = json.loads(event.get('body', '{}'))
        bucket_name = body.get('bucket_name')
        object_name = body.get('object_name')

        if not bucket_name or not object_name:
            raise ValueError("Faltan los parámetros 'bucket_name' o 'object_name' en el body.")

        print(f"Procesando archivo: s3://{bucket_name}/{object_name}")

        # 2. Ejecutar el pipeline de IA (las mismas funciones que antes)
        transcription_job = start_transcription_job(object_name, bucket_name)
        final_transcript = get_transcription_result(transcription_job)
        summary = get_summary_from_bedrock(final_transcript)
        
        print(f"Análisis generado con éxito.")

        # 3. Devolver una respuesta exitosa (formato requerido por API Gateway)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*' # Permite que cualquier web llame a nuestra API
            },
            'body': json.dumps({
                'summary': summary,
                'transcript': final_transcript
            })
        }

    except Exception as e:
        print(f"Error durante la ejecución: {e}")
        # 4. Devolver una respuesta de error (formato requerido por API Gateway)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }