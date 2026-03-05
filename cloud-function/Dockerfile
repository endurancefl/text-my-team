FROM public.ecr.aws/lambda/python:3.12

# No system library installation needed — DocRaptor renders PDFs remotely
# (Removed: pango, cairo, gdk-pixbuf2, harfbuzz, fontconfig, freetype)

# Copy requirements and install Python dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/
COPY docraptor_service.py ${LAMBDA_TASK_ROOT}/
COPY marvin-knowledge.md ${LAMBDA_TASK_ROOT}/

# Copy assets and templates (Jinja2 renders locally, sends HTML to DocRaptor)
COPY assets/ ${LAMBDA_TASK_ROOT}/assets/
COPY templates/ ${LAMBDA_TASK_ROOT}/templates/

# Font installation no longer needed at OS level — fonts are embedded as base64 in HTML

# Set the handler
CMD ["lambda_function.lambda_handler"]
