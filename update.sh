docker stop sagumo
docker rm sagumo
docker pull ghcr.io/being24/sagumo:latest
docker run -d -v test-data:/opt/sagumo/data --env-file .env --restart=always --name=sagumo ghcr.io/being24/sagumo