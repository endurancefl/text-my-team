FROM public.ecr.aws/lambda/python:3.12

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

# Copy assets and templates
COPY assets/ ${LAMBDA_TASK_ROOT}/assets/
COPY templates/ ${LAMBDA_TASK_ROOT}/templates/

# Install custom fonts (Dancing Script for e-signatures) and rebuild font cache
RUN mkdir -p /usr/share/fonts/custom && \
    cp ${LAMBDA_TASK_ROOT}/assets/fonts/*.ttf /usr/share/fonts/custom/ && \
    fc-cache -f -v

# Set the handler
CMD ["lambda_function.lambda_handler"]
