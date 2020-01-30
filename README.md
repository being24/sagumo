# sagumo:狭雲
SCPJP discord用のリアクション集計bot(読みは気にしない方針でお願いします）

## 目的
リアクション集計用の単一機能botです。セキュリティ確保のために皐月と分離。

## 使い方
```
/cnt 整数
```
で、規定数のリアクションがたまったら、コマンド実行者にメンションをとばします。
待ってのリアクションがあると、リアクションがたまってもメンションを飛ばしません

## 環境構築用メモ（そのうち清書する）
リポジトリ内のDockerfileと、tokenを記述したファイル名がtokenのファイル(token=bot_tokenの形で記述)を同一ディレクトリに入れ、ビルドしてrunすればOKです。
```sh
sudo docker build ./ -t sagumo
sudo docker run -d -v  sagumo-data:/opt/sagumo --restart=always --name sagumo sagumo
```
