import json
import boto3

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    try:
        bucket_name = 'andres-summarizer-audio-uploads-1'
        prefix = 'audio/'
        
        # Listar objetos en S3
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )
        
        audio_files = []
        
        if 'Contents' in response:
            for obj in response['Contents']:
                # Solo archivos MP3/WAV, excluir carpetas
                if obj['Key'].endswith(('.mp3', '.wav')) and obj['Key'] != prefix:
                    file_info = {
                        'key': obj['Key'],
                        'name': obj['Key'].replace(prefix, ''),  # Quitar prefijo audio/
                        'size_mb': round(obj['Size'] / 1024 / 1024, 2),
                        'last_modified': obj['LastModified'].isoformat()
                    }
                    audio_files.append(file_info)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'files': audio_files,
                'count': len(audio_files)
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }