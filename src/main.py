# src/main.py

import boto3
import time
import uuid
import json
import requests
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage

import os
from dotenv import load_dotenv

# Cargar variables de entorno para desarrollo local
load_dotenv()

# Configurar LangSmith para local
LANGSMITH_ENDPOINT="https://eu.api.smith.langchain.com"
if os.getenv('LANGSMITH_API_KEY'):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = os.getenv('LANGSMITH_API_KEY')
    os.environ["LANGCHAIN_PROJECT"] = "AI-Meeting-Summarizer-dev"

# --- Configuración Inicial ---
# (Asegúrate de que tu AWS CLI esté configurado)
s3_client = boto3.client('s3')
transcribe_client = boto3.client('transcribe')

# Cambia estos valores por los tuyos
BUCKET_NAME = "andres-summarizer-audio-uploads-1" # El bucket que creaste
AUDIO_FILE_PATH = "/Users/andrew/VScodeProjects/ProyectosPersonales/audio-prueba-1.mp3" # La ruta local de tu archivo de audio

# --- Funciones Lógicas ---

def upload_to_s3(file_path, bucket_name):
    """Sube un archivo a S3 y devuelve el nombre del objeto."""
    object_name = f"audio/{uuid.uuid4()}.mp3"
    print(f"Subiendo archivo a s3://{bucket_name}/{object_name}...")
    s3_client.upload_file(file_path, bucket_name, object_name)
    print("Carga completa.")
    return object_name

def start_transcription_job(object_name, bucket_name):
    """Inicia un trabajo de transcripción en Amazon Transcribe."""
    job_name = f"transcription-job-{uuid.uuid4()}"
    job_uri = f"s3://{bucket_name}/{object_name}"
    
    print(f"Iniciando trabajo de transcripción: {job_name}...")
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': job_uri},
        MediaFormat='mp3',  # o 'wav'
        LanguageCode='es-US'  # o el idioma que corresponda
    )
    print("Trabajo iniciado.")
    return job_name

def get_transcription_result(job_name):
    """Espera y obtiene el resultado de un trabajo de transcripción."""
    print("Esperando a que la transcripción finalice...")
    while True:
        status_response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        job_status = status_response['TranscriptionJob']['TranscriptionJobStatus']
        
        if job_status in ['COMPLETED', 'FAILED']:
            print(f"Trabajo finalizado con estado: {job_status}")
            if job_status == 'COMPLETED':
                # La URI del transcript es una URL segura y temporal (prefirmada)
                transcript_uri = status_response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                
                # Usamos la librería 'requests' para descargar el contenido de la URL
                response = requests.get(transcript_uri)
                response.raise_for_status() # Lanza un error si la descarga falla
                
                # El contenido es un JSON que procesamos
                result = response.json()
                
                return result['results']['transcripts'][0]['transcript']
            else:
                print(f"El trabajo de transcripción falló: {status_response.get('FailureReason')}")
                return None
        
        # Esperar 10 segundos antes de volver a consultar el estado
        time.sleep(10)

def get_summary_from_bedrock(transcript):
    """Envía la transcripción a Bedrock (Claude 3) y obtiene un resumen."""
    print("Enviando transcripción a Bedrock para análisis...")
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
    
    print("Análisis recibido.")
    return response.content


# --- Flujo Principal de Ejecución ---
if __name__ == "__main__":
    # 1. Subir el audio a S3
    s3_object_name = upload_to_s3(AUDIO_FILE_PATH, BUCKET_NAME)
    
    # 2. Iniciar el trabajo de transcripción
    transcription_job = start_transcription_job(s3_object_name, BUCKET_NAME)
    
    # 3. Obtener el texto transcrito
    final_transcript = get_transcription_result(transcription_job)
    
    if final_transcript:
        print("\n--- TRANSCRIPCIÓN ---")
        print(final_transcript)
        
        # 4. Obtener el resumen de Bedrock
        summary = get_summary_from_bedrock(final_transcript)
        print("\n--- ANÁLISIS DE IA ---")
        print(summary)
    else:
        print("No se pudo obtener la transcripción.")