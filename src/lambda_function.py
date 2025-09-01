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

# --- El Handler Principal de Lambda (VERSIÓN FINAL Y ROBUSTA) ---

def lambda_handler(event, context):
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
            s3_client.head_object(Bucket=bucket_name, Key=object_name)
            print("Verificación exitosa. El objeto existe y es accesible.")
        except Exception as s3_error:
            print(f"Fallo en la verificación de S3: {s3_error}")
            raise Exception(f"El objeto S3 especificado no se encuentra o no se puede acceder: s3://{bucket_name}/{object_name}")

        # 3. Ejecutar el pipeline de IA
        print("Iniciando pipeline de IA...")
        transcription_job = start_transcription_job(object_name, bucket_name)
        final_transcript = get_transcription_result(transcription_job)
        summary = get_summary_from_bedrock(final_transcript)
        
        print("Análisis generado con éxito.")

        # 4. Devolver una respuesta exitosa
        return {
            'statusCode': 200,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({ 'summary': summary, 'transcript': final_transcript })
        }

    except Exception as e:
        print(f"Error durante la ejecución: {e}")
        return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': str(e)})
        }