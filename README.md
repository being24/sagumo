# sagumo: 狭雲

SCPJP discord用のリアクション集計bot(読みは気にしない方針でお願いします）

## 目的

リアクション集計用のbotです。セキュリティ確保のために皐月と分離。

## 使い方

### リアクション集計関連

#### count (aliases = [cnt])

``` sh
/cnt 整数 *(discord.Role or discord.Member)
```

リアクション集計のコマンドです。指定した整数のリアクションが溜まった時、実行者にメンションを行います。

* :matte:のリアクションがついている場合は待ちます。なくなり次第メンションを行います。
* 整数の後に役職、もしくは任意の人へのメンションを行えば、その人以外はリアクションができません（botに取り消されます）
* 一回集まった後に取り消し、再度リアクションが集まった場合も通知します
* リマインドは12h, 24h, 以後24h間隔です
* リアクション集計が終了してから3日以上たった時に削除します
* リアクションが終了してなくても14日経ったら強制削除します

#### list_reaction (aliases = [lsre, ls])

``` sh
/ls
```

コマンドを打ったサーバーで集計中のリアクションを一覧表示します。

``` sh
/ls all
```

集計終了したけどまだDBから消えてないリアクション集計も表示します。

#### remove (aliases = [rm])

``` sh
/remove(rm) id
```

指定されたIDの集計を取りやめます。

#### add_role_for_init (aliases = [add_role])

``` sh
/add_role_for_init(add_role) add_role *has_role
```

has_role（複数個も可）を持っている役職にadd_roleをつけるコマンド。

#### sagumo_initialization (aliases=[s_init])

``` sh
/sagumo_initialization(s_init)  bot_manager bot_user
```

沙雲の管理用役職を登録するコマンド、両方ともroleです、順番注意。

### 投票関連

#### poll

``` sh
/poll question *choices_or_user_role
```

投票を行うコマンドです。内容だけ投稿すれば賛成反対の二択に、選択肢も入れればその投票になります.
ユーザーと役職のメンションを入れるとその役職に限定できます.チェックを押すと集計します.

* 選択肢は9個以下
* 30日経ったら強制削除します

### ツイート関連

#### tweet

``` sh
/tweet content
```

特定のサーバー限定でツイートを行うコマンド。管理者の1名以上の承認で投稿されます。（ログ取りあり）

#### remove_tweet

``` sh
/remove_tweet id
```

承認待ちを中止するコマンド

#### list_tweet (aliases=[lstw, lst])

``` sh
/list_tweet
```

承認待ち中のツイートを表示するコマンド

### ヘルプコマンド関連

#### help

``` sh
/help
```

拡張版ヘルプコマンド、dm対応しました

## dockerコマンド

[update.sh](update.sh)
