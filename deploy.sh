#!/bin/bash

# deploy.sh - Script de despliegue automatizado para AI Meeting Summarizer
# Compatible con macOS M1 y AWS Lambda

set -e  # Salir si cualquier comando falla

echo "🚀 Iniciando despliegue de AI Meeting Summarizer..."

# Variables de configuración
FUNCTION_NAME="AI-Meeting-Summarizer-Function"
REGION="eu-central-1"
PACKAGE_DIR="package"
ZIP_FILE="deployment_package.zip"

# Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ] || [ ! -d "src" ]; then
    echo "❌ Error: Ejecuta este script desde el directorio raíz del proyecto"
    echo "   Debe contener 'requirements.txt' y carpeta 'src/'"
    exit 1
fi

# Verificar que AWS CLI está configurado
if ! aws sts get-caller-identity --region $REGION > /dev/null 2>&1; then
    echo "❌ Error: AWS CLI no está configurado correctamente"
    echo "   Ejecuta: aws configure"
    exit 1
fi

echo "✅ Verificaciones iniciales completadas"

# Paso 1: Limpiar archivos anteriores
echo "🧹 Limpiando archivos anteriores..."
rm -rf $PACKAGE_DIR $ZIP_FILE
echo "   Limpieza completada"

# Paso 2: Crear directorio para el paquete
echo "📦 Creando paquete de despliegue..."
mkdir $PACKAGE_DIR

# Paso 3: Instalar dependencias compatibles con Lambda
echo "⬇️  Instalando dependencias para Lambda (esto puede tomar un momento)..."
pip install --platform manylinux2014_x86_64 \
    --target=$PACKAGE_DIR \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --upgrade \
    -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Error instalando dependencias"
    exit 1
fi

echo "   Dependencias instaladas correctamente"

# Paso 4: Copiar código fuente
echo "📋 Copiando código fuente..."
cp src/lambda_function.py $PACKAGE_DIR/

# Verificar que el archivo principal existe
if [ ! -f "$PACKAGE_DIR/lambda_function.py" ]; then
    echo "❌ Error: No se pudo copiar lambda_function.py"
    exit 1
fi

echo "   Código copiado correctamente"

# Paso 5: Crear archivo ZIP
echo "🗜️  Creando archivo ZIP..."
cd $PACKAGE_DIR
zip -r ../$ZIP_FILE . -q
cd ..

# Verificar que el ZIP se creó
if [ ! -f "$ZIP_FILE" ]; then
    echo "❌ Error: No se pudo crear el archivo ZIP"
    exit 1
fi

ZIP_SIZE=$(du -h $ZIP_FILE | cut -f1)
echo "   ZIP creado: $ZIP_FILE ($ZIP_SIZE)"

# Paso 6: Verificar que la función Lambda existe
echo "🔍 Verificando función Lambda..."
if ! aws lambda get-function --function-name $FUNCTION_NAME --region $REGION > /dev/null 2>&1; then
    echo "❌ Error: La función Lambda '$FUNCTION_NAME' no existe en la región $REGION"
    echo "   Créala primero en AWS Console"
    exit 1
fi

echo "   Función Lambda encontrada"

# Paso 7: Subir ZIP al bucket S3
S3_BUCKET="andres-summarizer-audio-uploads-1"
S3_KEY="lambda-packages/$ZIP_FILE"

echo "☁️ Subiendo ZIP a S3..."
aws s3 cp $ZIP_FILE s3://$S3_BUCKET/lambda-packages/ --region $REGION

if [ $? -ne 0 ]; then
echo "❌ Error subiendo ZIP a S3"
exit 1
fi

echo " ZIP subido a S3: s3://$S3_BUCKET/lambda-packages/$ZIP_FILE"

# Paso 8: Actualizar Lambda desde S3
echo "🔄 Actualizando función Lambda desde S3..."
aws lambda update-function-code \
--function-name $FUNCTION_NAME \
--s3-bucket $S3_BUCKET \
--s3-key lambda-packages/$ZIP_FILE \
--region $REGION \
--no-cli-pager

if [ $? -ne 0 ]; then
echo "❌ Error actualizando Lambda desde S3"
exit 1
fi

echo " Función Lambda actualizada correctamente"

# Paso 9: Verificar que la actualización fue exitosa
echo "✅ Verificando despliegue..."
LAST_MODIFIED=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.LastModified' --output text)
echo "   Última modificación: $LAST_MODIFIED"

# Paso 10: Limpiar archivos temporales (opcional)
echo "🧹 Limpiando archivos temporales..."
rm -rf $PACKAGE_DIR $ZIP_FILE
echo "   Limpieza completada"

echo ""
echo "🎉 ¡Despliegue completado exitosamente!"
echo "📝 Función: $FUNCTION_NAME"
echo "🌍 Región: $REGION"
echo "⏰ Hora: $(date)"
echo ""
echo "🔗 Puedes probar tu función en:"
echo "   https://console.aws.amazon.com/lambda/home?region=$REGION#/functions/$FUNCTION_NAME"
echo ""
echo "💡 Tip: Para ver logs en tiempo real:"
echo "   aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $REGION"