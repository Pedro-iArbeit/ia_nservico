# Projeto iA Nserviço

Instalação limpa da API FastAPI para deploy no Render e testes locais com Docker.

## Testar com Docker no Windows

1. Instale o [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Extraia este projeto para uma pasta local
3. Abra o terminal (PowerShell ou CMD) e navegue até à pasta do projeto:
   cd C:\caminho\para\ia_nservico
4. Construa a imagem Docker:
   docker build -t ia_nservico .
5. Execute o container:
   docker run -p 10000:10000 ia_nservico
6. Aceda à API no navegador:
   http://localhost:10000

## Deploy no Render

1. Faça push deste projeto para o GitHub
2. Crie um novo serviço no [Render](https://render.com)
3. Ligue o repositório e Render detectará automaticamente o `render.yaml`
4. O serviço será iniciado na porta 10000
