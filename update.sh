docker stop sagumo
docker rm sagumo
docker pull ghcr.io/being24/sagumo:latest
docker run -d -v sagumo-data:/opt --env-file .env --restart=always --name=sagumo ghcr.io/being24/sagumo