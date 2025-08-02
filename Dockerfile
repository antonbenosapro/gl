FROM python:3.10-slim

WORKDIR /gl

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt


COPY . .

ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
EXPOSE 8501

CMD ["streamlit", "run", "Home.py"]

