# sagumo:狭雲
SCPJP discord用のリアクション集計bot

## 目的
リアクション集計用の単一機能botです。セキュリティ確保のために皐月と分離。

## 環境構築用メモ（そのうち清書する）
```sh
sudo docker volume create sagumo-data
sudo docker build ./ -t sagumo
sudo docker run -d -v  sagumo-data:/opt/sagumo --restart=always --name sagumo sagumo
```
