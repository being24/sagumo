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
リアクション可能な役職を限定したい場合は
```
/cnt 整数 discord.Role
```
でその役職限定にできます

```
/ls
```
現在集計中のリアクションを一覧表示します
```
/remove(rm) ID
```
指定されたIDの集計を取りやめます
```
/clear_all
```
全てのリアクションの集計を取りやめます

## 環境構築用メモ
リポジトリ内のDockerfileと、tokenを記述したファイル名がtokenのファイル(token=bot_tokenの形で記述)を同一ディレクトリに入れ、ビルドしてrunすればOKです。
```sh
docker pull being241/sagumo
docker run -d -v sagumo-data:/opt --env-file .env --restart=always --name=sagumo being241/sagumo
```

docker hubからpullできるようにしました
環境変数DISCORD_BOT_TOKENからtokenを読み取ります
自分は.envファイルに環境変数DISCORD_BOT_TOKENにtokenを定義して渡してます