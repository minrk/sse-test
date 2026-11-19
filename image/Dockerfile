FROM python:3.14-slim
RUN python3 -m pip install --no-cache tornado
COPY ./ /src/
WORKDIR /src/
EXPOSE 8888
ENV PYTHONUNBUFFERED=1
CMD ["python3", "app.py"]
