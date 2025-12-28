To run locally run:
docker build -t fpl-api:latest .
docker run --rm -p 8000:8000 --env-file .env -e PORT=8000 fpl-api:latest

Also don't forget that the endpoints have /entry/
e.g. http://localhost:8000/entry/3982786/insights

Deployed on render.com: https://fpl-api-aqej.onrender.com/entry/3982786/insights
