FROM public.ecr.aws/lambda/python:3.12

# Add Lambda Web Adapter for streaming support (activates when AWS_LWA_INVOKE_MODE is set)
COPY --from=public.ecr.aws/awsguru/aws-lambda-web-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter

# Install system dependencies required by WeasyPrint
# AL2023 uses dnf and ships Pango 1.54+ (WeasyPrint needs >= 1.44)
RUN dnf install -y \
    pango \
    cairo \
    gdk-pixbuf2 \
    libffi \
    fontconfig \
    freetype \
    harfbuzz \
    && dnf clean all

# Copy requirements and install Python dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/
COPY main.py ${LAMBDA_TASK_ROOT}/
COPY pdf_generator.py ${LAMBDA_TASK_ROOT}/
COPY marvin-knowledge.md ${LAMBDA_TASK_ROOT}/
COPY marvin_stream.py ${LAMBDA_TASK_ROOT}/

# Copy assets and templates
COPY assets/ ${LAMBDA_TASK_ROOT}/assets/
COPY templates/ ${LAMBDA_TASK_ROOT}/templates/

# Install custom fonts (Dancing Script for e-signatures) and rebuild font cache
RUN mkdir -p /usr/share/fonts/custom && \
    cp ${LAMBDA_TASK_ROOT}/assets/fonts/*.ttf /usr/share/fonts/custom/ && \
    fc-cache -f -v

# Set the handler
CMD ["lambda_function.lambda_handler"]
